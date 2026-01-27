"""
Query Handler Agent for REACH.


This agent handles general queries and routes requests to appropriate specialized agents.
It serves as the primary interface for user interactions.
"""

import logging
from typing import Any, Optional

from .base_agent import AgentConfig, BaseAgent

logger = logging.getLogger(__name__)


class QueryHandlerAgent(BaseAgent):
    """
    Query Handler Agent that processes user queries and provides general assistance.
    
    This agent:
    - Handles general questions and requests
    - Provides guidance on available capabilities
    - Assists with clarifying user intent
    - Offers suggestions for content creation
    """

    DEFAULT_SYSTEM_PROMPT = """You are REACH's intelligent assistant, specialized in helping users create high-quality marketing content. Your role is to:

1. Understand user requests and provide helpful responses
2. Guide users toward the best content creation approach
3. Clarify ambiguous requests to ensure optimal results
4. Suggest relevant content types based on user needs

Available content creation capabilities:
- Deep Research: Comprehensive web research and analysis on any topic
- SEO Blog Writing: Search-optimized long-form articles and guides
- LinkedIn Posts: Professional social media content for engagement
- Image Generation: Custom visuals and graphics using AI
- Content Strategy: Marketing plans and content calendars

When responding:
- Be helpful, professional, and concise
- Ask clarifying questions when needed
- Suggest the most appropriate content type for the user's needs
- Provide actionable guidance

If the user's request is unclear, help them refine it by asking specific questions about:
- Their target audience
- The purpose of the content
- Preferred tone and style
- Any specific requirements or constraints"""

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        system_prompt: Optional[str] = None,
    ):
        """
        Initialize the Query Handler Agent.
        
        Args:
            llm_client: Optional LLM client instance
            system_prompt: Optional custom system prompt
        """
        config = AgentConfig(
            name="Query Handler Agent",
            description="Handles general queries and provides content creation guidance",
            model="gemini-1.5-pro",
            temperature=0.7,
            max_tokens=2048,
            system_prompt=system_prompt or self.DEFAULT_SYSTEM_PROMPT,
        )
        super().__init__(config, llm_client)

    async def generate(
        self,
        user_input: str,
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Generate a response to the user's query.
        
        Args:
            user_input: User's question or request
            context: Optional context information
            
        Returns:
            Generated response string
        """
        # Build the prompt
        prompt = self._build_prompt(user_input, context)

        # Add to conversation history
        self.add_to_history("user", user_input)

        # Generate response
        response = await self._retry_generation(prompt)

        if response.error:
            error_message = f"I apologize, but I encountered an issue: {response.error}. Please try again."
            self.add_to_history("assistant", error_message)
            return error_message

        # Add response to history
        self.add_to_history("assistant", response.content)

        return response.content

    def _build_prompt(
        self,
        user_input: str,
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Build the prompt for the LLM.
        
        Args:
            user_input: User's input
            context: Optional context
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = []

        # Add conversation history context
        if self._conversation_history:
            history_text = self._format_history()
            if history_text:
                prompt_parts.append(f"Previous conversation:\n{history_text}\n")

        # Add any additional context
        if context:
            context_summary = self._extract_context_summary(context)
            if context_summary:
                prompt_parts.append(f"Context:\n{context_summary}\n")

        # Add the current user input
        prompt_parts.append(f"User request: {user_input}")

        # Add instruction for response
        prompt_parts.append(
            "\nProvide a helpful response. If the user wants to create content, "
            "guide them toward the appropriate content type and ask any clarifying "
            "questions needed to produce the best results."
        )

        return "\n".join(prompt_parts)

    def _format_history(self, max_turns: int = 5) -> str:
        """
        Format conversation history for prompt inclusion.
        
        Args:
            max_turns: Maximum number of turns to include
            
        Returns:
            Formatted history string
        """
        if not self._conversation_history:
            return ""

        recent_history = self._conversation_history[-max_turns * 2 :]
        formatted = []

        for message in recent_history:
            role = message["role"].capitalize()
            content = message["content"][:500]  # Truncate long messages
            formatted.append(f"{role}: {content}")

        return "\n".join(formatted)

    async def clarify_request(
        self,
        user_input: str,
        missing_info: list[str],
    ) -> str:
        """
        Generate clarifying questions for ambiguous requests.
        
        Args:
            user_input: Original user input
            missing_info: List of missing information types
            
        Returns:
            Clarifying questions string
        """
        prompt = f"""The user made the following request: "{user_input}"

To provide the best content, I need more information about:
{chr(10).join(f'- {info}' for info in missing_info)}

Generate friendly, professional clarifying questions to gather this information.
Keep questions concise and focused."""

        response = await self._call_llm(prompt)

        if response.error:
            # Fallback to generic questions
            questions = [
                "Could you tell me more about your target audience?",
                "What's the main goal of this content?",
                "Do you have any specific requirements or preferences?",
            ]
            return "\n".join(questions)

        return response.content

    async def suggest_content_type(
        self,
        user_input: str,
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Suggest the best content type based on user input.
        
        Args:
            user_input: User's request
            context: Optional context
            
        Returns:
            Dictionary with suggested content type and reasoning
        """
        prompt = f"""Analyze this user request and suggest the best content type:

Request: "{user_input}"

Available content types:
1. research - For gathering information and analysis
2. blog - For SEO-optimized articles and guides
3. linkedin - For professional social media posts
4. image - For visual content and graphics
5. strategy - For content planning and calendars

Respond in this format:
Content Type: [type]
Confidence: [high/medium/low]
Reasoning: [brief explanation]
Alternative: [alternative type if applicable]"""

        response = await self._call_llm(prompt, temperature=0.3)

        if response.error:
            return {
                "content_type": "research",
                "confidence": "low",
                "reasoning": "Unable to analyze request, defaulting to research",
                "alternative": None,
            }

        # Parse the response
        return self._parse_suggestion_response(response.content)

    def _parse_suggestion_response(self, response: str) -> dict[str, Any]:
        """
        Parse the content type suggestion response.
        
        Args:
            response: LLM response string
            
        Returns:
            Parsed suggestion dictionary
        """
        result = {
            "content_type": "research",
            "confidence": "medium",
            "reasoning": "",
            "alternative": None,
        }

        lines = response.strip().split("\n")
        for line in lines:
            line_lower = line.lower()
            if "content type:" in line_lower:
                value = line.split(":", 1)[1].strip().lower()
                if value in ["research", "blog", "linkedin", "image", "strategy"]:
                    result["content_type"] = value
            elif "confidence:" in line_lower:
                value = line.split(":", 1)[1].strip().lower()
                if value in ["high", "medium", "low"]:
                    result["confidence"] = value
            elif "reasoning:" in line_lower:
                result["reasoning"] = line.split(":", 1)[1].strip()
            elif "alternative:" in line_lower:
                value = line.split(":", 1)[1].strip().lower()
                if value and value != "none" and value != "n/a":
                    result["alternative"] = value

        return result

    async def provide_help(self) -> str:
        """
        Provide help information about available capabilities.
        
        Returns:
            Help text string
        """
        help_text = """# REACH - Your AI Content Assistant

I can help you create various types of marketing content:

## 📚 Deep Research
Get comprehensive research on any topic with sources and key insights.
Example: "Research the latest trends in sustainable fashion"

## 📝 SEO Blog Posts
Create search-optimized articles with proper structure and keywords.
Example: "Write a blog post about remote work productivity tips"

## 💼 LinkedIn Posts
Generate engaging professional content for LinkedIn.
Example: "Create a LinkedIn post about our new product launch"

## 🎨 Image Generation
Create custom visuals and graphics for your content.
Example: "Generate an image for a blog about AI in healthcare"

## 📊 Content Strategy
Develop content plans and marketing strategies.
Example: "Create a content strategy for a B2B SaaS company"

---

**Tips for best results:**
- Be specific about your topic and goals
- Mention your target audience
- Specify any tone or style preferences
- Include relevant keywords if you have them

How can I help you today?"""

        return help_text