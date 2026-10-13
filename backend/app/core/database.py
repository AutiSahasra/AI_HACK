import logging
import asyncio
from typing import Dict, Any, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

logger = logging.getLogger(__name__)

# Lightweight in-memory async collection implementation for offline/test environments
class InMemoryCollection:
    def __init__(self, name: str):
        self.name = name
        self._docs: List[Dict[str, Any]] = []

    async def insert_one(self, doc: Dict[str, Any]):
        doc_copy = dict(doc)
        if "_id" not in doc_copy:
            import uuid
            doc_copy["_id"] = str(uuid.uuid4())
        self._docs.append(doc_copy)
        class InsertResult:
            def __init__(self, inserted_id):
                self.inserted_id = inserted_id
        return InsertResult(doc_copy["_id"])

    async def insert_many(self, docs: List[Dict[str, Any]]):
        inserted_ids = []
        for d in docs:
            res = await self.insert_one(d)
            inserted_ids.append(res.inserted_id)
        class ManyResult:
            def __init__(self, ids):
                self.inserted_ids = ids
        return ManyResult(inserted_ids)

    async def find_one(self, filter: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        results = await self._filter_docs(filter)
        return dict(results[0]) if results else None

    def find(self, filter: Optional[Dict[str, Any]] = None, sort: Optional[List[tuple]] = None):
        fltr = filter or {}
        class Cursor:
            def __init__(self, parent, filter_dict, sort_spec):
                self.parent = parent
                self.filter_dict = filter_dict
                self.sort_spec = sort_spec
                self._skip = 0
                self._limit = 0

            def skip(self, count: int):
                self._skip = count
                return self

            def limit(self, count: int):
                self._limit = count
                return self

            def sort(self, key_or_list, direction=1):
                if isinstance(key_or_list, str):
                    self.sort_spec = [(key_or_list, direction)]
                else:
                    self.sort_spec = key_or_list
                return self

            async def to_list(self, length: Optional[int] = None) -> List[Dict[str, Any]]:
                matched = await self.parent._filter_docs(self.filter_dict)
                if self.sort_spec:
                    for key, direction in reversed(self.sort_spec):
                        matched.sort(
                            key=lambda x: (x.get(key) is None, x.get(key)),
                            reverse=(direction == -1)
                        )
                if self._skip:
                    matched = matched[self._skip:]
                limit_val = length if length is not None else self._limit
                if limit_val and limit_val > 0:
                    matched = matched[:limit_val]
                return [dict(d) for d in matched]

            def __aiter__(self):
                self._iter_docs = None
                return self

            async def __anext__(self):
                if self._iter_docs is None:
                    self._iter_docs = await self.to_list(None)
                    self._idx = 0
                if self._idx < len(self._iter_docs):
                    res = self._iter_docs[self._idx]
                    self._idx += 1
                    return res
                raise StopAsyncIteration

        return Cursor(self, fltr, sort)

    async def update_one(self, filter: Dict[str, Any], update: Dict[str, Any], upsert: bool = False):
        matched = await self._filter_docs(filter)
        modified_count = 0
        upserted_id = None
        if matched:
            doc = matched[0]
            if "$set" in update:
                for k, v in update["$set"].items():
                    doc[k] = v
            if "$inc" in update:
                for k, v in update["$inc"].items():
                    doc[k] = doc.get(k, 0) + v
            if "$push" in update:
                for k, v in update["$push"].items():
                    if k not in doc or not isinstance(doc[k], list):
                        doc[k] = []
                    doc[k].append(v)
            if "$addToSet" in update:
                for k, v in update["$addToSet"].items():
                    if k not in doc or not isinstance(doc[k], list):
                        doc[k] = []
                    if v not in doc[k]:
                        doc[k].append(v)
            modified_count = 1
        elif upsert:
            new_doc = dict(filter)
            if "$set" in update:
                new_doc.update(update["$set"])
            import uuid
            new_doc["_id"] = str(uuid.uuid4())
            self._docs.append(new_doc)
            upserted_id = new_doc["_id"]

        class UpdateResult:
            def __init__(self, matched_cnt, mod_cnt, u):
                self.matched_count = matched_cnt
                self.modified_count = mod_cnt
                self.upserted_id = u
        return UpdateResult(1 if matched else 0, modified_count, upserted_id)

    async def count_documents(self, filter: Dict[str, Any]) -> int:
        matched = await self._filter_docs(filter)
        return len(matched)

    async def delete_one(self, filter: Dict[str, Any]):
        matched = await self._filter_docs(filter)
        if matched:
            self._docs.remove(matched[0])
            return 1
        return 0

    async def delete_many(self, filter: Dict[str, Any]):
        matched = await self._filter_docs(filter)
        for m in matched:
            self._docs.remove(m)
        class DeleteResult:
            def __init__(self, c):
                self.deleted_count = c
        return DeleteResult(len(matched))

    async def distinct(self, key: str, filter: Optional[Dict[str, Any]] = None) -> List[Any]:
        docs = await self._filter_docs(filter or {})
        vals = set()
        for d in docs:
            if key in d and d[key] is not None:
                vals.add(d[key])
        return list(vals)

    async def create_index(self, keys, **kwargs):
        return "index_ok"

    async def _filter_docs(self, filter_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        results = []
        for doc in self._docs:
            if self._matches(doc, filter_dict):
                results.append(doc)
        return results

    def _matches(self, doc: Dict[str, Any], filter_dict: Dict[str, Any]) -> bool:
        if not filter_dict:
            return True
        for k, v in filter_dict.items():
            if k == "$text":
                search_term = v.get("$search", "").lower()
                doc_str = json_str(doc).lower()
                if search_term not in doc_str:
                    return False
                continue
            if k == "$or":
                if not any(self._matches(doc, cond) for cond in v):
                    return False
                continue
            if k == "$and":
                if not all(self._matches(doc, cond) for cond in v):
                    return False
                continue

            # Nested fields e.g. "source.type"
            doc_val = self._get_nested(doc, k)
            if isinstance(v, dict):
                for op, op_val in v.items():
                    if op == "$gte" and not (doc_val is not None and doc_val >= op_val):
                        return False
                    if op == "$lte" and not (doc_val is not None and doc_val <= op_val):
                        return False
                    if op == "$gt" and not (doc_val is not None and doc_val > op_val):
                        return False
                    if op == "$lt" and not (doc_val is not None and doc_val < op_val):
                        return False
                    if op == "$in" and not (doc_val in op_val):
                        return False
                    if op == "$ne" and not (doc_val != op_val):
                        return False
                    if op == "$regex":
                        import re
                        if not doc_val or not re.search(str(op_val), str(doc_val), re.I):
                            return False
            else:
                if doc_val != v:
                    return False
        return True

    def _get_nested(self, doc: Dict[str, Any], key: str):
        parts = key.split('.')
        curr = doc
        for p in parts:
            if isinstance(curr, dict) and p in curr:
                curr = curr[p]
            else:
                return None
        return curr

def json_str(d):
    import json
    try:
        return json.dumps(d, default=str)
    except Exception:
        return str(d)

class InMemoryDatabase:
    def __init__(self, name: str):
        self.name = name
        self._collections: Dict[str, InMemoryCollection] = {}

    def get_collection(self, name: str) -> InMemoryCollection:
        if name not in self._collections:
            self._collections[name] = InMemoryCollection(name)
        return self._collections[name]

    def __getitem__(self, name: str) -> InMemoryCollection:
        return self.get_collection(name)

class DatabaseManager:
    client: Optional[AsyncIOMotorClient] = None
    db = None

    @classmethod
    async def connect(cls):
        if settings.USE_IN_MEMORY_DB:
            logger.info("Configured to use in-memory database")
            cls.db = InMemoryDatabase(settings.MONGODB_DB_NAME)
            return

        try:
            # Try connecting with 1.5s timeout to test if live Mongo is running
            test_client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=1500)
            await test_client.admin.command('ping')
            cls.client = test_client
            cls.db = cls.client[settings.MONGODB_DB_NAME]
            logger.info(f"Connected to live MongoDB at {settings.MONGODB_URI}")
            await cls._init_indexes()
        except Exception as e:
            logger.warning(f"Could not connect to MongoDB ({e}). Falling back to in-memory store for standalone/testing.")
            cls.db = InMemoryDatabase(settings.MONGODB_DB_NAME)

    @classmethod
    async def disconnect(cls):
        if cls.client:
            cls.client.close()
            cls.client = None

    @classmethod
    async def _init_indexes(cls):
        if cls.db is not None and not isinstance(cls.db, InMemoryDatabase):
            try:
                # logEvents indexes
                log_events = cls.db.get_collection("logEvents")
                await log_events.create_index([("timestamp", -1)])
                await log_events.create_index([("severity", 1)])
                await log_events.create_index([("service", 1)])
                await log_events.create_index([("source.type", 1)])
                await log_events.create_index([("fingerprint", 1)])
                await log_events.create_index([("message", "text")])

                # incidents indexes
                incidents = cls.db.get_collection("incidents")
                await incidents.create_index([("status", 1)])
                await incidents.create_index([("severity", 1)])
                await incidents.create_index([("service", 1)])
                await incidents.create_index([("updatedAt", -1)])

                # tickets indexes
                tickets = cls.db.get_collection("tickets")
                await tickets.create_index([("status", 1)])
                await tickets.create_index([("assignee", 1)])
                await tickets.create_index([("incidentId", 1)])

                # historicalIncidents & runbooks text indexes
                hist = cls.db.get_collection("historicalIncidents")
                await hist.create_index([("title", "text"), ("cause", "text"), ("summary", "text")])
                runbooks = cls.db.get_collection("runbooks")
                await runbooks.create_index([("title", "text"), ("description", "text")])
            except Exception as e:
                logger.warning(f"Index creation warning: {e}")

    @classmethod
    def get_collection(cls, name: str):
        if cls.db is None:
            # Lazy initialize in-memory if called before connect
            cls.db = InMemoryDatabase(settings.MONGODB_DB_NAME)
        return cls.db[name]

def get_db():
    return DatabaseManager.db
