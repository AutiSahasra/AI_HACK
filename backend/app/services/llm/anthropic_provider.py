import json
import httpx
from typing import List, Dict, Any, Type
from pydantic import BaseModel
from app.services.llm.base import LLMProvider
from app.core.config import settings

class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str = "", model: str = ""):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or settings.ANTHROPIC_MODEL

    async def generate(
        self,
        messages: List[Dict[str, str]],
        response_schema: Type[BaseModel],
        temperature: float = 0.1,
        timeout: float = 30.0
    ) -> BaseModel:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        schema_dict = response_schema.model_json_schema()
        system_prompt = (
            "You are an expert site reliability and root-cause analysis engineer. "
            f"You MUST respond ONLY with a valid JSON object matching the following schema:\n{json.dumps(schema_dict)}"
        )

        anthropic_messages = []
        for m in messages:
            anthropic_messages.append({
                "role": m.get("role", "user"),
                "content": m.get("content", "")
            })

        payload = {
            "model": self.model,
            "system": system_prompt,
            "messages": anthropic_messages,
            "max_tokens": 4096,
            "temperature": temperature
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["content"][0]["text"]
            # Extract json block if surrounded by markdown code fences
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            parsed_json = json.loads(content)
            return response_schema.model_validate(parsed_json)
