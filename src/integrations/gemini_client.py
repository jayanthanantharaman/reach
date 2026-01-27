"""
Google Gemini Client for REACH.


This module provides integration with Google's Gemini API for
natural language understanding and generation.
"""

import logging
from typing import Any, Optional

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from ..core.config import get_settings

logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Client for interacting with Google Gemini API.
    
    This client provides:
    - Text generation with configurable parameters
    - Conversation management
    - Error handling and retries
    - Token usage tracking
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        default_temperature: float = 0.7,
        default_max_tokens: int = 4096,
    ):
        """
        Initialize the Gemini client.
        
        Args:
            api_key: Google API key (uses env var if not provided)
            model: Model name to use
            default_temperature: Default temperature for generation
            default_max_tokens: Default max tokens for generation
        """
        settings = get_settings()
        self.api_key = api_key or settings.google_api_key
        self.model_name = model or settings.gemini_model
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens
        self._model = None
        self._chat_session = None
        self._initialized = False

        if self.api_key:
            self._initialize()

    def _initialize(self) -> None:
        """Initialize the Gemini API client."""
        try:
            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel(self.model_name)
            self._initialized = True
            logger.info(f"Gemini client initialized with model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Check if the client is initialized."""
        return self._initialized

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop_sequences: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Generate text using Gemini.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system instruction
            temperature: Generation temperature
            max_tokens: Maximum tokens to generate
            stop_sequences: Optional stop sequences
            
        Returns:
            Dictionary with content, metadata, and token usage
        """
        if not self._initialized:
            return {
                "content": "",
                "error": "Gemini client not initialized. Check API key.",
                "model": self.model_name,
            }

        try:
            # Build generation config
            generation_config = GenerationConfig(
                temperature=temperature or self.default_temperature,
                max_output_tokens=max_tokens or self.default_max_tokens,
                stop_sequences=stop_sequences,
            )

            # Combine system prompt with user prompt if provided
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"

            # Generate response
            response = self._model.generate_content(
                full_prompt,
                generation_config=generation_config,
            )

            # Extract content
            content = ""
            if response.parts:
                content = response.text

            # Get token usage if available
            tokens_used = None
            if hasattr(response, "usage_metadata"):
                tokens_used = getattr(response.usage_metadata, "total_token_count", None)

            return {
                "content": content,
                "model": self.model_name,
                "tokens_used": tokens_used,
                "metadata": {
                    "finish_reason": getattr(response, "finish_reason", None),
                    "safety_ratings": self._extract_safety_ratings(response),
                },
            }

        except Exception as e:
            logger.error(f"Gemini generation error: {str(e)}")
            return {
                "content": "",
                "error": str(e),
                "model": self.model_name,
            }

    async def generate_with_history(
        self,
        prompt: str,
        history: list[dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Generate text with conversation history.
        
        Args:
            prompt: Current user prompt
            history: List of previous messages
            system_prompt: Optional system instruction
            temperature: Generation temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Dictionary with content and metadata
        """
        if not self._initialized:
            return {
                "content": "",
                "error": "Gemini client not initialized. Check API key.",
                "model": self.model_name,
            }

        try:
            # Build generation config
            generation_config = GenerationConfig(
                temperature=temperature or self.default_temperature,
                max_output_tokens=max_tokens or self.default_max_tokens,
            )

            # Create chat session with history
            chat_history = self._format_history(history)

            # Start chat with system instruction if provided
            if system_prompt:
                chat = self._model.start_chat(
                    history=chat_history,
                )
            else:
                chat = self._model.start_chat(history=chat_history)

            # Send message
            response = chat.send_message(
                prompt,
                generation_config=generation_config,
            )

            content = ""
            if response.parts:
                content = response.text

            return {
                "content": content,
                "model": self.model_name,
                "metadata": {
                    "history_length": len(history),
                },
            }

        except Exception as e:
            logger.error(f"Gemini chat error: {str(e)}")
            return {
                "content": "",
                "error": str(e),
                "model": self.model_name,
            }

    def _format_history(
        self,
        history: list[dict[str, str]],
    ) -> list[dict[str, Any]]:
        """
        Format conversation history for Gemini.
        
        Args:
            history: List of message dictionaries
            
        Returns:
            Formatted history for Gemini
        """
        formatted = []
        for message in history:
            role = message.get("role", "user")
            content = message.get("content", "")

            # Map roles to Gemini format
            gemini_role = "user" if role == "user" else "model"

            formatted.append({
                "role": gemini_role,
                "parts": [content],
            })

        return formatted

    def _extract_safety_ratings(self, response: Any) -> list[dict[str, Any]]:
        """
        Extract safety ratings from response.
        
        Args:
            response: Gemini response object
            
        Returns:
            List of safety rating dictionaries
        """
        ratings = []
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "safety_ratings"):
                for rating in candidate.safety_ratings:
                    ratings.append({
                        "category": str(rating.category),
                        "probability": str(rating.probability),
                    })
        return ratings

    async def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Token count
        """
        if not self._initialized:
            # Rough estimate: ~4 characters per token
            return len(text) // 4

        try:
            result = self._model.count_tokens(text)
            return result.total_tokens
        except Exception as e:
            logger.warning(f"Token counting error: {str(e)}")
            return len(text) // 4

    def get_model_info(self) -> dict[str, Any]:
        """
        Get information about the current model.
        
        Returns:
            Model information dictionary
        """
        return {
            "model_name": self.model_name,
            "initialized": self._initialized,
            "default_temperature": self.default_temperature,
            "default_max_tokens": self.default_max_tokens,
        }

    async def test_connection(self) -> bool:
        """
        Test the API connection.
        
        Returns:
            True if connection is successful
        """
        if not self._initialized:
            return False

        try:
            response = await self.generate(
                prompt="Say 'Hello' in one word.",
                max_tokens=10,
            )
            return "error" not in response
        except Exception:
            return False