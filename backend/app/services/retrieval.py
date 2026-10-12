from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.core.database import DatabaseManager

class Retriever(ABC):
    @abstractmethod
    async def retrieve_historical_incidents(
        self,
        service: str,
        query: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def retrieve_runbooks(
        self,
        service: str,
        query: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        pass

class MongoTextRetriever(Retriever):
    async def retrieve_historical_incidents(
        self,
        service: str,
        query: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        col = DatabaseManager.get_collection("historicalIncidents")
        # Try service match or text search
        filter_dict: Dict[str, Any] = {}
        if service and service != "*":
            filter_dict["$or"] = [
                {"service": service},
                {"service": "*"}
            ]

        cursor = col.find(filter_dict)
        results = await cursor.to_list(length=top_k * 2)

        # Keyword relevance score in memory
        keywords = [w.lower() for w in query.split() if len(w) > 3]
        if keywords and results:
            for r in results:
                text = f"{r.get('title', '')} {r.get('summary', '')} {r.get('verifiedCause', '')} {r.get('logExcerpt', '')}".lower()
                score = sum(1 for kw in keywords if kw in text)
                r["_score"] = score
            results.sort(key=lambda x: x.get("_score", 0), reverse=True)

        return results[:top_k]

    async def retrieve_runbooks(
        self,
        service: str,
        query: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        col = DatabaseManager.get_collection("runbooks")
        filter_dict: Dict[str, Any] = {}
        if service and service != "*":
            filter_dict["$or"] = [
                {"service": service},
                {"service": "*"}
            ]

        cursor = col.find(filter_dict)
        results = await cursor.to_list(length=top_k * 2)

        keywords = [w.lower() for w in query.split() if len(w) > 3]
        if keywords and results:
            for r in results:
                text = f"{r.get('title', '')} {r.get('description', '')}".lower()
                score = sum(1 for kw in keywords if kw in text)
                r["_score"] = score
            results.sort(key=lambda x: x.get("_score", 0), reverse=True)

        return results[:top_k]

retriever_service = MongoTextRetriever()
