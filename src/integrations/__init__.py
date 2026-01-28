# Integrations module for REACH
# 

from .gemini_client import GeminiClient
from .imagen_client import ImagenClient
from .serp_client import SerpClient

try:
    from .openai_client import OpenAIClient
except ModuleNotFoundError as exc:
    if exc.name == "openai":
        OpenAIClient = None
    else:
        raise

__all__ = ["GeminiClient", "ImagenClient", "SerpClient"]
if OpenAIClient is not None:
    __all__.append("OpenAIClient")
