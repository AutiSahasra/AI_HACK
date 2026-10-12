from datetime import datetime, timezone
import dateutil.parser
from typing import Dict, Any, Optional
from app.models.log_event import LogSeverity

class NormalizationService:
    SEVERITY_MAP = {
        "debug": LogSeverity.DEBUG,
        "dbg": LogSeverity.DEBUG,
        "trace": LogSeverity.DEBUG,
        "verbose": LogSeverity.DEBUG,
        "info": LogSeverity.INFO,
        "information": LogSeverity.INFO,
        "notice": LogSeverity.INFO,
        "warn": LogSeverity.WARN,
        "warning": LogSeverity.WARN,
        "alert": LogSeverity.WARN,
        "error": LogSeverity.ERROR,
        "err": LogSeverity.ERROR,
        "exception": LogSeverity.ERROR,
        "critical": LogSeverity.CRITICAL,
        "crit": LogSeverity.CRITICAL,
        "fatal": LogSeverity.CRITICAL,
        "emergency": LogSeverity.CRITICAL,
        "emerg": LogSeverity.CRITICAL,
    }

    @classmethod
    def normalize_severity(cls, raw_severity: Optional[str]) -> LogSeverity:
        if not raw_severity:
            return LogSeverity.INFO
        clean = str(raw_severity).strip().lower()
        return cls.SEVERITY_MAP.get(clean, LogSeverity.INFO)

    @classmethod
    def normalize_timestamp(cls, raw_timestamp: Any) -> datetime:
        if isinstance(raw_timestamp, datetime):
            if raw_timestamp.tzinfo is None:
                return raw_timestamp.replace(tzinfo=timezone.utc)
            return raw_timestamp

        if isinstance(raw_timestamp, (int, float)):
            # Epoch timestamp in seconds or milliseconds
            if raw_timestamp > 1e11:  # likely milliseconds
                raw_timestamp = raw_timestamp / 1000.0
            return datetime.fromtimestamp(raw_timestamp, tz=timezone.utc)

        if isinstance(raw_timestamp, str):
            clean = raw_timestamp.strip()
            # If empty
            if not clean:
                return datetime.now(timezone.utc)
            try:
                dt = dateutil.parser.parse(clean)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                return datetime.now(timezone.utc)

        return datetime.now(timezone.utc)

    @classmethod
    def normalize_service_name(cls, raw_service: Optional[str], default: str = "unknown-service") -> str:
        if not raw_service or not str(raw_service).strip():
            return default
        return str(raw_service).strip()

normalization_service = NormalizationService()
