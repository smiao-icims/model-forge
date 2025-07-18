"""ModelForge: A reusable library for managing LLM providers."""

__version__ = "0.2.0"

from .auth import get_auth_strategy, get_credentials
from .config import get_config, get_current_model
from .registry import ModelForgeRegistry

__all__ = [
    "ModelForgeRegistry",
    "get_config",
    "get_current_model",
    "get_auth_strategy",
    "get_credentials",
]
