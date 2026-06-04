import os
from .base import AgentProvider
from config import AGENT_PROVIDER

def get_provider() -> AgentProvider:
    """
    Factory method to instantiate the configured AgentProvider.
    """
    provider_name = AGENT_PROVIDER.lower().strip()
    
    if provider_name == "openrouter":
        from .openrouter import OpenRouterProvider
        return OpenRouterProvider()
    elif provider_name == "custom":
        from .custom_api import CustomAPIProvider
        return CustomAPIProvider()
    elif provider_name == "local":
        from .local_agent import LocalAgentProvider
        return LocalAgentProvider()
    else:
        raise ValueError(f"Unknown AGENT_PROVIDER '{provider_name}'. Available providers: 'openrouter', 'custom', 'local'")
