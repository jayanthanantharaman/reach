"""
Content Router for REACH.


This module handles intelligent routing of user requests to appropriate agents
based on intent classification and context analysis.
"""

import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ContentType(str, Enum):
    """Enumeration of content types that can be generated."""

    RESEARCH = "research"
    BLOG = "blog"
    LINKEDIN = "linkedin"
    IMAGE = "image"
    STRATEGY = "strategy"
    GENERAL = "general"


class RoutingDecision(BaseModel):
    """Model representing a routing decision."""

    content_type: ContentType = Field(description="Type of content to generate")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence score for the routing"
    )
    reasoning: str = Field(default="", description="Reasoning for the routing decision")
    requires_research: bool = Field(
        default=False, description="Whether research is needed first"
    )
    follow_up_types: list[ContentType] = Field(
        default_factory=list, description="Suggested follow-up content types"
    )


class ContentRouter:
    """
    Intelligent router that classifies user intent and routes to appropriate agents.
    
    The router uses keyword matching, pattern recognition, and context analysis
    to determine the best agent to handle a user's request.
    """

    # Keywords associated with each content type
    CONTENT_KEYWORDS: dict[ContentType, list[str]] = {
        ContentType.RESEARCH: [
            "research",
            "find",
            "search",
            "look up",
            "investigate",
            "analyze",
            "study",
            "explore",
            "discover",
            "learn about",
            "what is",
            "who is",
            "how does",
            "why does",
            "explain",
            "information",
            "data",
            "facts",
            "statistics",
            "trends",
        ],
        ContentType.BLOG: [
            "blog",
            "article",
            "post",
            "write",
            "content",
            "seo",
            "long-form",
            "guide",
            "tutorial",
            "how-to",
            "listicle",
            "review",
            "comparison",
            "pillar",
            "evergreen",
        ],
        ContentType.LINKEDIN: [
            "linkedin",
            "professional",
            "network",
            "career",
            "business post",
            "thought leadership",
            "engagement",
            "social media",
            "professional network",
            "b2b",
            "corporate",
            "industry",
        ],
        ContentType.IMAGE: [
            "image",
            "picture",
            "visual",
            "graphic",
            "illustration",
            "photo",
            "design",
            "create image",
            "generate image",
            "artwork",
            "banner",
            "thumbnail",
            "infographic",
        ],
        ContentType.STRATEGY: [
            "strategy",
            "plan",
            "campaign",
            "marketing",
            "content calendar",
            "roadmap",
            "outline",
            "framework",
            "approach",
            "methodology",
        ],
    }

    # Patterns for more specific intent detection
    INTENT_PATTERNS: dict[ContentType, list[str]] = {
        ContentType.RESEARCH: [
            r"(?:can you |please )?(?:research|find|look up|search for)\s+.+",
            r"what (?:is|are|does|do)\s+.+",
            r"tell me (?:about|more about)\s+.+",
            r"i (?:want|need) (?:to know|information) about\s+.+",
        ],
        ContentType.BLOG: [
            r"(?:write|create|generate) (?:a |an )?(?:blog|article|post)\s+.+",
            r"(?:blog|article) (?:about|on)\s+.+",
            r"seo (?:content|article|blog)\s+.+",
        ],
        ContentType.LINKEDIN: [
            r"(?:write|create|generate) (?:a )?linkedin (?:post|content)\s*.*",
            r"linkedin (?:post|content) (?:about|on)\s+.+",
            r"professional (?:post|content) (?:about|for)\s+.+",
        ],
        ContentType.IMAGE: [
            r"(?:create|generate|make) (?:a |an )?(?:image|picture|visual|graphic)\s+.+",
            r"(?:image|picture|visual) (?:of|for|about)\s+.+",
            r"design (?:a |an )?.+",
        ],
        ContentType.STRATEGY: [
            r"(?:create|develop|build) (?:a )?(?:content )?strategy\s*.*",
            r"(?:marketing|content) plan (?:for|about)\s+.+",
            r"campaign (?:for|about)\s+.+",
        ],
    }

    def __init__(self):
        """Initialize the content router."""
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficient matching."""
        self._compiled_patterns: dict[ContentType, list[re.Pattern]] = {}
        for content_type, patterns in self.INTENT_PATTERNS.items():
            self._compiled_patterns[content_type] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]

    def route(
        self,
        user_input: str,
        context: Optional[dict] = None,
        conversation_history: Optional[list[dict]] = None,
    ) -> RoutingDecision:
        """
        Route user input to the appropriate content type.
        
        Args:
            user_input: The user's request or query
            context: Optional context information
            conversation_history: Optional conversation history for context
            
        Returns:
            RoutingDecision: The routing decision with content type and metadata
        """
        user_input_lower = user_input.lower().strip()

        # First, try pattern matching for high-confidence routing
        pattern_match = self._match_patterns(user_input_lower)
        if pattern_match:
            return self._create_decision(
                pattern_match,
                confidence=0.9,
                reasoning="Matched intent pattern",
                user_input=user_input,
            )

        # Fall back to keyword matching
        keyword_scores = self._score_keywords(user_input_lower)
        if keyword_scores:
            best_match = max(keyword_scores.items(), key=lambda x: x[1])
            if best_match[1] > 0:
                return self._create_decision(
                    best_match[0],
                    confidence=min(0.8, 0.3 + (best_match[1] * 0.1)),
                    reasoning=f"Matched {best_match[1]} keywords",
                    user_input=user_input,
                )

        # Check conversation history for context
        if conversation_history:
            context_type = self._infer_from_history(conversation_history)
            if context_type:
                return self._create_decision(
                    context_type,
                    confidence=0.6,
                    reasoning="Inferred from conversation context",
                    user_input=user_input,
                )

        # Default to general/research for unknown intents
        return self._create_decision(
            ContentType.GENERAL,
            confidence=0.5,
            reasoning="No specific intent detected, defaulting to general assistance",
            user_input=user_input,
        )

    def _match_patterns(self, text: str) -> Optional[ContentType]:
        """
        Match text against compiled patterns.
        
        Args:
            text: Lowercase text to match
            
        Returns:
            ContentType if matched, None otherwise
        """
        for content_type, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    return content_type
        return None

    def _score_keywords(self, text: str) -> dict[ContentType, int]:
        """
        Score text based on keyword matches.
        
        Args:
            text: Lowercase text to score
            
        Returns:
            Dictionary of content types to match scores
        """
        scores: dict[ContentType, int] = {}
        for content_type, keywords in self.CONTENT_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                scores[content_type] = score
        return scores

    def _infer_from_history(
        self, conversation_history: list[dict]
    ) -> Optional[ContentType]:
        """
        Infer content type from conversation history.
        
        Args:
            conversation_history: List of previous conversation turns
            
        Returns:
            ContentType if inferred, None otherwise
        """
        if not conversation_history:
            return None

        # Look at the last few messages for context
        recent_messages = conversation_history[-3:]
        for message in reversed(recent_messages):
            content = message.get("content", "").lower()
            for content_type, keywords in self.CONTENT_KEYWORDS.items():
                if any(keyword in content for keyword in keywords[:5]):
                    return content_type
        return None

    def _create_decision(
        self,
        content_type: ContentType,
        confidence: float,
        reasoning: str,
        user_input: str,
    ) -> RoutingDecision:
        """
        Create a routing decision with follow-up suggestions.
        
        Args:
            content_type: The determined content type
            confidence: Confidence score
            reasoning: Reasoning for the decision
            user_input: Original user input
            
        Returns:
            RoutingDecision with all metadata
        """
        # Determine if research is needed first
        requires_research = content_type in [
            ContentType.BLOG,
            ContentType.LINKEDIN,
            ContentType.STRATEGY,
        ] and "research" not in user_input.lower()

        # Suggest follow-up content types
        follow_ups = self._suggest_follow_ups(content_type)

        return RoutingDecision(
            content_type=content_type,
            confidence=confidence,
            reasoning=reasoning,
            requires_research=requires_research,
            follow_up_types=follow_ups,
        )

    def _suggest_follow_ups(self, content_type: ContentType) -> list[ContentType]:
        """
        Suggest follow-up content types based on current type.
        
        Args:
            content_type: Current content type
            
        Returns:
            List of suggested follow-up content types
        """
        suggestions: dict[ContentType, list[ContentType]] = {
            ContentType.RESEARCH: [
                ContentType.BLOG,
                ContentType.LINKEDIN,
                ContentType.IMAGE,
            ],
            ContentType.BLOG: [ContentType.LINKEDIN, ContentType.IMAGE],
            ContentType.LINKEDIN: [ContentType.IMAGE],
            ContentType.IMAGE: [],
            ContentType.STRATEGY: [
                ContentType.RESEARCH,
                ContentType.BLOG,
                ContentType.LINKEDIN,
            ],
            ContentType.GENERAL: [ContentType.RESEARCH],
        }
        return suggestions.get(content_type, [])

    def get_agent_for_type(self, content_type: ContentType) -> str:
        """
        Get the agent name for a content type.
        
        Args:
            content_type: The content type
            
        Returns:
            Agent name string
        """
        agent_mapping = {
            ContentType.RESEARCH: "research_agent",
            ContentType.BLOG: "blog_writer_agent",
            ContentType.LINKEDIN: "linkedin_writer_agent",
            ContentType.IMAGE: "image_generator_agent",
            ContentType.STRATEGY: "content_strategist_agent",
            ContentType.GENERAL: "query_handler_agent",
        }
        return agent_mapping.get(content_type, "query_handler_agent")