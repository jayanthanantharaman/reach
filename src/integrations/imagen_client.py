"""
Google Imagen Client for REACH.


This module provides integration with Google's Imagen API
for image generation capabilities.
"""

import logging
from typing import Any, Optional

import google.generativeai as genai

from ..core.config import settings

logger = logging.getLogger(__name__)


class ImagenClient:
    """
    Client for Google Imagen image generation.
    
    Uses Google's Imagen model for generating high-quality images
    from text prompts.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "imagen-3.0-generate-002",
    ):
        """
        Initialize the Imagen client.
        
        Args:
            api_key: Google API key (uses settings if not provided)
            model: Imagen model to use
        """
        self.api_key = api_key or settings.google_api_key
        self.model = model
        self._configure_client()

    def _configure_client(self) -> None:
        """Configure the Google Generative AI client."""
        if self.api_key:
            genai.configure(api_key=self.api_key)
            logger.info(f"Imagen client configured with model: {self.model}")
        else:
            logger.warning("No Google API key provided for Imagen")

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        aspect_ratio: str = "1:1",
        number_of_images: int = 1,
        safety_filter_level: str = "block_some",
        person_generation: str = "allow_adult",
    ) -> dict[str, Any]:
        """
        Generate an image using Google Imagen.
        
        Args:
            prompt: Text description of the image to generate
            negative_prompt: What to avoid in the image
            aspect_ratio: Image aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4)
            number_of_images: Number of images to generate (1-4)
            safety_filter_level: Safety filter level
            person_generation: Person generation setting
            
        Returns:
            Dictionary with image data and metadata
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "Google API key not configured",
                "images": [],
            }

        try:
            # Get the Imagen model
            imagen = genai.ImageGenerationModel(self.model)

            # Generate the image
            result = imagen.generate_images(
                prompt=prompt,
                negative_prompt=negative_prompt,
                number_of_images=number_of_images,
                aspect_ratio=aspect_ratio,
                safety_filter_level=safety_filter_level,
                person_generation=person_generation,
            )

            # Process results
            images = []
            for idx, image in enumerate(result.images):
                image_data = {
                    "index": idx,
                    "mime_type": "image/png",
                }

                # Save image to bytes
                if hasattr(image, "_pil_image"):
                    import io
                    import base64

                    buffer = io.BytesIO()
                    image._pil_image.save(buffer, format="PNG")
                    image_data["base64"] = base64.b64encode(buffer.getvalue()).decode()
                    image_data["size"] = len(buffer.getvalue())

                images.append(image_data)

            logger.info(f"Generated {len(images)} image(s) with Imagen")

            return {
                "success": True,
                "images": images,
                "prompt": prompt,
                "model": self.model,
                "aspect_ratio": aspect_ratio,
            }

        except Exception as e:
            logger.error(f"Imagen generation error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "images": [],
            }

    async def generate_image_url(
        self,
        prompt: str,
        aspect_ratio: str = "1:1",
        **kwargs,
    ) -> Optional[str]:
        """
        Generate an image and return as base64 data URL.
        
        Args:
            prompt: Text description of the image
            aspect_ratio: Image aspect ratio
            **kwargs: Additional generation parameters
            
        Returns:
            Base64 data URL of the generated image, or None on failure
        """
        result = await self.generate_image(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            number_of_images=1,
            **kwargs,
        )

        if result["success"] and result["images"]:
            image = result["images"][0]
            if "base64" in image:
                return f"data:{image['mime_type']};base64,{image['base64']}"

        return None

    async def edit_image(
        self,
        prompt: str,
        base_image: bytes,
        mask_image: Optional[bytes] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Edit an existing image using Imagen.
        
        Args:
            prompt: Edit instructions
            base_image: Original image bytes
            mask_image: Optional mask for inpainting
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with edited image data
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "Google API key not configured",
                "images": [],
            }

        try:
            # Get the Imagen model for editing
            imagen = genai.ImageGenerationModel(self.model)

            # Create image object from bytes
            from PIL import Image
            import io

            base_pil = Image.open(io.BytesIO(base_image))

            mask_pil = None
            if mask_image:
                mask_pil = Image.open(io.BytesIO(mask_image))

            # Edit the image
            result = imagen.edit_image(
                prompt=prompt,
                base_image=base_pil,
                mask=mask_pil,
                **kwargs,
            )

            # Process results
            images = []
            for idx, image in enumerate(result.images):
                image_data = {
                    "index": idx,
                    "mime_type": "image/png",
                }

                if hasattr(image, "_pil_image"):
                    import base64

                    buffer = io.BytesIO()
                    image._pil_image.save(buffer, format="PNG")
                    image_data["base64"] = base64.b64encode(buffer.getvalue()).decode()

                images.append(image_data)

            return {
                "success": True,
                "images": images,
                "prompt": prompt,
            }

        except Exception as e:
            logger.error(f"Imagen edit error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "images": [],
            }

    def get_supported_aspect_ratios(self) -> list[str]:
        """Get list of supported aspect ratios."""
        return ["1:1", "16:9", "9:16", "4:3", "3:4"]

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the current model."""
        return {
            "model": self.model,
            "provider": "Google",
            "capabilities": [
                "text-to-image",
                "image-editing",
                "inpainting",
            ],
            "supported_aspect_ratios": self.get_supported_aspect_ratios(),
            "max_images_per_request": 4,
        }