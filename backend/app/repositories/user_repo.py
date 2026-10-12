from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid
from app.core.database import DatabaseManager
from app.models.user import UserCreate, UserInDB, UserRole
from app.core.security import hash_password

class UserRepository:
    @property
    def col(self):
        return DatabaseManager.get_collection("users")

    async def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        return await self.col.find_one({"username": username})

    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        return await self.col.find_one({"email": email})

    async def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        return await self.col.find_one({"_id": user_id})

    async def create(self, user: UserCreate) -> Dict[str, Any]:
        user_id = str(uuid.uuid4())
        doc = {
            "_id": user_id,
            "username": user.username,
            "email": user.email,
            "role": user.role.value if isinstance(user.role, UserRole) else user.role,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "hashed_password": hash_password(user.password),
            "created_at": datetime.now(timezone.utc),
        }
        await self.col.insert_one(doc)
        return doc

    async def list_all(self) -> List[Dict[str, Any]]:
        cursor = self.col.find({})
        return await cursor.to_list(length=100)

user_repo = UserRepository()
