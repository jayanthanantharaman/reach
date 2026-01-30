"""
Image Prompt Agent for REACH.

This intermediary agent reads content (blogs, articles, etc.) and generates
optimized image prompts based on the content's summary and key themes.
"""

import logging
import re
from typing import Any, Optional

from .base_agent import AgentConfig, BaseAgent

logger = logging.getLogger(__name__)


class ImagePromptAgent(BaseAgent):
    """
    Image Prompt Agent that generates optimized image prompts from content.
    
    This agent:
    - Reads and analyzes blog/article content
    - Extracts key themes, topics, and visual elements
    - Generates optimized prompts for image generation
    - Ensures prompts are suitable for real estate imagery
    """

    DEFAULT_SYSTEM_PROMPT = """You are an expert at creating image generation prompts for real estate content. Your role is to:

1. Analyze blog posts, articles, and other content
2. Extract the main theme, topic, and visual elements
3. Create detailed, descriptive prompts for image generation
4. Focus on real estate, property, and home-related imagery

When creating image prompts:
- Be specific about the scene, lighting, and composition
- Include architectural and design details
- Specify the mood and atmosphere
- Avoid text, logos, or watermarks in the description
- Focus on photorealistic, professional real estate photography style
- Consider the aspect ratio (16:9 for blog headers, 1:1 for social media)

Your prompts should result in high-quality, professional images suitable for real estate marketing."""

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        system_prompt: Optional[str] = None,
    ):
        """
        Initialize the Image Prompt Agent.
        
        Args:
            llm_client: Optional LLM client instance
            system_prompt: Optional custom system prompt
        """
        config = AgentConfig(
            name="Image Prompt Agent",
            description="Generates optimized image prompts from content",
            system_prompt=system_prompt or self.DEFAULT_SYSTEM_PROMPT,
        )
        super().__init__(config, llm_client)

    async def generate(
        self,
        user_input: str,
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Generate an optimized image prompt from content.
        
        Args:
            user_input: The content to analyze (blog post, article, etc.)
            context: Optional context with additional parameters
                - content_type: str - Type of content (blog, article, etc.)
                - aspect_ratio: str - Target aspect ratio (16:9, 1:1, etc.)
                - style: str - Image style (professional, luxury, modern, etc.)
                - focus: str - What to focus on in the image
            
        Returns:
            Optimized image generation prompt
        """
        context = context or {}
        content_type = context.get("content_type", "blog")
        aspect_ratio = context.get("aspect_ratio", "16:9")
        style = context.get("style", "professional")
        focus = context.get("focus", "")
        
        # Extract title and summary from content
        title = self._extract_title(user_input)
        summary = self._extract_summary(user_input)
        key_themes = self._extract_key_themes(user_input)
        
        # Build the prompt generation request
        prompt = self._build_prompt_request(
            title=title,
            summary=summary,
            key_themes=key_themes,
            content_type=content_type,
            aspect_ratio=aspect_ratio,
            style=style,
            focus=focus,
        )
        
        # Generate the image prompt
        response = await self._call_llm(prompt, temperature=0.7, max_tokens=500)
        
        if response.error:
            # Fallback to a basic prompt
            return self._create_fallback_prompt(title, style)
        
        # Clean and validate the prompt
        image_prompt = self._clean_prompt(response.content)
        
        logger.info(f"Generated image prompt: {image_prompt[:100]}...")
        
        return image_prompt

    async def generate_from_blog(
        self,
        blog_content: str,
        style: str = "professional",
        aspect_ratio: str = "16:9",
    ) -> str:
        """
        Generate an image prompt specifically for a blog post.
        
        Args:
            blog_content: The full blog post content
            style: Image style preset
            aspect_ratio: Target aspect ratio
            
        Returns:
            Optimized image generation prompt for blog header
        """
        return await self.generate(
            user_input=blog_content,
            context={
                "content_type": "blog",
                "aspect_ratio": aspect_ratio,
                "style": style,
            },
        )

    async def generate_from_summary(
        self,
        title: str,
        summary: str,
        style: str = "professional",
        aspect_ratio: str = "16:9",
    ) -> str:
        """
        Generate an image prompt from a title and summary.
        
        Args:
            title: Content title
            summary: Content summary
            style: Image style preset
            aspect_ratio: Target aspect ratio
            
        Returns:
            Optimized image generation prompt
        """
        prompt = f"""Create a detailed image generation prompt for a real estate blog header image.

Blog Title: {title}
Blog Summary: {summary}

Requirements:
- Style: {style} real estate photography
- Aspect Ratio: {aspect_ratio} (wide landscape for blog header)
- Focus on visual elements that represent the blog topic
- Professional, high-quality, photorealistic
- No text, logos, or watermarks
- Suitable for real estate marketing

Generate ONLY the image prompt, nothing else. The prompt should be 2-3 sentences describing the scene in detail."""

        response = await self._call_llm(prompt, temperature=0.7, max_tokens=300)
        
        if response.error:
            return self._create_fallback_prompt(title, style)
        
        return self._clean_prompt(response.content)

    def _extract_title(self, content: str) -> str:
        """
        Extract the title from content.
        
        Args:
            content: Content to analyze
            
        Returns:
            Extracted title or default
        """
        # Look for H1 heading
        h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if h1_match:
            return h1_match.group(1).strip()
        
        # Look for **Title** pattern
        title_match = re.search(r"\*\*Title[:\s]*\*\*\s*(.+)", content, re.IGNORECASE)
        if title_match:
            return title_match.group(1).strip()
        
        # Take first non-empty line
        for line in content.split("\n"):
            line = line.strip()
            if line and not line.startswith("*") and not line.startswith("-"):
                return line[:100]
        
        return "Real Estate Property"

    def _extract_summary(self, content: str) -> str:
        """
        Extract a summary from content.
        
        Args:
            content: Content to analyze
            
        Returns:
            Extracted summary or default
        """
        # Look for meta description
        meta_match = re.search(
            r"\*\*Meta Description[:\s]*\*\*\s*(.+)",
            content,
            re.IGNORECASE,
        )
        if meta_match:
            return meta_match.group(1).strip()
        
        # Look for introduction section
        intro_match = re.search(
            r"(?:introduction|intro)[:\s]*\n+(.+?)(?:\n\n|\n#)",
            content,
            re.IGNORECASE | re.DOTALL,
        )
        if intro_match:
            return intro_match.group(1).strip()[:300]
        
        # Take first substantial paragraph after title
        paragraphs = content.split("\n\n")
        for para in paragraphs[1:3]:
            para = para.strip()
            if para and not para.startswith("#") and len(para) > 50:
                return para[:300]
        
        return "Professional real estate content"

    def _extract_key_themes(self, content: str) -> list[str]:
        """
        Extract key themes from content.
        
        Args:
            content: Content to analyze
            
        Returns:
            List of key themes
        """
        themes = []
        
        # Extract H2 headings as themes
        h2_matches = re.findall(r"^##\s+(.+)$", content, re.MULTILINE)
        themes.extend([h.strip() for h in h2_matches[:5]])
        
        # Look for common real estate keywords
        real_estate_keywords = [
            "home", "house", "property", "real estate", "luxury", "modern",
            "staging", "buying", "selling", "investment", "market", "mortgage",
            "interior", "exterior", "kitchen", "bathroom", "bedroom", "garden",
            "pool", "condo", "apartment", "townhouse", "villa", "commercial",
        ]
        
        content_lower = content.lower()
        for keyword in real_estate_keywords:
            if keyword in content_lower and keyword not in [t.lower() for t in themes]:
                themes.append(keyword)
                if len(themes) >= 10:
                    break
        
        return themes

    def _build_prompt_request(
        self,
        title: str,
        summary: str,
        key_themes: list[str],
        content_type: str,
        aspect_ratio: str,
        style: str,
        focus: str,
    ) -> str:
        """
        Build the prompt generation request.
        
        Args:
            title: Content title
            summary: Content summary
            key_themes: List of key themes
            content_type: Type of content
            aspect_ratio: Target aspect ratio
            style: Image style
            focus: What to focus on
            
        Returns:
            Formatted prompt request
        """
        themes_str = ", ".join(key_themes[:5]) if key_themes else "real estate"
        
        prompt = f"""Analyze this content and create an optimized image generation prompt:

Content Title: {title}
Content Summary: {summary}
Key Themes: {themes_str}
Content Type: {content_type}

Image Requirements:
- Style: {style} real estate photography
- Aspect Ratio: {aspect_ratio}
- Focus: {focus if focus else 'Main theme of the content'}

Create a detailed, descriptive prompt for generating a professional real estate image that:
1. Visually represents the main topic of the content
2. Is suitable for a {content_type} header image
3. Uses {style} photography style
4. Does NOT include any text, logos, or watermarks
5. Is photorealistic and high-quality

Generate ONLY the image prompt (2-3 sentences), nothing else."""

        return prompt

    def _clean_prompt(self, prompt: str) -> str:
        """
        Clean and validate the generated prompt.
        
        Args:
            prompt: Raw generated prompt
            
        Returns:
            Cleaned prompt
        """
        # Remove any markdown formatting
        prompt = re.sub(r"\*\*|\*|__|_", "", prompt)
        
        # Remove any "Image prompt:" or similar prefixes
        prompt = re.sub(r"^(?:image\s*prompt|prompt)[:\s]*", "", prompt, flags=re.IGNORECASE)
        
        # Remove quotes if the entire prompt is quoted
        prompt = prompt.strip().strip('"\'')
        
        # Ensure it doesn't contain instructions to add text
        text_patterns = [
            r"with\s+text",
            r"include\s+text",
            r"add\s+text",
            r"with\s+logo",
            r"include\s+logo",
            r"with\s+watermark",
        ]
        for pattern in text_patterns:
            prompt = re.sub(pattern, "", prompt, flags=re.IGNORECASE)
        
        # Add real estate context if missing
        if "real estate" not in prompt.lower() and "property" not in prompt.lower() and "home" not in prompt.lower():
            prompt = f"Professional real estate photography: {prompt}"
        
        return prompt.strip()

    def _create_fallback_prompt(self, title: str, style: str) -> str:
        """
        Create a fallback prompt when generation fails.
        
        Args:
            title: Content title
            style: Image style
            
        Returns:
            Fallback image prompt
        """
        # Extract key words from title
        title_words = title.lower().split()
        
        # Common real estate image elements
        elements = {
            "home": "beautiful modern home exterior with landscaped garden",
            "house": "stunning residential property with curb appeal",
            "luxury": "luxurious high-end property with elegant architecture",
            "staging": "professionally staged living room with modern furniture",
            "buying": "welcoming home entrance with open door",
            "selling": "attractive property exterior ready for sale",
            "investment": "commercial real estate building with modern design",
            "market": "aerial view of residential neighborhood",
            "interior": "bright and airy interior living space",
            "kitchen": "modern kitchen with premium appliances",
            "bathroom": "spa-like bathroom with elegant fixtures",
            "garden": "beautiful landscaped garden with outdoor living space",
            "pool": "stunning backyard with swimming pool",
            "condo": "modern condominium building exterior",
            "apartment": "contemporary apartment interior",
        }
        
        # Find matching element
        for word in title_words:
            if word in elements:
                return f"{style.capitalize()} real estate photography: {elements[word]}, natural lighting, high quality, no text or watermarks"
        
        # Default fallback
        return f"{style.capitalize()} real estate photography: beautiful modern home exterior with landscaped garden, natural lighting, high quality, no text or watermarks"