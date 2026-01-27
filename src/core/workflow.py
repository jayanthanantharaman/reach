"""
Content Workflow Orchestration for REACH.


This module defines the main workflow orchestration using LangGraph
for managing multi-agent content creation pipelines.
"""

import logging
from typing import Any, Optional

from pydantic import BaseModel, Field

from .router import ContentRouter, ContentType, RoutingDecision

logger = logging.getLogger(__name__)


class ContentRequest(BaseModel):
    """Model representing a content creation request."""

    user_input: str = Field(description="User's content request")
    content_type: Optional[ContentType] = Field(
        default=None, description="Explicit content type if specified"
    )
    topic: Optional[str] = Field(default=None, description="Main topic for content")
    keywords: list[str] = Field(
        default_factory=list, description="Target keywords for SEO"
    )
    tone: str = Field(default="professional", description="Desired tone of content")
    target_audience: Optional[str] = Field(
        default=None, description="Target audience description"
    )
    additional_context: dict[str, Any] = Field(
        default_factory=dict, description="Additional context for content creation"
    )


class ContentResponse(BaseModel):
    """Model representing a content creation response."""

    content_type: ContentType = Field(description="Type of content generated")
    content: str = Field(description="Generated content")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Content metadata"
    )
    quality_score: Optional[float] = Field(
        default=None, description="Quality score if validated"
    )
    suggestions: list[str] = Field(
        default_factory=list, description="Improvement suggestions"
    )
    follow_up_options: list[ContentType] = Field(
        default_factory=list, description="Suggested follow-up content types"
    )
    error: Optional[str] = Field(default=None, description="Error message if any")


class WorkflowState(BaseModel):
    """State model for the content workflow."""

    request: ContentRequest = Field(description="Original content request")
    routing_decision: Optional[RoutingDecision] = Field(
        default=None, description="Routing decision"
    )
    research_results: Optional[dict[str, Any]] = Field(
        default=None, description="Research results if applicable"
    )
    generated_content: Optional[str] = Field(
        default=None, description="Generated content"
    )
    quality_validated: bool = Field(
        default=False, description="Whether quality validation passed"
    )
    quality_score: Optional[float] = Field(
        default=None, description="Quality validation score"
    )
    error: Optional[str] = Field(default=None, description="Error message if any")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Workflow metadata"
    )


class ContentWorkflow:
    """
    Main workflow orchestrator for content creation.
    
    This class manages the flow of content creation requests through
    various agents and ensures proper sequencing and error handling.
    """

    def __init__(self):
        """Initialize the content workflow."""
        self.router = ContentRouter()
        self._agents: dict[str, Any] = {}
        self._initialized = False

    def register_agent(self, agent_name: str, agent: Any) -> None:
        """
        Register an agent with the workflow.
        
        Args:
            agent_name: Name identifier for the agent
            agent: Agent instance
        """
        self._agents[agent_name] = agent
        logger.info(f"Registered agent: {agent_name}")

    def get_agent(self, agent_name: str) -> Optional[Any]:
        """
        Get a registered agent by name.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Agent instance or None if not found
        """
        return self._agents.get(agent_name)

    async def process_request(
        self,
        request: ContentRequest,
        conversation_history: Optional[list[dict]] = None,
    ) -> ContentResponse:
        """
        Process a content creation request through the workflow.
        
        Args:
            request: Content creation request
            conversation_history: Optional conversation history
            
        Returns:
            ContentResponse with generated content or error
        """
        try:
            # Initialize workflow state
            state = WorkflowState(request=request)

            # Step 1: Route the request
            state = await self._route_request(state, conversation_history)
            if state.error:
                return self._create_error_response(state)

            # Step 2: Perform research if needed
            if state.routing_decision and state.routing_decision.requires_research:
                state = await self._perform_research(state)
                if state.error:
                    return self._create_error_response(state)

            # Step 3: Generate content
            state = await self._generate_content(state)
            if state.error:
                return self._create_error_response(state)

            # Step 4: Validate quality
            state = await self._validate_quality(state)

            # Step 5: Create response
            return self._create_success_response(state)

        except Exception as e:
            logger.error(f"Workflow error: {str(e)}")
            return ContentResponse(
                content_type=ContentType.GENERAL,
                content="",
                error=f"Workflow error: {str(e)}",
            )

    async def _route_request(
        self,
        state: WorkflowState,
        conversation_history: Optional[list[dict]] = None,
    ) -> WorkflowState:
        """
        Route the request to determine content type.
        
        Args:
            state: Current workflow state
            conversation_history: Optional conversation history
            
        Returns:
            Updated workflow state
        """
        try:
            # Use explicit content type if provided
            if state.request.content_type:
                state.routing_decision = RoutingDecision(
                    content_type=state.request.content_type,
                    confidence=1.0,
                    reasoning="Explicit content type specified",
                )
            else:
                # Route based on user input
                state.routing_decision = self.router.route(
                    state.request.user_input,
                    context=state.request.additional_context,
                    conversation_history=conversation_history,
                )

            state.metadata["routing"] = {
                "content_type": state.routing_decision.content_type.value,
                "confidence": state.routing_decision.confidence,
                "reasoning": state.routing_decision.reasoning,
            }

            logger.info(
                f"Routed to {state.routing_decision.content_type.value} "
                f"with confidence {state.routing_decision.confidence}"
            )

        except Exception as e:
            state.error = f"Routing error: {str(e)}"
            logger.error(state.error)

        return state

    async def _perform_research(self, state: WorkflowState) -> WorkflowState:
        """
        Perform research using the research agent.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state with research results
        """
        try:
            research_agent = self.get_agent("research_agent")
            if not research_agent:
                logger.warning("Research agent not available, skipping research")
                return state

            # Extract topic from request
            topic = state.request.topic or state.request.user_input

            # Perform research
            research_results = await research_agent.research(topic)
            state.research_results = research_results
            state.metadata["research_performed"] = True

            logger.info(f"Research completed for topic: {topic}")

        except Exception as e:
            logger.warning(f"Research error (non-fatal): {str(e)}")
            state.metadata["research_error"] = str(e)

        return state

    async def _generate_content(self, state: WorkflowState) -> WorkflowState:
        """
        Generate content using the appropriate agent.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state with generated content
        """
        try:
            if not state.routing_decision:
                state.error = "No routing decision available"
                return state

            # Get the appropriate agent
            agent_name = self.router.get_agent_for_type(
                state.routing_decision.content_type
            )
            agent = self.get_agent(agent_name)

            if not agent:
                # Fall back to query handler
                agent = self.get_agent("query_handler_agent")
                if not agent:
                    state.error = f"Agent not available: {agent_name}"
                    return state

            # Prepare generation context
            context = {
                "topic": state.request.topic or state.request.user_input,
                "keywords": state.request.keywords,
                "tone": state.request.tone,
                "target_audience": state.request.target_audience,
                "research_results": state.research_results,
                **state.request.additional_context,
            }

            # Generate content
            content = await agent.generate(
                state.request.user_input,
                context=context,
            )
            state.generated_content = content
            state.metadata["agent_used"] = agent_name

            logger.info(f"Content generated using {agent_name}")

        except Exception as e:
            state.error = f"Content generation error: {str(e)}"
            logger.error(state.error)

        return state

    async def _validate_quality(self, state: WorkflowState) -> WorkflowState:
        """
        Validate content quality.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state with quality validation results
        """
        try:
            if not state.generated_content:
                return state

            # Basic quality checks
            content_length = len(state.generated_content)
            has_content = content_length > 50

            # Calculate basic quality score
            quality_score = 0.0
            if has_content:
                quality_score += 0.5
            if content_length > 200:
                quality_score += 0.2
            if content_length > 500:
                quality_score += 0.2
            if state.research_results:
                quality_score += 0.1

            state.quality_score = min(1.0, quality_score)
            state.quality_validated = state.quality_score >= 0.5
            state.metadata["quality_validation"] = {
                "score": state.quality_score,
                "passed": state.quality_validated,
                "content_length": content_length,
            }

            logger.info(f"Quality validation: score={state.quality_score}")

        except Exception as e:
            logger.warning(f"Quality validation error (non-fatal): {str(e)}")

        return state

    def _create_success_response(self, state: WorkflowState) -> ContentResponse:
        """
        Create a successful content response.
        
        Args:
            state: Final workflow state
            
        Returns:
            ContentResponse with generated content
        """
        follow_ups = []
        if state.routing_decision:
            follow_ups = state.routing_decision.follow_up_types

        return ContentResponse(
            content_type=state.routing_decision.content_type
            if state.routing_decision
            else ContentType.GENERAL,
            content=state.generated_content or "",
            metadata=state.metadata,
            quality_score=state.quality_score,
            suggestions=self._generate_suggestions(state),
            follow_up_options=follow_ups,
        )

    def _create_error_response(self, state: WorkflowState) -> ContentResponse:
        """
        Create an error content response.
        
        Args:
            state: Workflow state with error
            
        Returns:
            ContentResponse with error information
        """
        return ContentResponse(
            content_type=state.routing_decision.content_type
            if state.routing_decision
            else ContentType.GENERAL,
            content="",
            metadata=state.metadata,
            error=state.error,
        )

    def _generate_suggestions(self, state: WorkflowState) -> list[str]:
        """
        Generate improvement suggestions based on content.
        
        Args:
            state: Final workflow state
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []

        if state.quality_score and state.quality_score < 0.8:
            suggestions.append("Consider adding more detail to improve content depth")

        if not state.research_results:
            suggestions.append(
                "Adding research could improve content accuracy and credibility"
            )

        if state.routing_decision:
            if state.routing_decision.content_type == ContentType.BLOG:
                suggestions.append("Consider adding relevant images to enhance the blog")
            elif state.routing_decision.content_type == ContentType.LINKEDIN:
                suggestions.append("Consider creating a supporting image for the post")

        return suggestions