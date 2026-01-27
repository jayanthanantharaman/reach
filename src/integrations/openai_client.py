"""
OpenAI Client for REACH.


This module provides integration with OpenAI's API for
DALL-E image generation and GPT text generation.
"""

import logging
from typing import Any, Optional

from openai import AsyncOpenAI

from ..core.config import get_settings

logger = logging.getLogger(__name__)


class OpenAIClient:
    """
    Client for interacting with OpenAI API.
    
    This client provides:
    - DALL-E 3 image generation
    - GPT text generation (as fallback)
    - Error handling and retries
    """

    # Supported DALL-E 3 sizes
    SUPPORTED_SIZES = ["1024x1024", "1792x1024", "1024x1792"]

    def __init__(
        self,
        api_key: Optional[str] = None,
        dalle_model: Optional[str] = None,
        default_image_size: str = "1024x1024",
        default_quality: str = "standard",
    ):
        """
        Initialize the OpenAI client.
        
        Args:
            api_key: OpenAI API key (uses env var if not provided)
            dalle_model: DALL-E model to use
            default_image_size: Default image size
            default_quality: Default image quality (standard or hd)
        """
        settings = get_settings()
        self.api_key = api_key or settings.openai_api_key
        self.dalle_model = dalle_model or settings.dalle_model
        self.default_image_size = default_image_size
        self.default_quality = default_quality
        self._client = None
        self._initialized = False

        if self.api_key:
            self._initialize()

    def _initialize(self) -> None:
        """Initialize the OpenAI client."""
        try:
            self._client = AsyncOpenAI(api_key=self.api_key)
            self._initialized = True
            logger.info(f"OpenAI client initialized with DALL-E model: {self.dalle_model}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Check if the client is initialized."""
        return self._initialized

    async def generate_image(
        self,
        prompt: str,
        size: Optional[str] = None,
        quality: Optional[str] = None,
        style: Optional[str] = None,
        n: int = 1,
    ) -> dict[str, Any]:
        """
        Generate an image using DALL-E 3.
        
        Args:
            prompt: Image generation prompt
            size: Image size (1024x1024, 1792x1024, or 1024x1792)
            quality: Image quality (standard or hd)
            style: Image style (vivid or natural)
            n: Number of images to generate (DALL-E 3 only supports 1)
            
        Returns:
            Dictionary with image URL and metadata
        """
        if not self._initialized:
            return {
                "url": "",
                "error": "OpenAI client not initialized. Check API key.",
                "model": self.dalle_model,
            }

        # Validate and set parameters
        image_size = size if size in self.SUPPORTED_SIZES else self.default_image_size
        image_quality = quality if quality in ["standard", "hd"] else self.default_quality
        image_style = style if style in ["vivid", "natural"] else "vivid"

        try:
            response = await self._client.images.generate(
                model=self.dalle_model,
                prompt=prompt,
                size=image_size,
                quality=image_quality,
                style=image_style,
                n=1,  # DALL-E 3 only supports n=1
            )

            # Extract image data
            image_data = response.data[0]

            return {
                "url": image_data.url,
                "revised_prompt": image_data.revised_prompt,
                "model": self.dalle_model,
                "size": image_size,
                "quality": image_quality,
                "style": image_style,
            }

        except Exception as e:
            logger.error(f"DALL-E generation error: {str(e)}")
            return {
                "url": "",
                "error": str(e),
                "model": self.dalle_model,
            }

    async def generate(
        self,
        prompt: str,
        size: Optional[str] = None,
        quality: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Alias for generate_image for compatibility with agent interface.
        
        Args:
            prompt: Image generation prompt
            size: Image size
            quality: Image quality
            
        Returns:
            Dictionary with image URL and metadata
        """
        return await self.generate_image(prompt, size, quality)

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> dict[str, Any]:
        """
        Generate text using GPT models (fallback/alternative to Gemini).
        
        Args:
            prompt: User prompt
            system_prompt: Optional system instruction
            model: GPT model to use
            temperature: Generation temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Dictionary with content and metadata
        """
        if not self._initialized:
            return {
                "content": "",
                "error": "OpenAI client not initialized. Check API key.",
                "model": model,
            }

        try:
            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            messages.append({"role": "user", "content": prompt})

            response = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            content = response.choices[0].message.content

            return {
                "content": content,
                "model": model,
                "tokens_used": response.usage.total_tokens if response.usage else None,
                "metadata": {
                    "finish_reason": response.choices[0].finish_reason,
                },
            }

        except Exception as e:
            logger.error(f"GPT generation error: {str(e)}")
            return {
                "content": "",
                "error": str(e),
                "model": model,
            }

    async def create_image_variation(
        self,
        image_path: str,
        n: int = 1,
        size: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Create variations of an existing image.
        
        Note: This uses DALL-E 2 as DALL-E 3 doesn't support variations.
        
        Args:
            image_path: Path to the source image
            n: Number of variations to generate
            size: Image size
            
        Returns:
            Dictionary with image URLs
        """
        if not self._initialized:
            return {
                "urls": [],
                "error": "OpenAI client not initialized. Check API key.",
            }

        try:
            with open(image_path, "rb") as image_file:
                response = await self._client.images.create_variation(
                    image=image_file,
                    n=n,
                    size=size or "1024x1024",
                )

            urls = [img.url for img in response.data]

            return {
                "urls": urls,
                "count": len(urls),
            }

        except Exception as e:
            logger.error(f"Image variation error: {str(e)}")
            return {
                "urls": [],
                "error": str(e),
            }

    async def edit_image(
        self,
        image_path: str,
        prompt: str,
        mask_path: Optional[str] = None,
        size: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Edit an image with a prompt.
        
        Note: This uses DALL-E 2 as DALL-E 3 doesn't support editing.
        
        Args:
            image_path: Path to the source image
            prompt: Edit instruction
            mask_path: Optional path to mask image
            size: Image size
            
        Returns:
            Dictionary with edited image URL
        """
        if not self._initialized:
            return {
                "url": "",
                "error": "OpenAI client not initialized. Check API key.",
            }

        try:
            with open(image_path, "rb") as image_file:
                mask_file = None
                if mask_path:
                    mask_file = open(mask_path, "rb")

                response = await self._client.images.edit(
                    image=image_file,
                    prompt=prompt,
                    mask=mask_file,
                    size=size or "1024x1024",
                )

                if mask_file:
                    mask_file.close()

            return {
                "url": response.data[0].url,
            }

        except Exception as e:
            logger.error(f"Image edit error: {str(e)}")
            return {
                "url": "",
                "error": str(e),
            }

    def get_supported_sizes(self) -> list[str]:
        """
        Get list of supported image sizes.
        
        Returns:
            List of supported size strings
        """
        return self.SUPPORTED_SIZES.copy()

    def get_model_info(self) -> dict[str, Any]:
        """
        Get information about the current configuration.
        
        Returns:
            Configuration information dictionary
        """
        return {
            "dalle_model": self.dalle_model,
            "initialized": self._initialized,
            "default_size": self.default_image_size,
            "default_quality": self.default_quality,
            "supported_sizes": self.SUPPORTED_SIZES,
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
            # Test with a simple models list call
            models = await self._client.models.list()
            return models is not None
        except Exception:
            return False