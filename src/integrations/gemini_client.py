"""
Google Gemini Client for REACH.


This module provides integration with Google's Gemini API for
natural language understanding and generation using the new google-genai package.
"""

import logging
import re
from typing import Any, Optional

from google import genai
from google.genai import types

from ..core.config import get_settings

logger = logging.getLogger(__name__)

# Conservative cap to avoid oversized prompts (Gemini rejects very large inputs).
MAX_INPUT_CHARS = 200_000


class GeminiClient:
    """
    Client for interacting with Google Gemini API.
    
    This client provides:
    - Text generation with configurable parameters
    - Conversation management
    - Error handling and retries
    - Token usage tracking
    
    Uses the new google-genai package (replacing deprecated google-generativeai).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        default_temperature: Optional[float] = None,
        default_max_tokens: Optional[int] = None,
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
        self.default_temperature = default_temperature if default_temperature is not None else settings.gemini_temperature
        self.default_max_tokens = default_max_tokens or settings.gemini_max_tokens
        self._client = None
        self._initialized = False

        if self.api_key:
            self._initialize()

    def _initialize(self) -> None:
        """Initialize the Gemini API client."""
        try:
            self._client = genai.Client(api_key=self.api_key)
            self._initialized = True
            logger.info(f"Gemini client initialized with model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Check if the client is initialized."""
        return self._initialized

    def _sanitize_text(self, text: Optional[str]) -> Optional[str]:
        """Strip oversized data URIs and truncate very long inputs."""
        if not text:
            return text

        # Remove embedded base64 images to avoid massive token counts.
        text = re.sub(
            r"data:image\/[a-zA-Z0-9.+-]+;base64,[A-Za-z0-9+/=]+",
            "[image omitted]",
            text,
        )

        if len(text) > MAX_INPUT_CHARS:
            logger.warning("Prompt too large (%s chars); truncating to %s chars.", len(text), MAX_INPUT_CHARS)
            text = text[:MAX_INPUT_CHARS]

        return text

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
            prompt = self._sanitize_text(prompt) or ""
            system_prompt = self._sanitize_text(system_prompt)

            # Build generation config
            generation_config = types.GenerateContentConfig(
                temperature=temperature if temperature is not None else self.default_temperature,
                max_output_tokens=max_tokens or self.default_max_tokens,
                stop_sequences=stop_sequences,
                system_instruction=system_prompt,
            )

            # Generate response using the new API
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=generation_config,
            )

            # Extract content
            content = ""
            if response.text:
                content = response.text

            # Get token usage if available
            tokens_used = None
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                tokens_used = getattr(response.usage_metadata, "total_token_count", None)

            return {
                "content": content,
                "model": self.model_name,
                "tokens_used": tokens_used,
                "metadata": {
                    "finish_reason": self._get_finish_reason(response),
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
            prompt = self._sanitize_text(prompt) or ""
            system_prompt = self._sanitize_text(system_prompt)
            sanitized_history = []
            for message in history:
                sanitized_history.append({
                    "role": message.get("role", "user"),
                    "content": self._sanitize_text(message.get("content", "")) or "",
                })

            # Build generation config
            generation_config = types.GenerateContentConfig(
                temperature=temperature if temperature is not None else self.default_temperature,
                max_output_tokens=max_tokens or self.default_max_tokens,
                system_instruction=system_prompt,
            )

            # Format history into contents
            contents = self._format_history_as_contents(sanitized_history)
            
            # Add current prompt
            contents.append(types.Content(
                role="user",
                parts=[types.Part.from_text(prompt)],
            ))

            # Generate response
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=generation_config,
            )

            content = ""
            if response.text:
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

    def _format_history_as_contents(
        self,
        history: list[dict[str, str]],
    ) -> list[types.Content]:
        """
        Format conversation history for Gemini.
        
        Args:
            history: List of message dictionaries
            
        Returns:
            Formatted contents for Gemini
        """
        contents = []
        for message in history:
            role = message.get("role", "user")
            content_text = message.get("content", "")

            # Map roles to Gemini format
            gemini_role = "user" if role == "user" else "model"

            contents.append(types.Content(
                role=gemini_role,
                parts=[types.Part.from_text(content_text)],
            ))

        return contents

    def _get_finish_reason(self, response: Any) -> Optional[str]:
        """
        Get finish reason from response.
        
        Args:
            response: Gemini response object
            
        Returns:
            Finish reason string or None
        """
        try:
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "finish_reason"):
                    return str(candidate.finish_reason)
        except Exception:
            pass
        return None

    def _extract_safety_ratings(self, response: Any) -> list[dict[str, Any]]:
        """
        Extract safety ratings from response.
        
        Args:
            response: Gemini response object
            
        Returns:
            List of safety rating dictionaries
        """
        ratings = []
        try:
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "safety_ratings") and candidate.safety_ratings:
                    for rating in candidate.safety_ratings:
                        ratings.append({
                            "category": str(rating.category) if hasattr(rating, "category") else "unknown",
                            "probability": str(rating.probability) if hasattr(rating, "probability") else "unknown",
                        })
        except Exception as e:
            logger.debug(f"Could not extract safety ratings: {e}")
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
            result = self._client.models.count_tokens(
                model=self.model_name,
                contents=text,
            )
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

    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop_sequences: Optional[list[str]] = None,
    ):
        """
        Generate text using Gemini with streaming.
        
        This is a synchronous generator that yields text chunks as they are generated.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system instruction
            temperature: Generation temperature
            max_tokens: Maximum tokens to generate
            stop_sequences: Optional stop sequences
            
        Yields:
            Text chunks as they are generated
        """
        if not self._initialized:
            yield ""
            return

        try:
            # Build generation config
            generation_config = types.GenerateContentConfig(
                temperature=temperature if temperature is not None else self.default_temperature,
                max_output_tokens=max_tokens or self.default_max_tokens,
                stop_sequences=stop_sequences,
                system_instruction=system_prompt,
            )

            # Generate response with streaming using the new API
            response_stream = self._client.models.generate_content_stream(
                model=self.model_name,
                contents=prompt,
                config=generation_config,
            )

            # Yield text chunks as they arrive
            for chunk in response_stream:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"Gemini streaming error: {str(e)}")
            yield f"Error: {str(e)}"

    async def generate_stream_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop_sequences: Optional[list[str]] = None,
    ):
        """
        Generate text using Gemini with async streaming.
        
        This is an async generator that yields text chunks as they are generated.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system instruction
            temperature: Generation temperature
            max_tokens: Maximum tokens to generate
            stop_sequences: Optional stop sequences
            
        Yields:
            Text chunks as they are generated
        """
        if not self._initialized:
            yield ""
            return

        try:
            # Build generation config
            generation_config = types.GenerateContentConfig(
                temperature=temperature if temperature is not None else self.default_temperature,
                max_output_tokens=max_tokens or self.default_max_tokens,
                stop_sequences=stop_sequences,
                system_instruction=system_prompt,
            )

            # Generate response with async streaming
            async for chunk in await self._client.aio.models.generate_content_stream(
                model=self.model_name,
                contents=prompt,
                config=generation_config,
            ):
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"Gemini async streaming error: {str(e)}")
            yield f"Error: {str(e)}"

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
