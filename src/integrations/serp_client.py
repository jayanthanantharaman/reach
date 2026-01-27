"""
SERP API Client for REACH.


This module provides integration with SERP API for
web search and research capabilities.
"""

import logging
from typing import Any, Optional
from urllib.parse import urlencode

import httpx

from ..core.config import get_settings

logger = logging.getLogger(__name__)


class SerpClient:
    """
    Client for interacting with SERP API.
    
    This client provides:
    - Google search results
    - News search
    - Image search
    - Related questions (People Also Ask)
    """

    BASE_URL = "https://serpapi.com/search"

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_num_results: int = 10,
        default_location: str = "United States",
        default_language: str = "en",
    ):
        """
        Initialize the SERP API client.
        
        Args:
            api_key: SERP API key (uses env var if not provided)
            default_num_results: Default number of results to fetch
            default_location: Default search location
            default_language: Default search language
        """
        settings = get_settings()
        self.api_key = api_key or settings.serp_api_key
        self.default_num_results = default_num_results
        self.default_location = default_location
        self.default_language = default_language
        self._initialized = bool(self.api_key)

        if self._initialized:
            logger.info("SERP API client initialized")
        else:
            logger.warning("SERP API client not initialized - no API key provided")

    @property
    def is_initialized(self) -> bool:
        """Check if the client is initialized."""
        return self._initialized

    async def search(
        self,
        query: str,
        num_results: Optional[int] = None,
        location: Optional[str] = None,
        language: Optional[str] = None,
        search_type: str = "google",
    ) -> list[dict[str, Any]]:
        """
        Perform a web search.
        
        Args:
            query: Search query
            num_results: Number of results to fetch
            location: Search location
            language: Search language
            search_type: Type of search (google, news, images)
            
        Returns:
            List of search result dictionaries
        """
        if not self._initialized:
            logger.warning("SERP client not initialized, returning empty results")
            return []

        params = {
            "api_key": self.api_key,
            "q": query,
            "num": num_results or self.default_num_results,
            "location": location or self.default_location,
            "hl": language or self.default_language,
            "engine": search_type,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

            return self._parse_search_results(data, search_type)

        except httpx.TimeoutException:
            logger.error("SERP API request timed out")
            return []
        except httpx.HTTPStatusError as e:
            logger.error(f"SERP API HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"SERP API error: {str(e)}")
            return []

    def _parse_search_results(
        self,
        data: dict[str, Any],
        search_type: str,
    ) -> list[dict[str, Any]]:
        """
        Parse search results from SERP API response.
        
        Args:
            data: Raw API response
            search_type: Type of search performed
            
        Returns:
            List of parsed result dictionaries
        """
        results = []

        if search_type == "google":
            # Parse organic results
            organic_results = data.get("organic_results", [])
            for result in organic_results:
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("link", ""),
                    "snippet": result.get("snippet", ""),
                    "position": result.get("position", 0),
                    "domain": result.get("displayed_link", ""),
                    "source": "google",
                })

            # Also include knowledge graph if available
            knowledge_graph = data.get("knowledge_graph", {})
            if knowledge_graph:
                results.insert(0, {
                    "title": knowledge_graph.get("title", ""),
                    "url": knowledge_graph.get("website", ""),
                    "snippet": knowledge_graph.get("description", ""),
                    "position": 0,
                    "domain": "Knowledge Graph",
                    "source": "knowledge_graph",
                    "type": knowledge_graph.get("type", ""),
                })

        elif search_type == "news":
            news_results = data.get("news_results", [])
            for result in news_results:
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("link", ""),
                    "snippet": result.get("snippet", ""),
                    "source": result.get("source", ""),
                    "date": result.get("date", ""),
                    "thumbnail": result.get("thumbnail", ""),
                })

        elif search_type == "images":
            image_results = data.get("images_results", [])
            for result in image_results:
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("original", ""),
                    "thumbnail": result.get("thumbnail", ""),
                    "source": result.get("source", ""),
                    "source_url": result.get("link", ""),
                })

        return results

    async def search_news(
        self,
        query: str,
        num_results: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """
        Search for news articles.
        
        Args:
            query: Search query
            num_results: Number of results to fetch
            
        Returns:
            List of news result dictionaries
        """
        return await self.search(
            query=query,
            num_results=num_results,
            search_type="news",
        )

    async def search_images(
        self,
        query: str,
        num_results: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """
        Search for images.
        
        Args:
            query: Search query
            num_results: Number of results to fetch
            
        Returns:
            List of image result dictionaries
        """
        return await self.search(
            query=query,
            num_results=num_results,
            search_type="images",
        )

    async def get_related_questions(
        self,
        query: str,
    ) -> list[dict[str, str]]:
        """
        Get "People Also Ask" related questions.
        
        Args:
            query: Search query
            
        Returns:
            List of related question dictionaries
        """
        if not self._initialized:
            return []

        params = {
            "api_key": self.api_key,
            "q": query,
            "engine": "google",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

            related_questions = data.get("related_questions", [])
            return [
                {
                    "question": q.get("question", ""),
                    "snippet": q.get("snippet", ""),
                    "link": q.get("link", ""),
                }
                for q in related_questions
            ]

        except Exception as e:
            logger.error(f"Error fetching related questions: {str(e)}")
            return []

    async def get_related_searches(
        self,
        query: str,
    ) -> list[str]:
        """
        Get related search queries.
        
        Args:
            query: Search query
            
        Returns:
            List of related search strings
        """
        if not self._initialized:
            return []

        params = {
            "api_key": self.api_key,
            "q": query,
            "engine": "google",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

            related_searches = data.get("related_searches", [])
            return [s.get("query", "") for s in related_searches if s.get("query")]

        except Exception as e:
            logger.error(f"Error fetching related searches: {str(e)}")
            return []

    async def get_trending_topics(
        self,
        location: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Get trending search topics.
        
        Args:
            location: Location for trends
            
        Returns:
            List of trending topic dictionaries
        """
        if not self._initialized:
            return []

        params = {
            "api_key": self.api_key,
            "engine": "google_trends_trending_now",
            "geo": location or "US",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

            trending = data.get("trending_searches", [])
            return [
                {
                    "query": t.get("query", ""),
                    "traffic": t.get("traffic", ""),
                }
                for t in trending
            ]

        except Exception as e:
            logger.error(f"Error fetching trending topics: {str(e)}")
            return []

    async def comprehensive_research(
        self,
        query: str,
        include_news: bool = True,
        include_related: bool = True,
    ) -> dict[str, Any]:
        """
        Perform comprehensive research on a topic.
        
        Args:
            query: Research query
            include_news: Whether to include news results
            include_related: Whether to include related questions
            
        Returns:
            Dictionary with all research data
        """
        research_data = {
            "query": query,
            "web_results": [],
            "news_results": [],
            "related_questions": [],
            "related_searches": [],
        }

        # Get web results
        research_data["web_results"] = await self.search(query)

        # Get news if requested
        if include_news:
            research_data["news_results"] = await self.search_news(query, num_results=5)

        # Get related content if requested
        if include_related:
            research_data["related_questions"] = await self.get_related_questions(query)
            research_data["related_searches"] = await self.get_related_searches(query)

        return research_data

    def get_client_info(self) -> dict[str, Any]:
        """
        Get information about the client configuration.
        
        Returns:
            Configuration information dictionary
        """
        return {
            "initialized": self._initialized,
            "default_num_results": self.default_num_results,
            "default_location": self.default_location,
            "default_language": self.default_language,
        }

    async def test_connection(self) -> bool:
        """
        Test the API connection.
        
        Returns:
            True if connection is successful
        """
        if not self._initialized:
            return False

        try:
            results = await self.search("test", num_results=1)
            return len(results) > 0
        except Exception:
            return False