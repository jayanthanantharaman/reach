"""
SEO Blog Writer Agent for REACH.


This agent creates search-optimized long-form blog content with proper
structure, keywords, and SEO best practices. It can also generate
relevant images for the blog using the Image Generator Agent.
"""

import logging
import re
from typing import Any, Optional

from .base_agent import AgentConfig, BaseAgent
from .image_generator import ImageGeneratorAgent

logger = logging.getLogger(__name__)


class BlogWriterAgent(BaseAgent):
    """
    SEO Blog Writer Agent that creates optimized long-form content.
    
    This agent:
    - Creates SEO-optimized blog posts and articles
    - Structures content with proper headings and formatting
    - Incorporates target keywords naturally
    - Generates meta descriptions and title tags
    - Follows content marketing best practices
    """

    DEFAULT_SYSTEM_PROMPT = """You are an expert SEO content writer specializing in creating high-quality, search-optimized blog posts and articles. Your role is to:

1. Create engaging, informative long-form content
2. Optimize content for search engines while maintaining readability
3. Structure articles with proper headings (H1, H2, H3)
4. Incorporate keywords naturally without keyword stuffing
5. Write compelling introductions and conclusions
6. Include actionable insights and valuable information

SEO Best Practices to Follow:
- Use the primary keyword in the title, first paragraph, and throughout the content
- Include related keywords and semantic variations
- Write meta descriptions that encourage clicks (150-160 characters)
- Use descriptive headings that include keywords where appropriate
- Keep paragraphs short and scannable
- Include internal linking opportunities
- Add calls-to-action where appropriate

Content Structure Guidelines:
- Start with a hook that captures attention
- Provide clear value proposition early
- Use bullet points and numbered lists for readability
- Include examples, statistics, or case studies when relevant
- End with a strong conclusion and call-to-action

Always write in a {tone} tone appropriate for the target audience."""

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        image_client: Optional[Any] = None,
        system_prompt: Optional[str] = None,
    ):
        """
        Initialize the Blog Writer Agent.
        
        Args:
            llm_client: Optional LLM client instance
            image_client: Optional image generation client (Google Imagen)
            system_prompt: Optional custom system prompt
        """
        config = AgentConfig(
            name="SEO Blog Writer Agent",
            description="Creates search-optimized blog posts and articles with images",
            system_prompt=system_prompt or self.DEFAULT_SYSTEM_PROMPT,
        )
        super().__init__(config, llm_client)
        
        # Initialize image generator for blog images
        self.image_generator = ImageGeneratorAgent(
            llm_client=llm_client,
            image_client=image_client,
        )
        self.image_client = image_client

    def set_image_client(self, client: Any) -> None:
        """
        Set the image generation client.
        
        Args:
            client: Image generation client (Google Imagen)
        """
        self.image_client = client
        self.image_generator.set_image_client(client)
        logger.info("Image client set for Blog Writer Agent")

    async def generate(
        self,
        user_input: str,
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Generate an SEO-optimized blog post with an optional image.
        
        Args:
            user_input: Blog topic or request
            context: Optional context with keywords, tone, etc.
                - include_image: bool - Whether to generate an image (default: True)
                - image_style: str - Style for the image (default: "professional")
            
        Returns:
            Generated blog post string with image (if enabled)
        """
        # Extract parameters from context
        context = context or {}
        topic = context.get("topic", user_input)
        keywords = context.get("keywords", [])
        tone = context.get("tone", "professional")
        target_audience = context.get("target_audience", "general audience")
        word_count = context.get("word_count", 1500)
        research_results = context.get("research_results")
        include_image = context.get("include_image", True)
        image_style = context.get("image_style", "professional")

        # Build the blog generation prompt
        prompt = self._build_blog_prompt(
            topic=topic,
            keywords=keywords,
            tone=tone,
            target_audience=target_audience,
            word_count=word_count,
            research_results=research_results,
        )

        # Generate the blog post
        response = await self._retry_generation(prompt, max_retries=2)

        if response.error:
            return f"Unable to generate blog post: {response.error}"

        # Post-process the content
        blog_content = self._post_process_blog(response.content, keywords)

        # Generate image if enabled
        if include_image:
            image_result = await self._generate_blog_image(
                topic=topic,
                blog_content=blog_content,
                style=image_style,
            )
            
            if image_result:
                # Insert image after the title/intro section
                blog_content = self._insert_image_into_blog(blog_content, image_result)

        return blog_content

    async def generate_with_image(
        self,
        user_input: str,
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Generate an SEO-optimized blog post with a separate image result.
        
        This method returns both the blog content and image data separately,
        useful when you need to handle them independently.
        
        Args:
            user_input: Blog topic or request
            context: Optional context with keywords, tone, etc.
            
        Returns:
            Dictionary with 'blog_content', 'image_data', and 'image_prompt'
        """
        context = context or {}
        topic = context.get("topic", user_input)
        keywords = context.get("keywords", [])
        tone = context.get("tone", "professional")
        target_audience = context.get("target_audience", "general audience")
        word_count = context.get("word_count", 1500)
        research_results = context.get("research_results")
        image_style = context.get("image_style", "professional")

        # Build the blog generation prompt
        prompt = self._build_blog_prompt(
            topic=topic,
            keywords=keywords,
            tone=tone,
            target_audience=target_audience,
            word_count=word_count,
            research_results=research_results,
        )

        # Generate the blog post
        response = await self._retry_generation(prompt, max_retries=2)

        if response.error:
            return {
                "success": False,
                "error": f"Unable to generate blog post: {response.error}",
                "blog_content": None,
                "image_data": None,
                "image_prompt": None,
            }

        # Post-process the content
        blog_content = self._post_process_blog(response.content, keywords)

        # Extract title and summary for image generation
        title = self._extract_title(blog_content)
        summary = self._extract_summary(blog_content)

        # Generate optimized image prompt
        image_prompt = await self.image_generator.create_blog_header_prompt(
            blog_title=title or topic,
            blog_summary=summary or topic,
        )

        # Generate the image
        image_result = await self.image_generator.generate(
            user_input=image_prompt,
            context={
                "style": image_style,
                "aspect_ratio": "16:9",
                "optimize_prompt": False,  # Already optimized
            },
        )

        return {
            "success": True,
            "blog_content": blog_content,
            "image_data": image_result,
            "image_prompt": image_prompt,
            "title": title,
            "summary": summary,
        }

    async def _generate_blog_image(
        self,
        topic: str,
        blog_content: str,
        style: str = "professional",
    ) -> Optional[str]:
        """
        Generate a relevant image for the blog post.
        
        Args:
            topic: Blog topic
            blog_content: Generated blog content
            style: Image style preset
            
        Returns:
            Image result string or None if generation fails
        """
        try:
            # Extract title and summary for better image generation
            title = self._extract_title(blog_content)
            summary = self._extract_summary(blog_content)

            # Create optimized blog header prompt
            image_prompt = await self.image_generator.create_blog_header_prompt(
                blog_title=title or topic,
                blog_summary=summary or topic,
            )

            logger.info(f"Generating blog image with prompt: {image_prompt[:100]}...")

            # Generate the image
            image_result = await self.image_generator.generate(
                user_input=image_prompt,
                context={
                    "style": style,
                    "aspect_ratio": "16:9",  # Wide format for blog headers
                    "optimize_prompt": False,  # Already optimized by create_blog_header_prompt
                },
            )

            return image_result

        except Exception as e:
            logger.error(f"Failed to generate blog image: {str(e)}")
            return None

    def _extract_title(self, content: str) -> Optional[str]:
        """
        Extract the title from blog content.
        
        Args:
            content: Blog content
            
        Returns:
            Extracted title or None
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

        return None

    def _extract_summary(self, content: str) -> Optional[str]:
        """
        Extract a summary from blog content.
        
        Args:
            content: Blog content
            
        Returns:
            Extracted summary or None
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

        # Take first paragraph after title
        paragraphs = content.split("\n\n")
        for para in paragraphs[1:3]:  # Skip title, check next 2 paragraphs
            para = para.strip()
            if para and not para.startswith("#") and len(para) > 50:
                return para[:300]

        return None

    def _insert_image_into_blog(
        self,
        blog_content: str,
        image_result: str,
    ) -> str:
        """
        Insert the generated image into the blog content.
        
        Args:
            blog_content: Original blog content
            image_result: Image generation result (may be base64 data URI or URL)
            
        Returns:
            Blog content with image inserted as markdown image
        """
        # Check if image_result is a data URI or URL
        if image_result and isinstance(image_result, str):
            if image_result.startswith("data:image") or image_result.startswith("http"):
                # Create proper markdown image syntax
                image_section = f"""
---

## 📸 Featured Image

![Featured Image]({image_result})

---

"""
            else:
                # If it's some other format, try to display as-is but note it
                image_section = f"""
---

## 📸 Featured Image

*Image generated - see below*

![Featured Image]({image_result})

---

"""
        else:
            # No valid image result
            return blog_content

        # Find the best place to insert the image (after title and meta description)
        lines = blog_content.split("\n")
        insert_index = 0

        for i, line in enumerate(lines):
            # Skip title (H1)
            if line.startswith("# "):
                insert_index = i + 1
                continue
            # Skip meta description
            if "meta description" in line.lower():
                insert_index = i + 2
                continue
            # Insert before first H2 or after intro paragraph
            if line.startswith("## ") and insert_index > 0:
                break
            # If we find a substantial paragraph, insert after it
            if len(line) > 100 and insert_index > 0:
                insert_index = i + 1
                break

        # Insert the image section
        if insert_index > 0 and insert_index < len(lines):
            lines.insert(insert_index, image_section)
            return "\n".join(lines)

        # Fallback: insert after title
        return blog_content.replace("\n\n", f"\n\n{image_section}\n\n", 1)

    def _build_blog_prompt(
        self,
        topic: str,
        keywords: list[str],
        tone: str,
        target_audience: str,
        word_count: int,
        research_results: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Build the prompt for blog generation.
        
        Args:
            topic: Blog topic
            keywords: Target keywords
            tone: Writing tone
            target_audience: Target audience description
            word_count: Target word count
            research_results: Optional research data
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = []

        # Main instruction
        prompt_parts.append(f"""Write a comprehensive, SEO-optimized blog post about: "{topic}"

Target Specifications:
- Word Count: Approximately {word_count} words
- Tone: {tone}
- Target Audience: {target_audience}""")

        # Add keywords if provided
        if keywords:
            keywords_str = ", ".join(keywords[:10])
            prompt_parts.append(f"""
Target Keywords to Include:
Primary: {keywords[0] if keywords else topic}
Secondary: {keywords_str}

Incorporate these keywords naturally throughout the content.""")

        # Add research context if available
        if research_results:
            research_summary = self._format_research_for_prompt(research_results)
            prompt_parts.append(f"""
Research Context:
{research_summary}

Use this research to support your points with facts and data.""")

        # Structure requirements
        prompt_parts.append("""
Required Blog Structure:
1. **Title**: Compelling, keyword-rich title (H1)
2. **Meta Description**: 150-160 character summary for search results
3. **Introduction**: Hook the reader, introduce the topic, preview what they'll learn
4. **Main Content**: 
   - Use H2 headings for main sections
   - Use H3 headings for subsections
   - Include bullet points or numbered lists where appropriate
   - Add relevant examples or statistics
5. **Conclusion**: Summarize key points, include call-to-action
6. **FAQ Section** (optional): 3-5 common questions about the topic

Formatting Guidelines:
- Use markdown formatting
- Keep paragraphs to 2-4 sentences
- Include transition sentences between sections
- Bold important terms and concepts
- Use engaging subheadings that include keywords""")

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
            parts.append(f"Summary: {research_results['summary'][:500]}")

        if research_results.get("key_findings"):
            findings = research_results["key_findings"][:5]
            parts.append("Key Facts:")
            for finding in findings:
                parts.append(f"- {finding}")

        return "\n".join(parts) if parts else "No research data available."

    def _post_process_blog(
        self,
        content: str,
        keywords: list[str],
    ) -> str:
        """
        Post-process the generated blog content.
        
        Args:
            content: Raw generated content
            keywords: Target keywords
            
        Returns:
            Processed blog content
        """
        # Ensure proper markdown formatting
        content = self._fix_markdown_formatting(content)

        # Add keyword density check note if keywords provided
        if keywords:
            keyword_analysis = self._analyze_keyword_usage(content, keywords)
            if keyword_analysis:
                content += f"\n\n---\n*SEO Analysis: {keyword_analysis}*"

        return content

    def _fix_markdown_formatting(self, content: str) -> str:
        """
        Fix common markdown formatting issues.
        
        Args:
            content: Raw content
            
        Returns:
            Fixed content
        """
        # Ensure headings have proper spacing
        content = re.sub(r"(#{1,6})\s*([^\n]+)", r"\1 \2", content)

        # Ensure blank lines before headings
        content = re.sub(r"([^\n])\n(#{1,6}\s)", r"\1\n\n\2", content)

        # Fix bullet point formatting
        content = re.sub(r"^\s*[-*]\s*", "- ", content, flags=re.MULTILINE)

        return content.strip()

    def _analyze_keyword_usage(
        self,
        content: str,
        keywords: list[str],
    ) -> str:
        """
        Analyze keyword usage in the content.
        
        Args:
            content: Blog content
            keywords: Target keywords
            
        Returns:
            Analysis summary string
        """
        content_lower = content.lower()
        word_count = len(content.split())

        analysis_parts = []
        for keyword in keywords[:5]:
            keyword_lower = keyword.lower()
            count = content_lower.count(keyword_lower)
            density = (count / word_count) * 100 if word_count > 0 else 0

            if count > 0:
                analysis_parts.append(f'"{keyword}": {count}x ({density:.1f}%)')

        if analysis_parts:
            return "Keyword usage - " + ", ".join(analysis_parts)
        return ""

    async def generate_outline(
        self,
        topic: str,
        keywords: Optional[list[str]] = None,
    ) -> str:
        """
        Generate a blog post outline before full content.
        
        Args:
            topic: Blog topic
            keywords: Optional target keywords
            
        Returns:
            Blog outline string
        """
        keywords_str = ", ".join(keywords[:5]) if keywords else "relevant terms"

        prompt = f"""Create a detailed blog post outline for: "{topic}"

Target keywords: {keywords_str}

Provide:
1. Suggested title options (3 variations)
2. Meta description
3. Introduction approach
4. Main sections with H2 headings (5-7 sections)
5. Subsections with H3 headings where appropriate
6. Key points to cover in each section
7. Suggested conclusion approach
8. Potential FAQ questions (3-5)

Format as a structured outline that can guide the full article writing."""

        response = await self._call_llm(prompt, temperature=0.5)

        if response.error:
            return f"Unable to generate outline: {response.error}"

        return response.content

    async def generate_meta_description(
        self,
        title: str,
        content_summary: str,
        keywords: Optional[list[str]] = None,
    ) -> str:
        """
        Generate an SEO meta description.
        
        Args:
            title: Blog title
            content_summary: Brief content summary
            keywords: Optional target keywords
            
        Returns:
            Meta description string (150-160 chars)
        """
        keywords_str = ", ".join(keywords[:3]) if keywords else ""

        prompt = f"""Write an SEO meta description for this blog post:

Title: {title}
Summary: {content_summary}
Keywords to include: {keywords_str}

Requirements:
- Exactly 150-160 characters
- Include primary keyword naturally
- Compelling and click-worthy
- Accurately represents the content
- Include a subtle call-to-action

Provide only the meta description, no explanation."""

        response = await self._call_llm(prompt, temperature=0.6, max_tokens=100)

        if response.error:
            return f"Learn about {title[:100]}. Discover key insights and actionable tips."

        # Ensure proper length
        meta = response.content.strip().strip('"')
        if len(meta) > 160:
            meta = meta[:157] + "..."

        return meta

    async def suggest_titles(
        self,
        topic: str,
        keywords: Optional[list[str]] = None,
        num_titles: int = 5,
    ) -> list[str]:
        """
        Suggest SEO-optimized title options.
        
        Args:
            topic: Blog topic
            keywords: Optional target keywords
            num_titles: Number of title suggestions
            
        Returns:
            List of title suggestions
        """
        keywords_str = ", ".join(keywords[:3]) if keywords else topic

        prompt = f"""Generate {num_titles} SEO-optimized blog title options for: "{topic}"

Keywords to incorporate: {keywords_str}

Title Requirements:
- 50-60 characters ideal length
- Include primary keyword near the beginning
- Compelling and click-worthy
- Use power words where appropriate
- Mix of different title formats (how-to, listicle, question, etc.)

Provide only the titles as a numbered list."""

        response = await self._call_llm(prompt, temperature=0.8)

        if response.error:
            return [f"The Ultimate Guide to {topic}"]

        # Parse titles from response
        titles = []
        for line in response.content.split("\n"):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-")):
                title = line.lstrip("0123456789.-) ").strip()
                if title:
                    titles.append(title)

        return titles[:num_titles] if titles else [response.content.split("\n")[0]]

    async def improve_content(
        self,
        content: str,
        improvement_type: str = "seo",
    ) -> str:
        """
        Improve existing blog content.
        
        Args:
            content: Existing blog content
            improvement_type: Type of improvement (seo, readability, engagement)
            
        Returns:
            Improved content string
        """
        improvement_prompts = {
            "seo": """Improve this blog content for better SEO:
- Add more keyword variations
- Improve heading structure
- Add internal linking suggestions
- Enhance meta elements""",
            "readability": """Improve this blog content for better readability:
- Shorten long paragraphs
- Add more subheadings
- Include bullet points where appropriate
- Simplify complex sentences""",
            "engagement": """Improve this blog content for better engagement:
- Add more compelling hooks
- Include questions to engage readers
- Add calls-to-action
- Make the content more conversational""",
        }

        instruction = improvement_prompts.get(improvement_type, improvement_prompts["seo"])

        prompt = f"""{instruction}

Original Content:
{content[:4000]}

Provide the improved version maintaining the same topic and key information."""

        response = await self._call_llm(prompt, max_tokens=5000)

        if response.error:
            return content  # Return original if improvement fails

        return response.content