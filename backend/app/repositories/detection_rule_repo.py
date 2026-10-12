from typing import List, Dict, Any, Optional
from app.core.database import DatabaseManager

class DetectionRuleRepository:
    @property
    def col(self):
        return DatabaseManager.get_collection("detectionRules")

    async def list_active_rules(self) -> List[Dict[str, Any]]:
        cursor = self.col.find({"enabled": True})
        return await cursor.to_list(length=100)

    async def get_by_id(self, rule_id: str) -> Optional[Dict[str, Any]]:
        return await self.col.find_one({"_id": rule_id})

    async def update_rule(self, rule_id: str, updates: Dict[str, Any]):
        await self.col.update_one({"_id": rule_id}, {"$set": updates})

detection_rule_repo = DetectionRuleRepository()
