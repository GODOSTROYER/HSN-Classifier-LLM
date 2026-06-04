import json
import httpx
from typing import AsyncGenerator
from .base import AgentProvider
from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, MODEL_ID

class OpenRouterProvider(AgentProvider):
    """
    Provider implementation for the OpenRouter API.
    """

    async def generate_response(self, system_prompt: str, user_prompt: str, 
                                max_tokens: int = 4096, temperature: float = 0.1) -> str:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8899",
            "X-Title": "HSN Classifier"
        }
        
        payload = {
            "model": MODEL_ID,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 0.95,
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                OPENROUTER_BASE_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            elif "error" in data:
                raise Exception(f"API Error: {data['error']}")
            else:
                raise Exception(f"Unexpected response: {data}")

    async def generate_streaming_response(self, system_prompt: str, user_prompt: str, 
                                          max_tokens: int = 16384, temperature: float = 0.15) -> AsyncGenerator[str, None]:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8899",
            "X-Title": "HSN Classifier"
        }
        
        payload = {
            "model": MODEL_ID,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 0.95,
            "stream": True,
        }
        
        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream("POST", OPENROUTER_BASE_URL,
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
