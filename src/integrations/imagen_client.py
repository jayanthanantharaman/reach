"""
Google Imagen Client for REACH.


This module provides integration with Google's Imagen API
for image generation capabilities using the new google-genai package.
"""

import base64
import io
import logging
from typing import Any, Optional

from google import genai
from google.genai import types

from ..core.config import get_settings

logger = logging.getLogger(__name__)


class ImagenClient:
    """
    Client for Google Imagen image generation.
    
    Uses Google's Imagen model for generating high-quality images
    from text prompts via the new google-genai package.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "imagen-4.0-generate-001",
    ):
        """
        Initialize the Imagen client.
        
        Args:
            api_key: Google API key (uses settings if not provided)
            model: Imagen model to use
        """
        settings = get_settings()
        self.api_key = api_key or settings.google_api_key
        self.model = model
        self._client = None
        self._initialized = False
        self._configure_client()

    def _configure_client(self) -> None:
        """Configure the Google GenAI client."""
        if self.api_key:
            try:
                self._client = genai.Client(api_key=self.api_key)
                self._initialized = True
                logger.info(f"Imagen client configured with model: {self.model}")
            except Exception as e:
                logger.error(f"Failed to initialize Imagen client: {str(e)}")
                self._initialized = False
        else:
            logger.warning("No Google API key provided for Imagen")

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        aspect_ratio: str = "1:1",
        number_of_images: int = 1,
        safety_filter_level: str = "block_low_and_above",
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
        if not self._initialized or not self._client:
            return {
                "success": False,
                "error": "Google API key not configured or client not initialized",
                "images": [],
            }

        try:
            safety_level = safety_filter_level
            if safety_level != "block_low_and_above":
                logger.warning(
                    "Unsupported safety_filter_level '%s'; falling back to 'block_low_and_above'.",
                    safety_level,
                )
                safety_level = "block_low_and_above"

            # Build the image generation config
            config = types.GenerateImagesConfig(
                number_of_images=number_of_images,
                aspect_ratio=aspect_ratio,
                safety_filter_level=safety_level,
                person_generation=person_generation,
                negative_prompt=negative_prompt,
            )

            # Generate the image using the new API
            response = self._client.models.generate_images(
                model=self.model,
                prompt=prompt,
                config=config,
            )

            # Process results
            images = []
            if response.generated_images:
                for idx, generated_image in enumerate(response.generated_images):
                    image_data = {
                        "index": idx,
                        "mime_type": "image/png",
                    }

                    # Get image bytes from the response
                    if hasattr(generated_image, "image") and generated_image.image:
                        image_obj = generated_image.image
                        
                        # Try to get image data
                        if hasattr(image_obj, "image_bytes") and image_obj.image_bytes:
                            image_data["base64"] = base64.b64encode(image_obj.image_bytes).decode()
                            image_data["size"] = len(image_obj.image_bytes)
                        elif hasattr(image_obj, "_pil_image") and image_obj._pil_image:
                            # Fallback to PIL image if available
                            buffer = io.BytesIO()
                            image_obj._pil_image.save(buffer, format="PNG")
                            image_bytes = buffer.getvalue()
                            image_data["base64"] = base64.b64encode(image_bytes).decode()
                            image_data["size"] = len(image_bytes)

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
        if not self._initialized or not self._client:
            return {
                "success": False,
                "error": "Google API key not configured or client not initialized",
                "images": [],
            }

        try:
            from PIL import Image

            # Create image object from bytes
            base_pil = Image.open(io.BytesIO(base_image))

            mask_pil = None
            if mask_image:
                mask_pil = Image.open(io.BytesIO(mask_image))

            # Build edit config
            config = types.EditImageConfig(
                edit_mode="inpainting" if mask_pil else "product_image",
                **kwargs,
            )

            # Create the reference image
            reference_image = types.RawReferenceImage(
                reference_image=base_pil,
            )

            # Edit the image using the new API
            response = self._client.models.edit_image(
                model=self.model,
                prompt=prompt,
                reference_images=[reference_image],
                config=config,
            )

            # Process results
            images = []
            if response.generated_images:
                for idx, generated_image in enumerate(response.generated_images):
                    image_data = {
                        "index": idx,
                        "mime_type": "image/png",
                    }

                    if hasattr(generated_image, "image") and generated_image.image:
                        image_obj = generated_image.image
                        
                        if hasattr(image_obj, "image_bytes") and image_obj.image_bytes:
                            image_data["base64"] = base64.b64encode(image_obj.image_bytes).decode()
                        elif hasattr(image_obj, "_pil_image") and image_obj._pil_image:
                            buffer = io.BytesIO()
                            image_obj._pil_image.save(buffer, format="PNG")
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
            "initialized": self._initialized,
            "capabilities": [
                "text-to-image",
                "image-editing",
                "inpainting",
            ],
            "supported_aspect_ratios": self.get_supported_aspect_ratios(),
            "max_images_per_request": 4,
        }
