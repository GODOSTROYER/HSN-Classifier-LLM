import json
import httpx
from typing import AsyncGenerator
from .base import AgentProvider
from config import CUSTOM_AGENT_API_URL, CUSTOM_AGENT_API_KEY

class CustomAPIProvider(AgentProvider):
    """
    Provider implementation for a Custom API endpoint.
    Expects the custom endpoint to follow a similar OpenAI/OpenRouter chat completions interface.
    """

    async def generate_response(self, system_prompt: str, user_prompt: str, 
                                max_tokens: int = 4096, temperature: float = 0.1) -> str:
        headers = {
            "Content-Type": "application/json",
        }
        if CUSTOM_AGENT_API_KEY:
            headers["Authorization"] = f"Bearer {CUSTOM_AGENT_API_KEY}"
        
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                CUSTOM_AGENT_API_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            else:
                return data.get("response", str(data))

    async def generate_streaming_response(self, system_prompt: str, user_prompt: str, 
                                          max_tokens: int = 16384, temperature: float = 0.15) -> AsyncGenerator[str, None]:
        headers = {
            "Content-Type": "application/json",
        }
        if CUSTOM_AGENT_API_KEY:
            headers["Authorization"] = f"Bearer {CUSTOM_AGENT_API_KEY}"
        
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        
        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream("POST", CUSTOM_AGENT_API_URL,
                                      headers=headers, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            return
                        try:
                            data = json.loads(data_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
