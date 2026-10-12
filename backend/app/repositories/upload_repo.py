from typing import Optional, List, Dict, Any
from app.core.database import DatabaseManager

class UploadRepository:
    @property
    def col(self):
        return DatabaseManager.get_collection("uploads")

    async def create(self, upload_doc: Dict[str, Any]) -> str:
        res = await self.col.insert_one(upload_doc)
        return res.inserted_id

    async def get_by_id(self, upload_id: str) -> Optional[Dict[str, Any]]:
        return await self.col.find_one({"_id": upload_id})

    async def list_uploads(self, limit: int = 50) -> List[Dict[str, Any]]:
        cursor = self.col.find({}).sort("createdAt", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def update(self, upload_id: str, update_dict: Dict[str, Any]):
        await self.col.update_one({"_id": upload_id}, {"$set": update_dict})

upload_repo = UploadRepository()
