"""
Content Strategist Agent for REACH.


This agent creates content strategies, marketing plans, and organizes
research into actionable content calendars and campaigns.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from .base_agent import AgentConfig, BaseAgent

logger = logging.getLogger(__name__)


class ContentStrategistAgent(BaseAgent):
    """
    Content Strategist Agent that creates marketing strategies and content plans.
    
    This agent:
    - Develops comprehensive content strategies
    - Creates content calendars and schedules
    - Organizes research into actionable plans
    - Suggests content themes and topics
    - Provides campaign frameworks
    """

    DEFAULT_SYSTEM_PROMPT = """You are an expert content strategist specializing in digital marketing and content planning. Your role is to:

1. Develop comprehensive content strategies aligned with business goals
2. Create actionable content calendars and schedules
3. Identify content themes and topic clusters
4. Plan multi-channel content campaigns
5. Optimize content mix for audience engagement

Strategic Planning Principles:
- Align content with business objectives and KPIs
- Consider the customer journey and funnel stages
- Balance content types (educational, promotional, engaging)
- Plan for consistency and sustainable output
- Include measurement and optimization strategies

Content Strategy Components:
- Audience analysis and personas
- Content pillars and themes
- Channel strategy and distribution
- Content calendar and scheduling
- Performance metrics and KPIs
- Resource allocation and workflow

Always provide actionable, practical recommendations that can be implemented immediately."""

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        system_prompt: Optional[str] = None,
    ):
        """
        Initialize the Content Strategist Agent.
        
        Args:
            llm_client: Optional LLM client instance
            system_prompt: Optional custom system prompt
        """
        config = AgentConfig(
            name="Content Strategist Agent",
            description="Creates content strategies and marketing plans",
            system_prompt=system_prompt or self.DEFAULT_SYSTEM_PROMPT,
        )
        super().__init__(config, llm_client)

    async def generate(
        self,
        user_input: str,
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Generate a content strategy based on user input.
        
        Args:
            user_input: Strategy request or business context
            context: Optional context with goals, audience, etc.
            
        Returns:
            Generated strategy string
        """
        # Extract parameters from context
        context = context or {}
        business_type = context.get("business_type", "")
        target_audience = context.get("target_audience", "")
        goals = context.get("goals", [])
        timeframe = context.get("timeframe", "monthly")
        research_results = context.get("research_results")

        # Build the strategy prompt
        prompt = self._build_strategy_prompt(
            user_input=user_input,
            business_type=business_type,
            target_audience=target_audience,
            goals=goals,
            timeframe=timeframe,
            research_results=research_results,
        )

        # Generate the strategy
        response = await self._retry_generation(prompt, max_retries=2)

        if response.error:
            return f"Unable to generate content strategy: {response.error}"

        return response.content

    def _build_strategy_prompt(
        self,
        user_input: str,
        business_type: str,
        target_audience: str,
        goals: list[str],
        timeframe: str,
        research_results: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Build the prompt for strategy generation.
        
        Args:
            user_input: User's strategy request
            business_type: Type of business
            target_audience: Target audience description
            goals: List of business/content goals
            timeframe: Planning timeframe
            research_results: Optional research data
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = []

        # Main instruction
        prompt_parts.append(f"""Create a comprehensive content strategy for: "{user_input}"

Planning Parameters:
- Business Type: {business_type or 'Not specified'}
- Target Audience: {target_audience or 'General professional audience'}
- Timeframe: {timeframe}""")

        # Add goals if provided
        if goals:
            goals_str = "\n".join(f"- {goal}" for goal in goals)
            prompt_parts.append(f"""
Business Goals:
{goals_str}""")

        # Add research context if available
        if research_results:
            research_summary = self._format_research_for_prompt(research_results)
            prompt_parts.append(f"""
Market Research Insights:
{research_summary}""")

        # Strategy requirements
        prompt_parts.append("""
Required Strategy Components:

## 1. Executive Summary
Brief overview of the strategy and expected outcomes

## 2. Audience Analysis
- Target audience segments
- Pain points and needs
- Content preferences
- Engagement patterns

## 3. Content Pillars
- 3-5 main content themes/topics
- Rationale for each pillar
- Example topics under each pillar

## 4. Content Mix
- Content types and formats
- Distribution across channels
- Frequency recommendations

## 5. Channel Strategy
- Primary and secondary channels
- Channel-specific tactics
- Cross-promotion approach

## 6. Content Calendar Framework
- Weekly/monthly content rhythm
- Key dates and opportunities
- Content batching suggestions

## 7. Success Metrics
- KPIs to track
- Measurement approach
- Optimization triggers

## 8. Implementation Roadmap
- Quick wins (Week 1-2)
- Short-term actions (Month 1)
- Long-term initiatives

Provide actionable, specific recommendations throughout.""")

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
            parts.append(research_results["summary"][:400])

        if research_results.get("key_findings"):
            findings = research_results["key_findings"][:4]
            for finding in findings:
                parts.append(f"• {finding}")

        return "\n".join(parts) if parts else "No research data available."

    async def create_content_calendar(
        self,
        topic: str,
        duration_weeks: int = 4,
        content_types: Optional[list[str]] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Create a detailed content calendar.
        
        Args:
            topic: Main topic or theme
            duration_weeks: Number of weeks to plan
            content_types: Types of content to include
            context: Optional additional context
            
        Returns:
            Content calendar string
        """
        content_types = content_types or ["blog", "linkedin", "image"]
        content_types_str = ", ".join(content_types)

        # Calculate date range
        start_date = datetime.now()
        end_date = start_date + timedelta(weeks=duration_weeks)

        prompt = f"""Create a detailed {duration_weeks}-week content calendar for: "{topic}"

Date Range: {start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}
Content Types to Include: {content_types_str}

For each week, provide:
1. Week number and date range
2. Theme or focus for the week
3. Specific content pieces with:
   - Content type (blog, LinkedIn post, image, etc.)
   - Title/topic
   - Target keywords (for SEO content)
   - Publishing day
   - Brief description

Calendar Requirements:
- Maintain consistent posting frequency
- Build on themes progressively
- Include variety in content types
- Consider optimal posting days
- Include content repurposing opportunities

Format as a clear, actionable calendar that can be followed directly."""

        response = await self._call_llm(prompt, max_tokens=3000)

        if response.error:
            return f"Unable to generate content calendar: {response.error}"

        return response.content

    async def suggest_content_topics(
        self,
        niche: str,
        num_topics: int = 10,
        content_type: Optional[str] = None,
    ) -> list[dict[str, str]]:
        """
        Suggest content topics for a niche.
        
        Args:
            niche: Industry or topic niche
            num_topics: Number of topics to suggest
            content_type: Optional specific content type
            
        Returns:
            List of topic dictionaries
        """
        content_type_str = f"for {content_type} content" if content_type else ""

        prompt = f"""Suggest {num_topics} content topics {content_type_str} in the {niche} niche.

For each topic provide:
1. Topic title
2. Target audience
3. Content angle/hook
4. Potential keywords
5. Content format recommendation

Focus on:
- Topics with search potential
- Evergreen and trending topics mix
- Different funnel stages (awareness, consideration, decision)
- Unique angles that stand out

Format each topic clearly."""

        response = await self._call_llm(prompt, temperature=0.8)

        if response.error:
            return [{"title": f"Content about {niche}", "audience": "", "angle": ""}]

        # Parse topics
        return self._parse_topic_suggestions(response.content, num_topics)

    def _parse_topic_suggestions(
        self,
        response: str,
        num_topics: int,
    ) -> list[dict[str, str]]:
        """
        Parse topic suggestions from LLM response.
        
        Args:
            response: LLM response
            num_topics: Expected number of topics
            
        Returns:
            List of topic dictionaries
        """
        topics = []
        current_topic = {
            "title": "",
            "audience": "",
            "angle": "",
            "keywords": "",
            "format": "",
        }

        lines = response.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            line_lower = line.lower()

            # Check for new topic
            if any(
                marker in line_lower
                for marker in ["topic", "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "10."]
            ) and ":" in line:
                if current_topic["title"]:
                    topics.append(current_topic)
                    current_topic = {
                        "title": "",
                        "audience": "",
                        "angle": "",
                        "keywords": "",
                        "format": "",
                    }

            # Parse fields
            if "title:" in line_lower or "topic:" in line_lower:
                current_topic["title"] = line.split(":", 1)[1].strip()
            elif "audience:" in line_lower:
                current_topic["audience"] = line.split(":", 1)[1].strip()
            elif "angle:" in line_lower or "hook:" in line_lower:
                current_topic["angle"] = line.split(":", 1)[1].strip()
            elif "keyword" in line_lower:
                current_topic["keywords"] = line.split(":", 1)[1].strip()
            elif "format:" in line_lower:
                current_topic["format"] = line.split(":", 1)[1].strip()
            elif not current_topic["title"] and line and line[0].isdigit():
                # Extract title from numbered list
                title = line.lstrip("0123456789.-) ").strip()
                if title:
                    current_topic["title"] = title

        if current_topic["title"]:
            topics.append(current_topic)

        return topics[:num_topics] if topics else [{"title": response.split("\n")[0], "audience": "", "angle": ""}]

    async def create_campaign_framework(
        self,
        campaign_goal: str,
        duration: str = "1 month",
        budget_level: str = "medium",
    ) -> str:
        """
        Create a content campaign framework.
        
        Args:
            campaign_goal: Main goal of the campaign
            duration: Campaign duration
            budget_level: Budget level (low, medium, high)
            
        Returns:
            Campaign framework string
        """
        prompt = f"""Create a content marketing campaign framework:

Campaign Goal: {campaign_goal}
Duration: {duration}
Budget Level: {budget_level}

Provide a comprehensive campaign plan including:

## Campaign Overview
- Campaign name suggestion
- Core message/theme
- Target outcomes

## Audience Targeting
- Primary audience segment
- Secondary audiences
- Audience insights to leverage

## Content Strategy
- Content pillars for the campaign
- Content types and formats
- Content production schedule

## Channel Mix
- Primary channels
- Supporting channels
- Channel-specific tactics

## Campaign Phases
- Launch phase
- Momentum phase
- Conversion phase
- Wrap-up phase

## Content Assets Needed
- Hero content pieces
- Supporting content
- Social media content
- Visual assets

## Promotion Strategy
- Organic promotion tactics
- Paid promotion recommendations (if applicable)
- Influencer/partnership opportunities

## Success Metrics
- Primary KPIs
- Secondary metrics
- Tracking approach

## Timeline
- Week-by-week breakdown
- Key milestones
- Review points

Make the framework actionable and specific to the goal."""

        response = await self._call_llm(prompt, max_tokens=3500)

        if response.error:
            return f"Unable to generate campaign framework: {response.error}"

        return response.content

    async def analyze_content_gaps(
        self,
        current_content: str,
        competitors: Optional[list[str]] = None,
        target_keywords: Optional[list[str]] = None,
    ) -> str:
        """
        Analyze content gaps and opportunities.
        
        Args:
            current_content: Description of current content
            competitors: Optional list of competitors
            target_keywords: Optional target keywords
            
        Returns:
            Gap analysis string
        """
        competitors_str = ", ".join(competitors) if competitors else "industry leaders"
        keywords_str = ", ".join(target_keywords) if target_keywords else "relevant industry terms"

        prompt = f"""Analyze content gaps and opportunities:

Current Content Overview:
{current_content}

Competitors to Consider: {competitors_str}
Target Keywords: {keywords_str}

Provide analysis including:

## Content Audit Summary
- Strengths of current content
- Weaknesses identified
- Content type distribution

## Gap Analysis
- Topics not covered
- Content formats missing
- Audience segments underserved
- Funnel stages with gaps

## Competitive Insights
- What competitors do well
- Opportunities they're missing
- Differentiation opportunities

## Recommendations
- Quick wins (easy to implement)
- Strategic priorities
- Long-term content investments

## Action Plan
- Immediate actions (this week)
- Short-term actions (this month)
- Long-term initiatives (quarter)

Be specific and actionable in recommendations."""

        response = await self._call_llm(prompt, max_tokens=2500)

        if response.error:
            return f"Unable to analyze content gaps: {response.error}"

        return response.content

    async def create_content_brief(
        self,
        topic: str,
        content_type: str = "blog",
        target_keywords: Optional[list[str]] = None,
    ) -> str:
        """
        Create a detailed content brief for writers.
        
        Args:
            topic: Content topic
            content_type: Type of content
            target_keywords: Optional target keywords
            
        Returns:
            Content brief string
        """
        keywords_str = ", ".join(target_keywords) if target_keywords else "to be researched"

        prompt = f"""Create a detailed content brief for:

Topic: {topic}
Content Type: {content_type}
Target Keywords: {keywords_str}

Content Brief Structure:

## Overview
- Working title
- Content type and format
- Target word count/length
- Target audience

## Objectives
- Primary goal
- Secondary goals
- Desired reader action

## SEO Requirements
- Primary keyword
- Secondary keywords
- Search intent
- Meta description guidance

## Content Outline
- Introduction approach
- Main sections (H2s)
- Subsections (H3s)
- Conclusion approach

## Key Points to Cover
- Must-include information
- Statistics or data to reference
- Examples to include
- Questions to answer

## Tone and Style
- Voice guidelines
- Tone description
- Style notes
- Brand considerations

## Resources
- Reference materials
- Competitor content to review
- Subject matter experts

## Deliverables
- Draft deadline
- Review process
- Final delivery date

Make the brief comprehensive enough for a writer to create excellent content."""

        response = await self._call_llm(prompt, max_tokens=2000)

        if response.error:
            return f"Unable to create content brief: {response.error}"

        return response.content

    async def suggest_content_repurposing(
        self,
        original_content: str,
        original_type: str = "blog",
    ) -> str:
        """
        Suggest ways to repurpose content across formats.
        
        Args:
            original_content: The original content or summary
            original_type: Type of original content
            
        Returns:
            Repurposing suggestions string
        """
        prompt = f"""Suggest content repurposing opportunities:

Original Content Type: {original_type}
Content Summary:
{original_content[:1500]}

Provide repurposing suggestions including:

## Repurposing Opportunities

### Social Media
- LinkedIn post ideas (2-3 variations)
- Twitter/X thread outline
- Instagram carousel concept

### Long-form Content
- Related blog post ideas
- Guide or ebook expansion
- Case study angle

### Visual Content
- Infographic concept
- Video script outline
- Presentation slides

### Audio Content
- Podcast episode idea
- Audio summary concept

### Interactive Content
- Quiz or assessment idea
- Calculator or tool concept

For each suggestion, provide:
- Format description
- Key points to include
- Platform optimization tips
- Estimated effort level

Focus on maximizing the value of the original content."""

        response = await self._call_llm(prompt, max_tokens=2000)

        if response.error:
            return f"Unable to generate repurposing suggestions: {response.error}"

        return response.content