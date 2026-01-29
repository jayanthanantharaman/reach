"""
Image Generation Agent for REACH.


This agent creates high-quality visual content using Google Imagen
with optimized prompts for marketing and content purposes.
"""

import logging
from typing import Any, Optional

from .base_agent import AgentConfig, BaseAgent

logger = logging.getLogger(__name__)


class ImageGeneratorAgent(BaseAgent):
    """
    Image Generation Agent that creates visual content using Google Imagen.
    
    This agent:
    - Generates high-quality images using Google Imagen
    - Optimizes prompts for better image generation
    - Creates marketing-appropriate visuals
    - Supports various image styles and aspect ratios
    """

    DEFAULT_SYSTEM_PROMPT = """You are an expert visual content creator and prompt engineer specializing in AI image generation. Your role is to:

1. Create detailed, effective prompts for Google Imagen
2. Understand visual design principles
3. Optimize prompts for marketing and content purposes
4. Ensure brand-appropriate imagery
5. Consider composition, lighting, and style

When creating image prompts:
- Be specific about visual elements, style, and composition
- Include details about lighting, colors, and mood
- Specify the perspective and framing
- Mention any text or typography requirements
- Consider the intended use (blog, social media, etc.)

Image Style Guidelines:
- Professional and polished for business content
- Engaging and eye-catching for social media
- Clean and modern for tech topics
- Warm and relatable for lifestyle content
- Bold and impactful for marketing materials"""

    # Supported aspect ratios for Google Imagen
    SUPPORTED_ASPECT_RATIOS = ["1:1", "16:9", "9:16", "4:3", "3:4"]

    # Image style presets
    STYLE_PRESETS = {
        "professional": "clean, modern, professional, corporate style, high quality",
        "creative": "artistic, creative, vibrant colors, unique perspective",
        "minimalist": "minimalist, simple, clean lines, white space, elegant",
        "bold": "bold, impactful, high contrast, attention-grabbing",
        "warm": "warm tones, inviting, friendly, approachable",
        "tech": "futuristic, digital, technology-focused, sleek",
        "natural": "natural, organic, earthy tones, authentic",
        "luxury": "luxurious, premium, sophisticated, elegant",
    }

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        image_client: Optional[Any] = None,
        system_prompt: Optional[str] = None,
    ):
        """
        Initialize the Image Generator Agent.
        
        Args:
            llm_client: Optional LLM client for prompt optimization
            image_client: Optional image generation client (Google Imagen)
            system_prompt: Optional custom system prompt
        """
        config = AgentConfig(
            name="Image Generation Agent",
            description="Creates high-quality visual content using Google Imagen",
            system_prompt=system_prompt or self.DEFAULT_SYSTEM_PROMPT,
        )
        super().__init__(config, llm_client)
        self.image_client = image_client

    def set_image_client(self, client: Any) -> None:
        """
        Set the image generation client.
        
        Args:
            client: Image generation client (Google Imagen)
        """
        self.image_client = client
        logger.info("Image client set for Image Generator Agent")

    async def generate(
        self,
        user_input: str,
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Generate an image based on user input.
        
        Args:
            user_input: Image description or request
            context: Optional context with style, aspect_ratio, etc.
            
        Returns:
            Image URL or generation result string
        """
        # Extract parameters from context
        context = context or {}
        style = context.get("style", "professional")
        aspect_ratio = context.get("aspect_ratio", "1:1")
        negative_prompt = context.get("negative_prompt")
        optimize_prompt = context.get("optimize_prompt", True)

        # Validate aspect ratio
        if aspect_ratio not in self.SUPPORTED_ASPECT_RATIOS:
            aspect_ratio = "1:1"

        # Optimize the prompt if requested
        if optimize_prompt:
            optimized_prompt = await self.optimize_prompt(user_input, style)
        else:
            optimized_prompt = user_input

        # Generate the image
        result = await self._generate_image(
            prompt=optimized_prompt,
            aspect_ratio=aspect_ratio,
            negative_prompt=negative_prompt,
        )

        return result

    async def optimize_prompt(
        self,
        user_input: str,
        style: str = "professional",
    ) -> str:
        """
        Optimize a user's image request into a detailed Imagen prompt.
        
        Args:
            user_input: User's image description
            style: Desired style preset
            
        Returns:
            Optimized prompt string
        """
        style_description = self.STYLE_PRESETS.get(style, self.STYLE_PRESETS["professional"])

        prompt = f"""Transform this image request into an optimized Google Imagen prompt:

User Request: "{user_input}"
Desired Style: {style_description}

Create a detailed prompt that includes:
1. Main subject and composition
2. Visual style and artistic direction
3. Lighting and color palette
4. Background and environment
5. Mood and atmosphere
6. Technical specifications (if relevant)

Important Guidelines:
- Be specific and descriptive
- Avoid text in images (AI image generators struggle with text)
- Focus on visual elements that convey the message
- Keep the prompt clear and detailed for best results
- Make it appropriate for professional/marketing use

Provide ONLY the optimized prompt, no explanation."""

        response = await self._call_llm(prompt, temperature=0.6, max_tokens=500)

        if response.error:
            # Fall back to enhanced user input
            return f"{user_input}, {style_description}, high quality, detailed"

        return response.content.strip()

    async def _generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "1:1",
        negative_prompt: Optional[str] = None,
    ) -> str:
        """
        Generate an image using Google Imagen.
        
        Args:
            prompt: Image generation prompt
            aspect_ratio: Image aspect ratio
            negative_prompt: What to avoid in the image
            
        Returns:
            Image URL or result message
        """
        if not self.image_client:
            # Return the optimized prompt if no image client
            return f"""**Image Generation Request**

**Optimized Prompt:**
{prompt}

**Settings:**
- Aspect Ratio: {aspect_ratio}
- Negative Prompt: {negative_prompt or 'None'}

*Note: Image generation client not configured. Use this prompt with Google Imagen to generate the image.*"""

        try:
            result = await self.image_client.generate_image(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                negative_prompt=negative_prompt,
            )

            if isinstance(result, dict):
                if result.get("success"):
                    images = result.get("images", [])
                    if images:
                        image = images[0]
                        if "base64" in image:
                            image_url = f"data:{image.get('mime_type', 'image/png')};base64,{image['base64']}"
                        else:
                            image_url = image.get("url", "Image generated successfully")

                        # Return the raw image URL/data URI so UIs can display it directly.
                        if isinstance(image_url, str) and (
                            image_url.startswith("data:image")
                            or image_url.startswith("http")
                        ):
                            return image_url

                        # Fallback to a readable string if no usable URL/data URI.
                        response_parts = [
                            "**Generated Image**\n\n",
                            f"Image URL: {image_url}",
                            f"\n\n**Prompt Used:** {prompt}",
                            f"\n**Aspect Ratio:** {aspect_ratio}",
                        ]
                        return "\n".join(response_parts)
                    else:
                        return f"Image generated but no image data returned.\n\n**Prompt:** {prompt}"
                else:
                    error = result.get("error", "Unknown error")
                    return f"""**Image Generation Failed**

Error: {error}

**Original Prompt:**
{prompt}

*Please try again or check your API configuration.*"""

            return str(result)

        except Exception as e:
            logger.error(f"Image generation error: {str(e)}")
            return f"""**Image Generation Failed**

Error: {str(e)}

**Original Prompt:**
{prompt}

*Please try again or use this prompt directly with Google Imagen.*"""

    async def generate_variations(
        self,
        description: str,
        num_variations: int = 3,
        context: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, str]]:
        """
        Generate multiple prompt variations for an image concept.
        
        Args:
            description: Base image description
            num_variations: Number of variations to generate
            context: Optional context
            
        Returns:
            List of optimized prompts
        """
        styles = list(self.STYLE_PRESETS.keys())[:num_variations]
        variations = []

        for style in styles:
            optimized = await self.optimize_prompt(description, style)
            variations.append({
                "style": style,
                "prompt": optimized,
            })

        return variations

    async def suggest_images_for_content(
        self,
        content: str,
        content_type: str = "blog",
        num_suggestions: int = 3,
    ) -> list[dict[str, str]]:
        """
        Suggest image ideas for a piece of content.
        
        Args:
            content: The content to create images for
            content_type: Type of content (blog, linkedin, etc.)
            num_suggestions: Number of image suggestions
            
        Returns:
            List of image suggestion dictionaries
        """
        prompt = f"""Analyze this {content_type} content and suggest {num_suggestions} image ideas:

Content:
{content[:1500]}

For each image suggestion provide:
1. Image concept (what the image should show)
2. Purpose (how it supports the content)
3. Recommended style
4. Placement suggestion (header, inline, etc.)

Format each suggestion clearly."""

        response = await self._call_llm(prompt, temperature=0.7)

        if response.error:
            return [{"concept": "Unable to generate suggestions", "purpose": "", "style": ""}]

        # Parse suggestions
        return self._parse_image_suggestions(response.content, num_suggestions)

    def _parse_image_suggestions(
        self,
        response: str,
        num_suggestions: int,
    ) -> list[dict[str, str]]:
        """
        Parse image suggestions from LLM response.
        
        Args:
            response: LLM response
            num_suggestions: Expected number of suggestions
            
        Returns:
            List of suggestion dictionaries
        """
        suggestions = []
        current_suggestion = {"concept": "", "purpose": "", "style": "", "placement": ""}

        lines = response.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            line_lower = line.lower()

            # Check for new suggestion
            if any(
                marker in line_lower
                for marker in ["suggestion", "image 1", "image 2", "image 3", "1.", "2.", "3."]
            ):
                if current_suggestion["concept"]:
                    suggestions.append(current_suggestion)
                    current_suggestion = {"concept": "", "purpose": "", "style": "", "placement": ""}

            # Parse fields
            if "concept:" in line_lower or "image:" in line_lower:
                current_suggestion["concept"] = line.split(":", 1)[1].strip()
            elif "purpose:" in line_lower:
                current_suggestion["purpose"] = line.split(":", 1)[1].strip()
            elif "style:" in line_lower:
                current_suggestion["style"] = line.split(":", 1)[1].strip()
            elif "placement:" in line_lower:
                current_suggestion["placement"] = line.split(":", 1)[1].strip()
            elif not current_suggestion["concept"] and line:
                current_suggestion["concept"] = line

        if current_suggestion["concept"]:
            suggestions.append(current_suggestion)

        return suggestions[:num_suggestions] if suggestions else [{"concept": response, "purpose": "", "style": ""}]

    async def create_social_media_image_prompt(
        self,
        topic: str,
        platform: str = "linkedin",
    ) -> str:
        """
        Create an optimized prompt for social media images.
        
        Args:
            topic: Image topic
            platform: Social media platform
            
        Returns:
            Optimized prompt string
        """
        platform_specs = {
            "linkedin": {
                "style": "professional, corporate, clean",
                "aspect": "1:1 or 16:9",
                "mood": "trustworthy, authoritative",
            },
            "twitter": {
                "style": "eye-catching, bold, modern",
                "aspect": "16:9",
                "mood": "engaging, shareable",
            },
            "instagram": {
                "style": "visually stunning, aesthetic",
                "aspect": "1:1 or 9:16",
                "mood": "inspiring, beautiful",
            },
            "facebook": {
                "style": "friendly, relatable, warm",
                "aspect": "16:9",
                "mood": "community-focused, engaging",
            },
        }

        specs = platform_specs.get(platform, platform_specs["linkedin"])

        prompt = f"""Create a Google Imagen prompt for a {platform} image about: "{topic}"

Platform Requirements:
- Style: {specs['style']}
- Aspect Ratio: {specs['aspect']}
- Mood: {specs['mood']}

The image should:
- Be scroll-stopping and attention-grabbing
- Work well at small sizes (mobile viewing)
- Not contain any text (text will be added separately)
- Be appropriate for professional audiences
- Support the topic without being too literal

Provide ONLY the optimized prompt."""

        response = await self._call_llm(prompt, temperature=0.7, max_tokens=400)

        if response.error:
            return f"Professional {platform} image about {topic}, {specs['style']}, high quality"

        return response.content.strip()

    async def create_blog_header_prompt(
        self,
        blog_title: str,
        blog_summary: str,
    ) -> str:
        """
        Create an optimized prompt for a blog header image.
        
        Args:
            blog_title: Title of the blog post
            blog_summary: Brief summary of the blog content
            
        Returns:
            Optimized prompt string
        """
        prompt = f"""Create a Google Imagen prompt for a blog header image:

Blog Title: {blog_title}
Summary: {blog_summary}

Requirements:
- Wide landscape format (16:9 aspect ratio)
- Professional and polished
- Visually represents the topic
- Works well with text overlay
- Clean composition with space for title
- No text in the image itself

The image should be:
- Eye-catching but not distracting
- Relevant to the content
- Appropriate for professional audiences
- High quality and detailed

Provide ONLY the optimized prompt."""

        response = await self._call_llm(prompt, temperature=0.6, max_tokens=400)

        if response.error:
            return f"Professional blog header image representing {blog_title}, wide landscape, clean composition, high quality"

        return response.content.strip()

    def get_recommended_aspect_ratio(self, use_case: str) -> str:
        """
        Get recommended aspect ratio for a use case.
        
        Args:
            use_case: The intended use case
            
        Returns:
            Recommended aspect ratio string
        """
        aspect_ratio_recommendations = {
            "blog_header": "16:9",
            "social_square": "1:1",
            "linkedin_post": "1:1",
            "twitter_post": "16:9",
            "instagram_post": "1:1",
            "instagram_story": "9:16",
            "pinterest": "9:16",
            "thumbnail": "1:1",
            "portrait": "3:4",
            "landscape": "4:3",
            "default": "1:1",
        }

        return aspect_ratio_recommendations.get(use_case, aspect_ratio_recommendations["default"])

    def get_style_presets(self) -> dict[str, str]:
        """
        Get available style presets.
        
        Returns:
            Dictionary of style presets
        """
        return self.STYLE_PRESETS.copy()

    def get_supported_aspect_ratios(self) -> list[str]:
        """
        Get list of supported aspect ratios.
        
        Returns:
            List of supported aspect ratios
        """
        return self.SUPPORTED_ASPECT_RATIOS.copy()
