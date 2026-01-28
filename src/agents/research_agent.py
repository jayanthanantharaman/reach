"""
Deep Research Agent for REACH.


This agent conducts comprehensive web research and analysis using SERP API
and synthesizes findings into structured research reports.
"""

import logging
from typing import Any, Optional

from .base_agent import AgentConfig, BaseAgent

logger = logging.getLogger(__name__)


class ResearchAgent(BaseAgent):
    """
    Deep Research Agent that conducts comprehensive web research.
    
    This agent:
    - Performs web searches using SERP API
    - Analyzes and synthesizes search results
    - Extracts key insights and facts
    - Provides structured research reports with sources
    """

    DEFAULT_SYSTEM_PROMPT = """You are an expert research analyst specializing in comprehensive web research and analysis. Your role is to:

1. Conduct thorough research on any given topic
2. Analyze multiple sources for accuracy and relevance
3. Synthesize findings into clear, structured reports
4. Identify key insights, trends, and important facts
5. Provide proper source attribution

When conducting research:
- Focus on credible, authoritative sources
- Look for recent and relevant information
- Identify multiple perspectives on the topic
- Extract actionable insights
- Note any conflicting information or debates

Your research reports should include:
- Executive summary
- Key findings and insights
- Supporting data and statistics
- Source references
- Recommendations for further exploration

Always maintain objectivity and clearly distinguish between facts and opinions."""

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        serp_client: Optional[Any] = None,
        system_prompt: Optional[str] = None,
    ):
        """
        Initialize the Research Agent.
        
        Args:
            llm_client: Optional LLM client instance
            serp_client: Optional SERP API client instance
            system_prompt: Optional custom system prompt
        """
        config = AgentConfig(
            name="Deep Research Agent",
            description="Conducts comprehensive web research and analysis",
            system_prompt=system_prompt or self.DEFAULT_SYSTEM_PROMPT,
        )
        super().__init__(config, llm_client)
        self.serp_client = serp_client

    def set_serp_client(self, client: Any) -> None:
        """
        Set the SERP API client.
        
        Args:
            client: SERP API client instance
        """
        self.serp_client = client
        logger.info("SERP client set for Research Agent")

    async def generate(
        self,
        user_input: str,
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Generate a research report based on user input.
        
        Args:
            user_input: Research topic or question
            context: Optional context information
            
        Returns:
            Generated research report string
        """
        # Extract topic from input
        topic = self._extract_topic(user_input, context)

        # Perform research
        research_results = await self.research(topic)

        # Format the research report
        report = self._format_research_report(research_results)

        return report

    async def research(
        self,
        topic: str,
        num_results: int = 10,
    ) -> dict[str, Any]:
        """
        Conduct comprehensive research on a topic.
        
        Args:
            topic: Research topic
            num_results: Number of search results to analyze
            
        Returns:
            Dictionary containing research results
        """
        research_data = {
            "topic": topic,
            "search_results": [],
            "key_findings": [],
            "summary": "",
            "sources": [],
            "related_topics": [],
        }

        try:
            # Perform web search if SERP client is available
            if self.serp_client:
                search_results = await self._perform_search(topic, num_results)
                research_data["search_results"] = search_results
                research_data["sources"] = self._extract_sources(search_results)

            # Analyze and synthesize results
            analysis = await self._analyze_results(topic, research_data["search_results"])
            research_data["key_findings"] = analysis.get("key_findings", [])
            research_data["summary"] = analysis.get("summary", "")
            research_data["related_topics"] = analysis.get("related_topics", [])

        except Exception as e:
            logger.error(f"Research error: {str(e)}")
            research_data["error"] = str(e)

        return research_data

    async def _perform_search(
        self,
        query: str,
        num_results: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Perform web search using SERP API.
        
        Args:
            query: Search query
            num_results: Number of results to fetch
            
        Returns:
            List of search result dictionaries
        """
        if not self.serp_client:
            logger.warning("SERP client not available, using LLM for research")
            return await self._llm_based_research(query)

        try:
            results = await self.serp_client.search(
                query=query,
                num_results=num_results,
            )
            return results
        except Exception as e:
            logger.error(f"SERP search error: {str(e)}")
            return await self._llm_based_research(query)

    async def _llm_based_research(
        self,
        topic: str,
    ) -> list[dict[str, Any]]:
        """
        Perform research using LLM when SERP is unavailable.
        
        Args:
            topic: Research topic
            
        Returns:
            List of simulated search results
        """
        prompt = f"""As a research expert, provide comprehensive information about: "{topic}"

Include:
1. Key facts and information
2. Recent developments or trends
3. Important statistics or data points
4. Different perspectives or viewpoints
5. Relevant context and background

Format your response as a detailed research brief."""

        response = await self._call_llm(prompt)

        if response.error:
            return []

        # Return as a single "result" for consistency
        return [{
            "title": f"Research on: {topic}",
            "snippet": response.content[:500],
            "content": response.content,
            "source": "AI Analysis",
            "url": "",
        }]

    async def _analyze_results(
        self,
        topic: str,
        search_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Analyze and synthesize search results.
        
        Args:
            topic: Research topic
            search_results: List of search results
            
        Returns:
            Analysis dictionary with findings and summary
        """
        # Prepare content for analysis
        content_to_analyze = self._prepare_content_for_analysis(search_results)

        prompt = f"""Analyze the following research content about "{topic}":

{content_to_analyze}

Provide a comprehensive analysis including:

1. EXECUTIVE SUMMARY (2-3 sentences)
2. KEY FINDINGS (5-7 bullet points of the most important insights)
3. SUPPORTING DATA (relevant statistics, facts, or figures)
4. DIFFERENT PERSPECTIVES (if any conflicting viewpoints exist)
5. RELATED TOPICS (3-5 related areas worth exploring)

Be thorough but concise. Focus on actionable insights."""

        response = await self._call_llm(prompt, max_tokens=3000)

        if response.error:
            return {
                "summary": "Unable to analyze research results.",
                "key_findings": [],
                "related_topics": [],
            }

        # Parse the analysis response
        return self._parse_analysis(response.content)

    def _prepare_content_for_analysis(
        self,
        search_results: list[dict[str, Any]],
    ) -> str:
        """
        Prepare search results content for analysis.
        
        Args:
            search_results: List of search results
            
        Returns:
            Formatted content string
        """
        if not search_results:
            return "No search results available."

        content_parts = []
        for i, result in enumerate(search_results[:10], 1):
            title = result.get("title", "Untitled")
            snippet = result.get("snippet", result.get("content", ""))[:500]
            source = result.get("source", result.get("url", "Unknown"))

            content_parts.append(f"""
Source {i}: {title}
{snippet}
Reference: {source}
---""")

        return "\n".join(content_parts)

    def _parse_analysis(self, analysis_text: str) -> dict[str, Any]:
        """
        Parse the analysis response into structured data.
        
        Args:
            analysis_text: Raw analysis text
            
        Returns:
            Structured analysis dictionary
        """
        result = {
            "summary": "",
            "key_findings": [],
            "supporting_data": [],
            "perspectives": [],
            "related_topics": [],
        }

        current_section = None
        lines = analysis_text.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            line_lower = line.lower()

            # Detect section headers
            if "executive summary" in line_lower or "summary" in line_lower:
                current_section = "summary"
            elif "key findings" in line_lower or "key insights" in line_lower:
                current_section = "key_findings"
            elif "supporting data" in line_lower or "statistics" in line_lower:
                current_section = "supporting_data"
            elif "perspectives" in line_lower or "viewpoints" in line_lower:
                current_section = "perspectives"
            elif "related topics" in line_lower:
                current_section = "related_topics"
            elif current_section:
                # Add content to current section
                if line.startswith(("-", "•", "*", "·")) or line[0].isdigit():
                    clean_line = line.lstrip("-•*·0123456789. ")
                    if clean_line:
                        if current_section == "summary":
                            result["summary"] += clean_line + " "
                        else:
                            result[current_section].append(clean_line)
                elif current_section == "summary":
                    result["summary"] += line + " "

        result["summary"] = result["summary"].strip()
        return result

    def _extract_sources(
        self,
        search_results: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        """
        Extract source information from search results.
        
        Args:
            search_results: List of search results
            
        Returns:
            List of source dictionaries
        """
        sources = []
        for result in search_results:
            source = {
                "title": result.get("title", "Untitled"),
                "url": result.get("url", result.get("link", "")),
                "domain": result.get("domain", ""),
            }
            if source["url"] or source["title"]:
                sources.append(source)
        return sources

    def _extract_topic(
        self,
        user_input: str,
        context: Optional[dict[str, Any]],
    ) -> str:
        """
        Extract the research topic from user input.
        
        Args:
            user_input: User's input
            context: Optional context
            
        Returns:
            Extracted topic string
        """
        # Check context for explicit topic
        if context and context.get("topic"):
            return context["topic"]

        # Clean up common prefixes
        prefixes_to_remove = [
            "research",
            "find information about",
            "look up",
            "search for",
            "tell me about",
            "what is",
            "who is",
            "learn about",
        ]

        topic = user_input.lower().strip()
        for prefix in prefixes_to_remove:
            if topic.startswith(prefix):
                topic = topic[len(prefix):].strip()
                break

        return topic or user_input

    def _format_research_report(
        self,
        research_data: dict[str, Any],
    ) -> str:
        """
        Format research data into a readable report.
        
        Args:
            research_data: Research results dictionary
            
        Returns:
            Formatted report string
        """
        report_parts = []

        # Title
        report_parts.append(f"# Research Report: {research_data['topic']}\n")

        # Summary
        if research_data.get("summary"):
            report_parts.append("## Executive Summary\n")
            report_parts.append(f"{research_data['summary']}\n")

        # Key Findings
        if research_data.get("key_findings"):
            report_parts.append("## Key Findings\n")
            for finding in research_data["key_findings"]:
                report_parts.append(f"- {finding}")
            report_parts.append("")

        # Sources
        if research_data.get("sources"):
            report_parts.append("## Sources\n")
            for i, source in enumerate(research_data["sources"][:10], 1):
                title = source.get("title", "Untitled")
                url = source.get("url", "")
                if url:
                    report_parts.append(f"{i}. [{title}]({url})")
                else:
                    report_parts.append(f"{i}. {title}")
            report_parts.append("")

        # Related Topics
        if research_data.get("related_topics"):
            report_parts.append("## Related Topics to Explore\n")
            for topic in research_data["related_topics"]:
                report_parts.append(f"- {topic}")
            report_parts.append("")

        # Error note if applicable
        if research_data.get("error"):
            report_parts.append(f"\n*Note: Some research data may be limited due to: {research_data['error']}*")

        return "\n".join(report_parts)

    async def get_quick_facts(
        self,
        topic: str,
        num_facts: int = 5,
    ) -> list[str]:
        """
        Get quick facts about a topic.
        
        Args:
            topic: Topic to research
            num_facts: Number of facts to return
            
        Returns:
            List of fact strings
        """
        prompt = f"""Provide {num_facts} key facts about "{topic}".

Requirements:
- Each fact should be concise (1-2 sentences)
- Focus on the most important and interesting information
- Include recent developments if relevant
- Be accurate and verifiable

Format: Return only the facts as a numbered list."""

        response = await self._call_llm(prompt, temperature=0.2)

        if response.error:
            return [f"Unable to retrieve facts about {topic}"]

        # Parse facts from response
        facts = []
        for line in response.content.split("\n"):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-")):
                fact = line.lstrip("0123456789.-) ").strip()
                if fact:
                    facts.append(fact)

        return facts[:num_facts] if facts else [response.content]