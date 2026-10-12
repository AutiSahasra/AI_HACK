from abc import ABC, abstractmethod
from typing import List, Dict, Any, Type, Optional
from pydantic import BaseModel

class LLMProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        response_schema: Type[BaseModel],
        temperature: float = 0.1,
        timeout: float = 30.0
    ) -> BaseModel:
        """
        Generate completion using strict Pydantic response schema.
        """
        pass
