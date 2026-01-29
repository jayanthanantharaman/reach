"""
Instagram Caption Writer Agent for REACH.


This agent generates engaging Instagram captions with relevant hashtags
for real estate images and property content.
"""

import logging
from typing import Any, Optional

from .base_agent import AgentConfig, BaseAgent

logger = logging.getLogger(__name__)


class InstagramWriterAgent(BaseAgent):
    """
    Agent for generating Instagram captions for real estate content.
    
    This agent creates engaging, informative captions with relevant
    hashtags optimized for real estate Instagram marketing.
    """

    def __init__(self, llm_client: Any = None):
        """
        Initialize the Instagram Writer Agent.
        
        Args:
            llm_client: LLM client for content generation
        """
        config = AgentConfig(
            name="Instagram Writer Agent",
            description="Generates engaging Instagram captions with hashtags for real estate content",
            system_prompt=self._get_system_prompt(),
        )
        super().__init__(config, llm_client)

        # Real estate hashtag categories
        self.hashtag_categories = {
            "general": [
                "#realestate", "#realtor", "#property", "#home", "#house",
                "#realtorlife", "#realestateagent", "#homesweethome",
            ],
            "buying": [
                "#homebuyer", "#firsttimehomebuyer", "#househunting",
                "#dreamhome", "#newhome", "#homeownership",
            ],
            "selling": [
                "#forsale", "#homeforsale", "#justlisted", "#newlisting",
                "#openhouse", "#sellingahome",
            ],
            "luxury": [
                "#luxuryrealestate", "#luxuryhomes", "#luxuryliving",
                "#milliondollarlisting", "#luxuryproperty", "#mansions",
            ],
            "investment": [
                "#realestateinvesting", "#investmentproperty", "#passiveincome",
                "#propertyinvestment", "#rentalincome", "#realestateinvestor",
            ],
            "location": [
                "#localrealestate", "#neighborhood", "#community",
                "#cityliving", "#suburbanlife",
            ],
            "interior": [
                "#interiordesign", "#homedecor", "#homedesign",
                "#modernhome", "#homestaging", "#interiors",
            ],
            "exterior": [
                "#curbappeal", "#landscaping", "#outdoorliving",
                "#backyard", "#frontyard", "#exteriordesign",
            ],
        }

    def _get_system_prompt(self) -> str:
        """Get the system prompt for Instagram caption generation."""
        return """You are an expert Instagram content creator specializing in real estate marketing.
Your role is to create engaging, scroll-stopping Instagram captions that:

1. CAPTURE ATTENTION: Start with a hook that makes people stop scrolling
2. TELL A STORY: Connect emotionally with the audience
3. PROVIDE VALUE: Share useful information about the property or real estate tips
4. INCLUDE CTA: End with a clear call-to-action
5. USE EMOJIS: Strategically place emojis to break up text and add visual appeal
6. ALWAYS INCLUDE HASHTAGS: Include 20-30 relevant, high-performing real estate hashtags

**CRITICAL REQUIREMENTS:**
- Caption text MUST be 150 words or less (excluding hashtags)
- ALWAYS include 20-30 hashtags at the end
- Hashtags should be separated from caption by a blank line

Caption Structure:
- Hook (1 line): Attention-grabbing opening with emoji
- Body (2-3 lines): Key property highlights or value proposition
- CTA (1 line): Clear call-to-action
- Hashtags: 20-30 relevant hashtags (REQUIRED)

Tone: Professional yet approachable, enthusiastic but not salesy.
Focus on benefits and lifestyle, not just features.
Keep it concise - Instagram users prefer shorter, punchier captions."""

    async def generate(
        self,
        prompt: str,
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Generate an Instagram caption for real estate content.
        
        Args:
            prompt: Description of the image or property
            context: Optional context including image details
            
        Returns:
            Instagram caption with hashtags (max 150 words + hashtags)
        """
        context = context or {}

        # Extract image context if available
        image_description = context.get("image_description", "")
        property_type = context.get("property_type", "")
        location = context.get("location", "")
        price = context.get("price", "")
        features = context.get("features", [])
        caption_style = context.get("caption_style", "Professional")

        # Build the generation prompt with strict word limit
        generation_prompt = f"""Create a SHORT, engaging Instagram caption for the following real estate content:

**Content Description:** {prompt}

{f"**Image Description:** {image_description}" if image_description else ""}
{f"**Property Type:** {property_type}" if property_type else ""}
{f"**Location:** {location}" if location else ""}
{f"**Price:** {price}" if price else ""}
{f"**Key Features:** {', '.join(features)}" if features else ""}
{f"**Style:** {caption_style}" if caption_style else ""}

**STRICT REQUIREMENTS:**
1. Caption text MUST be 150 words or LESS (excluding hashtags)
2. Start with an attention-grabbing hook (use 1-2 emojis)
3. Include 2-3 sentences highlighting key benefits
4. End with a clear call-to-action
5. MUST include 20-30 relevant hashtags at the end

**FORMAT:**
[Caption text - max 150 words]

[Blank line]

[20-30 hashtags separated by spaces]

Keep it concise and punchy - Instagram users prefer shorter captions!"""

        try:
            response = await self._call_llm(
                prompt=generation_prompt,
                system_prompt=self._get_system_prompt(),
            )

            if response.error:
                raise RuntimeError(response.error)

            content = response.content.strip()
            if not content:
                content = self._build_fallback_caption(prompt, context)

            # If the model returned only hashtags, prepend a fallback caption.
            if content and self._is_hashtags_only(content):
                fallback_caption = self._build_fallback_caption(prompt, context)
                content = f"{fallback_caption}\n\n{content}"

            # Ensure hashtags are included.
            if "#" not in content:
                hashtags = self._generate_hashtags(prompt, context)
                content = f"{content}\n\n{hashtags}"

            # Validate and enforce word limit on caption (excluding hashtags)
            content = self._enforce_word_limit(content, max_words=150)

            return content

        except Exception as e:
            logger.error(f"Instagram caption generation failed: {str(e)}")
            raise

    def _enforce_word_limit(self, response: str, max_words: int = 150) -> str:
        """
        Enforce word limit on caption while preserving hashtags.
        
        Args:
            response: Full response with caption and hashtags
            max_words: Maximum words for caption (excluding hashtags)
            
        Returns:
            Response with enforced word limit
        """
        # Split caption and hashtags
        parts = response.split("\n\n")
        
        # Find hashtags section (contains #)
        hashtag_section = ""
        caption_parts = []
        
        for part in parts:
            if "#" in part and part.count("#") > 5:  # Likely hashtag section
                hashtag_section = part
            else:
                caption_parts.append(part)
        
        caption = "\n\n".join(caption_parts).strip()
        
        # Count words in caption (excluding hashtags)
        words = caption.split()
        
        if len(words) > max_words:
            # Truncate to max words and add ellipsis
            truncated_words = words[:max_words]
            caption = " ".join(truncated_words)
            
            # Ensure it ends properly (not mid-sentence if possible)
            if not caption.endswith((".", "!", "?")):
                caption = caption.rstrip(",;:-") + "..."
            
            logger.info(f"Caption truncated from {len(words)} to {max_words} words")
        
        # Ensure we have hashtags
        if not hashtag_section:
            hashtag_section = self._generate_hashtags(caption, {})
        
        return f"{caption}\n\n{hashtag_section}"

    async def generate_for_image(
        self,
        image_prompt: str,
        image_url: Optional[str] = None,
        property_details: Optional[dict[str, Any]] = None,
    ) -> dict[str, str]:
        """
        Generate an Instagram caption specifically for a generated image.
        
        Args:
            image_prompt: The prompt used to generate the image
            image_url: URL of the generated image (if available)
            property_details: Additional property details
            
        Returns:
            Dictionary with caption and hashtags
        """
        property_details = property_details or {}

        context = {
            "image_description": image_prompt,
            **property_details,
        }

        caption = await self.generate(
            f"Instagram caption for real estate image: {image_prompt}",
            context=context,
        )

        # Split caption and hashtags
        parts = caption.rsplit("\n\n", 1)
        main_caption = parts[0]
        hashtags = parts[1] if len(parts) > 1 and "#" in parts[1] else self._generate_hashtags(image_prompt, context)

        return {
            "caption": main_caption,
            "hashtags": hashtags,
            "full_post": caption,
            "image_url": image_url,
        }

    async def generate_variations(
        self,
        prompt: str,
        num_variations: int = 3,
        context: Optional[dict[str, Any]] = None,
    ) -> list[str]:
        """
        Generate multiple caption variations for A/B testing.
        
        Args:
            prompt: Description of the content
            num_variations: Number of variations to generate
            context: Optional context
            
        Returns:
            List of caption variations
        """
        context = context or {}

        variation_prompt = f"""Create {num_variations} different Instagram caption variations for:

**Content:** {prompt}

Each variation should have a different:
1. Hook style (question, statement, emoji-heavy, etc.)
2. Tone (professional, casual, luxury, friendly)
3. CTA approach (DM, comment, link in bio, etc.)

Separate each variation with "---"
Include hashtags with each variation."""

        try:
            response = await self.llm_client.generate(
                prompt=variation_prompt,
                system_prompt=self._get_system_prompt(),
            )

            variations = [v.strip() for v in response.split("---") if v.strip()]
            return variations[:num_variations]

        except Exception as e:
            logger.error(f"Caption variation generation failed: {str(e)}")
            # Return single caption as fallback
            single = await self.generate(prompt, context)
            return [single]

    def _is_hashtags_only(self, content: str) -> bool:
        """Return True if the content contains only hashtags (no caption text)."""
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if not lines:
            return False
        return all(line.startswith("#") for line in lines)

    def _build_fallback_caption(
        self,
        prompt: str,
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """Create a short fallback caption if the model returns only hashtags."""
        context = context or {}
        property_type = context.get("property_type", "property")
        location = context.get("location", "")
        price = context.get("price", "")

        parts = [f"✨ New {property_type.lower()} alert!"]
        if location:
            parts.append(f"📍 {location}")
        if price:
            parts.append(f"💰 {price}")

        parts.append("DM for details or to schedule a tour. 🏡")
        return "\n".join(parts)

    def _generate_hashtags(
        self,
        prompt: str,
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Generate relevant hashtags based on content.
        
        Args:
            prompt: Content description
            context: Optional context
            
        Returns:
            String of hashtags
        """
        context = context or {}
        prompt_lower = prompt.lower()

        hashtags = set()

        # Always include general real estate hashtags
        hashtags.update(self.hashtag_categories["general"][:5])

        # Add category-specific hashtags based on content
        if any(word in prompt_lower for word in ["buy", "buyer", "purchase", "dream home"]):
            hashtags.update(self.hashtag_categories["buying"][:4])

        if any(word in prompt_lower for word in ["sell", "listing", "for sale", "open house"]):
            hashtags.update(self.hashtag_categories["selling"][:4])

        if any(word in prompt_lower for word in ["luxury", "million", "estate", "mansion", "premium"]):
            hashtags.update(self.hashtag_categories["luxury"][:4])

        if any(word in prompt_lower for word in ["invest", "rental", "income", "roi"]):
            hashtags.update(self.hashtag_categories["investment"][:4])

        if any(word in prompt_lower for word in ["interior", "kitchen", "bathroom", "bedroom", "living"]):
            hashtags.update(self.hashtag_categories["interior"][:4])

        if any(word in prompt_lower for word in ["exterior", "yard", "garden", "pool", "outdoor"]):
            hashtags.update(self.hashtag_categories["exterior"][:4])

        # Add location hashtag if provided
        location = context.get("location", "")
        if location:
            location_tag = f"#{location.replace(' ', '').replace(',', '')}"
            hashtags.add(location_tag)

        # Ensure we have enough hashtags
        while len(hashtags) < 20:
            for category in self.hashtag_categories.values():
                for tag in category:
                    if tag not in hashtags:
                        hashtags.add(tag)
                        if len(hashtags) >= 25:
                            break
                if len(hashtags) >= 25:
                    break

        return " ".join(sorted(hashtags)[:25])

    async def generate_story_caption(
        self,
        prompt: str,
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Generate a shorter caption suitable for Instagram Stories.
        
        Args:
            prompt: Content description
            context: Optional context
            
        Returns:
            Short, punchy caption for Stories
        """
        story_prompt = f"""Create a short, punchy Instagram Story caption for:

**Content:** {prompt}

Requirements:
- Maximum 2-3 lines
- Use 2-3 emojis
- Include a swipe-up CTA or engagement prompt
- No hashtags needed for Stories

Keep it brief and attention-grabbing!"""

        try:
            response = await self.llm_client.generate(
                prompt=story_prompt,
                system_prompt="You are an Instagram Story content expert. Create brief, engaging captions.",
            )
            return response

        except Exception as e:
            logger.error(f"Story caption generation failed: {str(e)}")
            raise

    async def generate_reel_caption(
        self,
        prompt: str,
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Generate a caption optimized for Instagram Reels.
        
        Args:
            prompt: Content description
            context: Optional context
            
        Returns:
            Reel-optimized caption with hashtags
        """
        context = context or {}

        reel_prompt = f"""Create an Instagram Reel caption for:

**Content:** {prompt}

Requirements:
- Start with a hook that complements the video
- Keep body text concise (Reels are fast-paced)
- Include trending real estate hashtags
- Add a CTA to follow for more content
- Use emojis strategically

Include 15-20 hashtags optimized for Reels discovery."""

        try:
            response = await self.llm_client.generate(
                prompt=reel_prompt,
                system_prompt=self._get_system_prompt(),
            )

            if "#" not in response:
                hashtags = self._generate_hashtags(prompt, context)
                response = f"{response}\n\n{hashtags}"

            return response

        except Exception as e:
            logger.error(f"Reel caption generation failed: {str(e)}")
            raise
