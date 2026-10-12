import json
import httpx
from typing import List, Dict, Any, Type
from pydantic import BaseModel
from app.services.llm.base import LLMProvider
from app.core.config import settings

class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, api_key: str = "", base_url: str = "", model: str = ""):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.base_url = (base_url or settings.OPENAI_BASE_URL).rstrip("/")
        self.model = model or settings.OPENAI_MODEL

    async def generate(
        self,
        messages: List[Dict[str, str]],
        response_schema: Type[BaseModel],
        temperature: float = 0.1,
        timeout: float = 30.0
    ) -> BaseModel:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        schema_dict = response_schema.model_json_schema()

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": response_schema.__name__,
                    "strict": True,
                    "schema": schema_dict
                }
            }
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            parsed_json = json.loads(content)
            return response_schema.model_validate(parsed_json)
