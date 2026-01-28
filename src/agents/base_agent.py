"""
Base Agent for REACH.


This module defines the base agent class that all specialized agents inherit from.
It provides common functionality for LLM interaction, error handling, and logging.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel, Field

from ..core.config import get_settings

logger = logging.getLogger(__name__)


def _get_default_model() -> str:
    """Get default model from settings."""
    return get_settings().gemini_model


def _get_default_temperature() -> float:
    """Get default temperature from settings."""
    return get_settings().gemini_temperature


def _get_default_max_tokens() -> int:
    """Get default max tokens from settings."""
    return get_settings().gemini_max_tokens


class AgentConfig(BaseModel):
    """Configuration for an agent."""

    name: str = Field(description="Agent name")
    description: str = Field(description="Agent description")
    model: str = Field(default_factory=_get_default_model, description="LLM model to use")
    temperature: float = Field(default_factory=_get_default_temperature, description="Temperature for generation")
    max_tokens: int = Field(default_factory=_get_default_max_tokens, description="Maximum tokens for response")
    system_prompt: str = Field(default="", description="System prompt for the agent")


class AgentResponse(BaseModel):
    """Standard response from an agent."""

    content: str = Field(description="Generated content")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Response metadata"
    )
    tokens_used: Optional[int] = Field(default=None, description="Tokens used")
    model: str = Field(default="", description="Model used for generation")
    error: Optional[str] = Field(default=None, description="Error message if any")


class BaseAgent(ABC):
    """
    Abstract base class for all content agents.
    
    This class provides common functionality including:
    - LLM client management
    - Prompt formatting
    - Error handling
    - Logging
    - Response parsing
    """

    def __init__(
        self,
        config: AgentConfig,
        llm_client: Optional[Any] = None,
    ):
        """
        Initialize the base agent.
        
        Args:
            config: Agent configuration
            llm_client: Optional LLM client instance
        """
        self.config = config
        self.llm_client = llm_client
        self._conversation_history: list[dict] = []
        logger.info(f"Initialized agent: {config.name}")

    @property
    def name(self) -> str:
        """Get agent name."""
        return self.config.name

    @property
    def description(self) -> str:
        """Get agent description."""
        return self.config.description

    def set_llm_client(self, client: Any) -> None:
        """
        Set the LLM client for this agent.
        
        Args:
            client: LLM client instance
        """
        self.llm_client = client
        logger.info(f"LLM client set for agent: {self.name}")

    @abstractmethod
    async def generate(
        self,
        user_input: str,
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Generate content based on user input.
        
        Args:
            user_input: User's request or query
            context: Optional context for generation
            
        Returns:
            Generated content string
        """
        pass

    async def _call_llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AgentResponse:
        """
        Call the LLM with the given prompt.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt override
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            
        Returns:
            AgentResponse with generated content
        """
        if not self.llm_client:
            return AgentResponse(
                content="",
                error="LLM client not configured",
            )

        try:
            # Use provided values or defaults from config
            sys_prompt = system_prompt or self.config.system_prompt
            temp = temperature if temperature is not None else self.config.temperature
            tokens = max_tokens or self.config.max_tokens

            # Call the LLM client
            response = await self.llm_client.generate(
                prompt=prompt,
                system_prompt=sys_prompt,
                temperature=temp,
                max_tokens=tokens,
            )

            return AgentResponse(
                content=response.get("content", ""),
                metadata=response.get("metadata", {}),
                tokens_used=response.get("tokens_used"),
                model=response.get("model", self.config.model),
            )

        except Exception as e:
            logger.error(f"LLM call error in {self.name}: {str(e)}")
            return AgentResponse(
                content="",
                error=f"LLM error: {str(e)}",
            )

    def _format_prompt(
        self,
        template: str,
        **kwargs: Any,
    ) -> str:
        """
        Format a prompt template with provided values.
        
        Args:
            template: Prompt template string
            **kwargs: Values to substitute in template
            
        Returns:
            Formatted prompt string
        """
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing template key: {e}")
            return template

    def add_to_history(
        self,
        role: str,
        content: str,
    ) -> None:
        """
        Add a message to conversation history.
        
        Args:
            role: Message role (user, assistant, system)
            content: Message content
        """
        self._conversation_history.append({
            "role": role,
            "content": content,
        })

        # Limit history size
        max_history = 20
        if len(self._conversation_history) > max_history:
            self._conversation_history = self._conversation_history[-max_history:]

    def get_history(self) -> list[dict]:
        """
        Get conversation history.
        
        Returns:
            List of conversation messages
        """
        return self._conversation_history.copy()

    def clear_history(self) -> None:
        """Clear conversation history."""
        self._conversation_history = []
        logger.info(f"Cleared history for agent: {self.name}")

    def _extract_context_summary(
        self,
        context: Optional[dict[str, Any]],
    ) -> str:
        """
        Extract a summary from context for prompt inclusion.
        
        Args:
            context: Context dictionary
            
        Returns:
            Context summary string
        """
        if not context:
            return ""

        summary_parts = []

        if context.get("topic"):
            summary_parts.append(f"Topic: {context['topic']}")

        if context.get("keywords"):
            keywords = ", ".join(context["keywords"][:5])
            summary_parts.append(f"Keywords: {keywords}")

        if context.get("tone"):
            summary_parts.append(f"Tone: {context['tone']}")

        if context.get("target_audience"):
            summary_parts.append(f"Target Audience: {context['target_audience']}")

        if context.get("research_results"):
            research = context["research_results"]
            if isinstance(research, dict):
                if research.get("summary"):
                    summary_parts.append(f"Research Summary: {research['summary'][:500]}")
                elif research.get("key_points"):
                    points = research["key_points"][:3]
                    summary_parts.append(f"Key Points: {', '.join(points)}")

        return "\n".join(summary_parts)

    def _validate_response(
        self,
        response: str,
        min_length: int = 50,
    ) -> tuple[bool, str]:
        """
        Validate generated response.
        
        Args:
            response: Generated response
            min_length: Minimum acceptable length
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not response:
            return False, "Empty response"

        if len(response) < min_length:
            return False, f"Response too short (min {min_length} chars)"

        return True, ""

    async def _retry_generation(
        self,
        prompt: str,
        max_retries: int = 2,
        **kwargs: Any,
    ) -> AgentResponse:
        """
        Retry generation with exponential backoff.
        
        Args:
            prompt: Generation prompt
            max_retries: Maximum retry attempts
            **kwargs: Additional arguments for _call_llm
            
        Returns:
            AgentResponse from successful attempt or last error
        """
        last_response = None

        for attempt in range(max_retries + 1):
            response = await self._call_llm(prompt, **kwargs)

            if not response.error:
                is_valid, error = self._validate_response(response.content)
                if is_valid:
                    return response
                response.error = error

            last_response = response

            if attempt < max_retries:
                logger.warning(
                    f"Retry {attempt + 1}/{max_retries} for {self.name}: {response.error}"
                )

        return last_response or AgentResponse(
            content="",
            error="Max retries exceeded",
        )