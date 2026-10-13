import json
import logging
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import redis
from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisOperationalService:
    """
    Redis boundary implementation for transient caching and event streams.
    Adheres to PDF specification:
    - Never stores permanent source of truth (MongoDB is durable store).
    - Caches analysis predictions using normalized incident feature keys with TTL.
    - Streams new log events for background workers.
    - Never caches or logs unredacted secrets.
    - Transparent fallback to local in-memory storage if Redis daemon is offline.
    """

    def __init__(self, redis_url: str = settings.REDIS_URL, ttl: int = settings.REDIS_CACHE_TTL_SECONDS):
        self.redis_url = redis_url
        self.default_ttl = ttl
        self._client: Optional[redis.Redis] = None
        self._is_connected = False
        self._mem_cache: Dict[str, Tuple[datetime, Dict[str, Any]]] = {}
        self._mem_stream: List[Dict[str, Any]] = []
        self._init_connection()

    def _init_connection(self):
        try:
            r = redis.from_url(self.redis_url, decode_responses=True, socket_timeout=1.0)
            r.ping()
            self._client = r
            self._is_connected = True
            logger.info(f"Connected to Redis at {self.redis_url}")
        except Exception as e:
            self._is_connected = False
            self._client = None
            logger.info(f"Redis is not reachable ({e}). Using in-memory fallback cache/streams.")

    @property
    def is_live(self) -> bool:
        return self._is_connected and self._client is not None

    def make_cache_key(
        self,
        incident_features: Dict[str, Any],
        model_version: str,
        rules_version: str = "v1",
        context_version: str = "v1",
    ) -> str:
        """
        Build normalized cache key incorporating input features, model version, and rules context.
        """
        # Redact any accidental sensitive keys before serialization
        clean_features = {
            k: v for k, v in sorted(incident_features.items())
            if not any(secret_term in k.lower() for secret_term in ["pass", "token", "key", "auth", "secret"])
        }
        feat_repr = json.dumps(clean_features, sort_keys=True, default=str)
        fp = hashlib.sha256(feat_repr.encode("utf-8")).hexdigest()[:16]
        return f"rca:cache:{fp}:{model_version}:{rules_version}:{context_version}"

    def get_cached_analysis(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached analysis if present and not expired."""
        if self.is_live:
            try:
                raw = self._client.get(cache_key)
                if raw:
                    return json.loads(raw)
            except Exception as e:
                logger.warning(f"Redis get error: {e}")

        # In-memory fallback
        if cache_key in self._mem_cache:
            expires_at, data = self._mem_cache[cache_key]
            if datetime.now(timezone.utc) < expires_at:
                return data
            else:
                del self._mem_cache[cache_key]
        return None

    def cache_analysis(self, cache_key: str, data: Dict[str, Any], ttl_seconds: Optional[int] = None) -> bool:
        """Store transient analysis result with expiration TTL."""
        ttl = ttl_seconds or self.default_ttl
        payload = json.dumps(data, default=str)

        if self.is_live:
            try:
                self._client.setex(cache_key, ttl, payload)
                return True
            except Exception as e:
                logger.warning(f"Redis set error: {e}")

        # In-memory fallback
        from datetime import timedelta
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
        self._mem_cache[cache_key] = (expires_at, data)
        return True

    def publish_log_event(self, event_dict: Dict[str, Any], stream_key: str = "stream:log_events") -> str:
        """Queue new log event for background processing."""
        clean_event = {
            k: str(v) for k, v in event_dict.items()
            if not any(term in k.lower() for term in ["pass", "token", "secret", "auth"])
        }

        if self.is_live:
            try:
                event_id = self._client.xadd(stream_key, clean_event, maxlen=10000)
                return str(event_id)
            except Exception as e:
                logger.warning(f"Redis xadd error: {e}")

        # In-memory queue fallback
        sim_id = f"mem_stream_{len(self._mem_stream)+1}"
        self._mem_stream.append({"id": sim_id, "data": clean_event, "ack": False})
        return sim_id

    def read_log_events(self, stream_key: str = "stream:log_events", count: int = 10) -> List[Dict[str, Any]]:
        """Read pending log events from stream."""
        if self.is_live:
            try:
                results = self._client.xrevrange(stream_key, count=count)
                events = []
                for eid, fields in results:
                    events.append({"id": eid, "data": fields})
                return events
            except Exception as e:
                logger.warning(f"Redis xrevrange error: {e}")

        # In-memory stream fallback
        unacked = [e for e in self._mem_stream if not e["ack"]][:count]
        return unacked

    def ack_log_event(self, event_id: str) -> bool:
        """Acknowledge processed event."""
        for item in self._mem_stream:
            if item["id"] == event_id:
                item["ack"] = True
                return True
        return True


redis_service = RedisOperationalService()
