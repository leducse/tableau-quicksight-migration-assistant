"""GenAI generation behind a swappable interface (mock by default, Bedrock guarded)."""

from .base import CalcTranslation, GenAIProvider
from .factory import get_provider

__all__ = ["CalcTranslation", "GenAIProvider", "get_provider"]
