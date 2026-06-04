from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional

class AgentProvider(ABC):
    """
    Abstract base class for all AI agent providers.
    """

    @abstractmethod
    async def generate_response(self, system_prompt: str, user_prompt: str, 
                                max_tokens: int = 4096, temperature: float = 0.1) -> str:
        """
        Generate a complete response from the AI agent.
        """
        pass

    @abstractmethod
    async def generate_streaming_response(self, system_prompt: str, user_prompt: str, 
                                          max_tokens: int = 16384, temperature: float = 0.15) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from the AI agent.
        """
        pass
