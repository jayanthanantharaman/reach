"""
LinkedIn Post Writer Agent for REACH.


This agent creates engaging professional social media content optimized
for LinkedIn's platform and audience.
"""

import logging
import re
from typing import Any, Optional

from .base_agent import AgentConfig, BaseAgent

logger = logging.getLogger(__name__)


class LinkedInWriterAgent(BaseAgent):
    """
    LinkedIn Post Writer Agent that creates engaging professional content.
    
    This agent:
    - Creates engaging LinkedIn posts optimized for the platform
    - Generates appropriate hashtags for reach
    - Structures content for maximum engagement
    - Adapts tone for professional audiences
    - Includes hooks and calls-to-action
    """

    DEFAULT_SYSTEM_PROMPT = """You are an expert LinkedIn content creator specializing in creating engaging, professional social media posts. Your role is to:

1. Create compelling LinkedIn posts that drive engagement
2. Write hooks that capture attention in the first line
3. Structure content for easy reading on mobile devices
4. Include relevant hashtags for discoverability
5. Add calls-to-action that encourage interaction
6. Maintain a professional yet personable tone

LinkedIn Best Practices:
- Start with a strong hook (first 2 lines are crucial)
- Use line breaks for readability
- Keep posts between 150-300 words for optimal engagement
- Include 3-5 relevant hashtags
- End with a question or call-to-action
- Use emojis sparingly and professionally
- Tell stories and share insights
- Be authentic and add personal perspective

Content Formats That Work Well:
- Personal stories with business lessons
- Industry insights and trends
- How-to tips and actionable advice
- Thought leadership and opinions
- Celebrating wins and milestones
- Asking questions to spark discussion

Always write in a {tone} tone that resonates with professional audiences."""

    # Maximum LinkedIn post length
    MAX_POST_LENGTH = 3000

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        system_prompt: Optional[str] = None,
    ):
        """
        Initialize the LinkedIn Writer Agent.
        
        Args:
            llm_client: Optional LLM client instance
            system_prompt: Optional custom system prompt
        """
        config = AgentConfig(
            name="LinkedIn Post Writer Agent",
            description="Creates engaging professional LinkedIn content",
            model="gemini-1.5-pro",
            temperature=0.8,  # Higher creativity for social content
            max_tokens=2000,
            system_prompt=system_prompt or self.DEFAULT_SYSTEM_PROMPT,
        )
        super().__init__(config, llm_client)

    async def generate(
        self,
        user_input: str,
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Generate an engaging LinkedIn post.
        
        Args:
            user_input: Post topic or request
            context: Optional context with tone, audience, etc.
            
        Returns:
            Generated LinkedIn post string
        """
        # Extract parameters from context
        context = context or {}
        topic = context.get("topic", user_input)
        tone = context.get("tone", "professional yet personable")
        target_audience = context.get("target_audience", "professionals")
        post_type = context.get("post_type", "insight")
        include_hashtags = context.get("include_hashtags", True)
        research_results = context.get("research_results")

        # Build the post generation prompt
        prompt = self._build_post_prompt(
            topic=topic,
            tone=tone,
            target_audience=target_audience,
            post_type=post_type,
            research_results=research_results,
        )

        # Generate the post
        response = await self._retry_generation(prompt, max_retries=2)

        if response.error:
            return f"Unable to generate LinkedIn post: {response.error}"

        # Post-process the content
        post_content = self._post_process_linkedin(
            response.content,
            include_hashtags=include_hashtags,
        )

        return post_content

    def _build_post_prompt(
        self,
        topic: str,
        tone: str,
        target_audience: str,
        post_type: str,
        research_results: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Build the prompt for LinkedIn post generation.
        
        Args:
            topic: Post topic
            tone: Writing tone
            target_audience: Target audience description
            post_type: Type of post (insight, story, tips, etc.)
            research_results: Optional research data
            
        Returns:
            Formatted prompt string
        """
        post_type_instructions = {
            "insight": "Share a valuable industry insight or observation",
            "story": "Tell a compelling personal or professional story",
            "tips": "Provide actionable tips or advice",
            "opinion": "Share a thought-provoking opinion or perspective",
            "announcement": "Make an engaging announcement",
            "question": "Pose a thought-provoking question to spark discussion",
            "celebration": "Celebrate an achievement or milestone",
        }

        instruction = post_type_instructions.get(post_type, post_type_instructions["insight"])

        prompt_parts = []

        # Main instruction
        prompt_parts.append(f"""Create an engaging LinkedIn post about: "{topic}"

Post Type: {instruction}
Tone: {tone}
Target Audience: {target_audience}""")

        # Add research context if available
        if research_results:
            research_summary = self._format_research_for_prompt(research_results)
            prompt_parts.append(f"""
Background Information:
{research_summary}

Use relevant facts or insights from this research to strengthen your post.""")

        # Structure requirements
        prompt_parts.append("""
LinkedIn Post Requirements:

1. **Hook** (First 2 lines - CRITICAL):
   - Must grab attention immediately
   - Create curiosity or emotional connection
   - Make readers want to click "see more"

2. **Body**:
   - Use short paragraphs (1-2 sentences each)
   - Add line breaks between paragraphs for readability
   - Include specific examples, numbers, or stories
   - Keep total length between 150-250 words

3. **Call-to-Action**:
   - End with a question or invitation to engage
   - Encourage comments, shares, or saves

4. **Hashtags**:
   - Include 3-5 relevant hashtags at the end
   - Mix popular and niche hashtags
   - Use hashtags relevant to the topic and industry

Formatting:
- Use emojis sparingly (1-3 max) if appropriate
- No bullet points in the main content (use line breaks instead)
- Make it feel authentic and personal
- Avoid corporate jargon""")

        return "\n".join(prompt_parts)

    def _format_research_for_prompt(
        self,
        research_results: dict[str, Any],
    ) -> str:
        """
        Format research results for inclusion in the prompt.
        
        Args:
            research_results: Research data dictionary
            
        Returns:
            Formatted research summary
        """
        parts = []

        if research_results.get("summary"):
            parts.append(research_results["summary"][:300])

        if research_results.get("key_findings"):
            findings = research_results["key_findings"][:3]
            for finding in findings:
                parts.append(f"• {finding}")

        return "\n".join(parts) if parts else ""

    def _post_process_linkedin(
        self,
        content: str,
        include_hashtags: bool = True,
    ) -> str:
        """
        Post-process the generated LinkedIn content.
        
        Args:
            content: Raw generated content
            include_hashtags: Whether to ensure hashtags are included
            
        Returns:
            Processed LinkedIn post
        """
        # Clean up formatting
        content = self._clean_linkedin_formatting(content)

        # Ensure proper length
        if len(content) > self.MAX_POST_LENGTH:
            content = self._truncate_post(content)

        # Add hashtags if missing and requested
        if include_hashtags and "#" not in content:
            hashtags = self._extract_topic_hashtags(content)
            if hashtags:
                content += f"\n\n{hashtags}"

        return content

    def _clean_linkedin_formatting(self, content: str) -> str:
        """
        Clean up LinkedIn post formatting.
        
        Args:
            content: Raw content
            
        Returns:
            Cleaned content
        """
        # Remove markdown headers (LinkedIn doesn't support them)
        content = re.sub(r"^#{1,6}\s*", "", content, flags=re.MULTILINE)

        # Remove bold/italic markdown (keep the text)
        content = re.sub(r"\*\*([^*]+)\*\*", r"\1", content)
        content = re.sub(r"\*([^*]+)\*", r"\1", content)
        content = re.sub(r"__([^_]+)__", r"\1", content)
        content = re.sub(r"_([^_]+)_", r"\1", content)

        # Ensure proper line breaks (LinkedIn uses double line breaks)
        content = re.sub(r"\n{3,}", "\n\n", content)

        # Remove any leading/trailing whitespace from lines
        lines = [line.strip() for line in content.split("\n")]
        content = "\n".join(lines)

        return content.strip()

    def _truncate_post(self, content: str) -> str:
        """
        Truncate post to fit LinkedIn's character limit.
        
        Args:
            content: Content to truncate
            
        Returns:
            Truncated content
        """
        if len(content) <= self.MAX_POST_LENGTH:
            return content

        # Try to truncate at a sentence boundary
        truncated = content[: self.MAX_POST_LENGTH - 3]
        last_period = truncated.rfind(".")
        last_newline = truncated.rfind("\n")

        cut_point = max(last_period, last_newline)
        if cut_point > self.MAX_POST_LENGTH * 0.7:
            return content[:cut_point + 1]

        return truncated + "..."

    def _extract_topic_hashtags(self, content: str) -> str:
        """
        Extract relevant hashtags from content.
        
        Args:
            content: Post content
            
        Returns:
            Hashtag string
        """
        # Common professional hashtags
        common_hashtags = [
            "#Leadership",
            "#Innovation",
            "#Business",
            "#Career",
            "#Success",
            "#Entrepreneurship",
            "#Marketing",
            "#Technology",
            "#Growth",
            "#Learning",
        ]

        # Return a subset of relevant hashtags
        return " ".join(common_hashtags[:4])

    async def generate_variations(
        self,
        topic: str,
        num_variations: int = 3,
        context: Optional[dict[str, Any]] = None,
    ) -> list[str]:
        """
        Generate multiple post variations for A/B testing.
        
        Args:
            topic: Post topic
            num_variations: Number of variations to generate
            context: Optional context
            
        Returns:
            List of post variations
        """
        variations = []
        post_types = ["insight", "story", "tips", "question", "opinion"]

        for i in range(min(num_variations, len(post_types))):
            context = context or {}
            context["post_type"] = post_types[i]

            post = await self.generate(topic, context)
            variations.append(post)

        return variations

    async def generate_hashtags(
        self,
        topic: str,
        num_hashtags: int = 5,
    ) -> list[str]:
        """
        Generate relevant hashtags for a topic.
        
        Args:
            topic: Post topic
            num_hashtags: Number of hashtags to generate
            
        Returns:
            List of hashtag strings
        """
        prompt = f"""Generate {num_hashtags} relevant LinkedIn hashtags for a post about: "{topic}"

Requirements:
- Mix of popular and niche hashtags
- Relevant to the topic and professional audience
- Include industry-specific hashtags
- Format: #HashtagName (CamelCase)

Provide only the hashtags, one per line."""

        response = await self._call_llm(prompt, temperature=0.6, max_tokens=200)

        if response.error:
            return ["#Business", "#Innovation", "#Leadership", "#Growth", "#Success"]

        # Parse hashtags from response
        hashtags = []
        for line in response.content.split("\n"):
            line = line.strip()
            if line.startswith("#"):
                # Clean up the hashtag
                hashtag = line.split()[0]  # Take only the hashtag part
                if hashtag not in hashtags:
                    hashtags.append(hashtag)

        return hashtags[:num_hashtags] if hashtags else ["#Business", "#Innovation"]

    async def generate_hook_variations(
        self,
        topic: str,
        num_hooks: int = 5,
    ) -> list[str]:
        """
        Generate multiple hook variations for testing.
        
        Args:
            topic: Post topic
            num_hooks: Number of hooks to generate
            
        Returns:
            List of hook strings
        """
        prompt = f"""Generate {num_hooks} compelling LinkedIn post hooks (opening lines) for a post about: "{topic}"

Hook Requirements:
- Maximum 2 lines each
- Create curiosity or emotional connection
- Make readers want to click "see more"
- Vary the approach (question, statement, story start, statistic, etc.)

Provide only the hooks, numbered 1-{num_hooks}."""

        response = await self._call_llm(prompt, temperature=0.9)

        if response.error:
            return [f"Here's what I learned about {topic}..."]

        # Parse hooks from response
        hooks = []
        for line in response.content.split("\n"):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-")):
                hook = line.lstrip("0123456789.-) ").strip()
                if hook:
                    hooks.append(hook)

        return hooks[:num_hooks] if hooks else [response.content.split("\n")[0]]

    async def improve_post(
        self,
        post: str,
        improvement_focus: str = "engagement",
    ) -> str:
        """
        Improve an existing LinkedIn post.
        
        Args:
            post: Existing post content
            improvement_focus: Focus area (engagement, hook, cta, hashtags)
            
        Returns:
            Improved post string
        """
        focus_instructions = {
            "engagement": "Make this post more engaging and likely to get comments",
            "hook": "Improve the opening hook to capture more attention",
            "cta": "Add or improve the call-to-action to drive more interaction",
            "hashtags": "Optimize the hashtags for better reach",
            "clarity": "Make the message clearer and more impactful",
        }

        instruction = focus_instructions.get(improvement_focus, focus_instructions["engagement"])

        prompt = f"""{instruction}

Original Post:
{post}

Provide the improved version. Maintain the core message but enhance it for better LinkedIn performance."""

        response = await self._call_llm(prompt, max_tokens=1500)

        if response.error:
            return post  # Return original if improvement fails

        return self._post_process_linkedin(response.content)

    async def create_carousel_content(
        self,
        topic: str,
        num_slides: int = 5,
    ) -> list[dict[str, str]]:
        """
        Create content for a LinkedIn carousel post.
        
        Args:
            topic: Carousel topic
            num_slides: Number of slides
            
        Returns:
            List of slide dictionaries with title and content
        """
        prompt = f"""Create content for a {num_slides}-slide LinkedIn carousel about: "{topic}"

For each slide provide:
- Slide number
- Title (short, impactful)
- Content (2-3 bullet points or short sentences)

The carousel should:
- Start with an attention-grabbing title slide
- Build a logical flow through the slides
- End with a call-to-action slide

Format each slide clearly."""

        response = await self._call_llm(prompt, temperature=0.7)

        if response.error:
            return [{"title": topic, "content": "Unable to generate carousel content"}]

        # Parse slides from response
        slides = self._parse_carousel_response(response.content, num_slides)
        return slides

    def _parse_carousel_response(
        self,
        response: str,
        num_slides: int,
    ) -> list[dict[str, str]]:
        """
        Parse carousel content from LLM response.
        
        Args:
            response: LLM response
            num_slides: Expected number of slides
            
        Returns:
            List of slide dictionaries
        """
        slides = []
        current_slide = {"title": "", "content": ""}

        lines = response.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            line_lower = line.lower()

            if "slide" in line_lower and any(c.isdigit() for c in line):
                if current_slide["title"]:
                    slides.append(current_slide)
                    current_slide = {"title": "", "content": ""}
            elif "title:" in line_lower:
                current_slide["title"] = line.split(":", 1)[1].strip()
            elif "content:" in line_lower:
                current_slide["content"] = line.split(":", 1)[1].strip()
            elif current_slide["title"] and not current_slide["content"]:
                current_slide["content"] += line + "\n"
            elif line.startswith("-") or line.startswith("•"):
                current_slide["content"] += line + "\n"

        if current_slide["title"]:
            slides.append(current_slide)

        return slides[:num_slides] if slides else [{"title": "Slide", "content": response}]