"""
LangGraph Workflow for REACH - Real Estate Automated Content Hub.


This module implements the multi-agent workflow using LangGraph
for orchestrating real estate content creation tasks with guardrails.
"""

import logging
from typing import Any, Literal, Optional, TypedDict

from langgraph.graph import END, StateGraph

from ..agents import (
    BlogWriterAgent,
    ContentStrategistAgent,
    ImageGeneratorAgent,
    InstagramWriterAgent,
    LinkedInWriterAgent,
    QueryHandlerAgent,
    ResearchAgent,
)
from ..core.router import ContentRouter, RoutingDecision
from ..guardrails import GuardrailsManager
from ..integrations import GeminiClient, ImagenClient, SerpClient
from .state_management import ConversationState, SessionManager

logger = logging.getLogger(__name__)


class GraphState(TypedDict):
    """State for the LangGraph workflow."""

    user_input: str
    route_decision: Optional[RoutingDecision]
    research_results: Optional[dict[str, Any]]
    generated_content: Optional[str]
    content_type: Optional[str]
    error: Optional[str]
    conversation_history: list[dict[str, str]]
    context: dict[str, Any]
    guardrails_result: Optional[dict[str, Any]]


class REACHGraph:
    """
    REACH - Real Estate Automated Content Hub.
    
    LangGraph-based workflow for real estate content creation.
    This class orchestrates the multi-agent system using LangGraph
    to route requests and generate content with guardrails protection.
    
    Guardrails:
    - Topical: Restricts to Real Estate topics only
    - Safety: Blocks profanity and inappropriate content
    """

    def __init__(
        self,
        gemini_client: Optional[GeminiClient] = None,
        imagen_client: Optional[ImagenClient] = None,
        serp_client: Optional[SerpClient] = None,
        enable_guardrails: bool = True,
    ):
        """
        Initialize the REACH graph.
        
        Args:
            gemini_client: Optional Gemini client
            imagen_client: Optional Imagen client for image generation
            serp_client: Optional SERP API client
            enable_guardrails: Enable topical and safety guardrails
        """
        # Initialize clients
        self.gemini_client = gemini_client or GeminiClient()
        self.imagen_client = imagen_client or ImagenClient()
        self.serp_client = serp_client or SerpClient()

        # Initialize agents
        self._init_agents()

        # Initialize router
        self.router = ContentRouter()

        # Initialize session manager
        self.session_manager = SessionManager()

        # Initialize guardrails
        self.enable_guardrails = enable_guardrails
        self.guardrails = GuardrailsManager(
            llm_client=self.gemini_client,
            enable_topical=enable_guardrails,
            enable_safety=enable_guardrails,
            strict_mode=True,
        ) if enable_guardrails else None

        # Build the graph
        self.graph = self._build_graph()

        logger.info(f"REACHGraph initialized with guardrails={enable_guardrails}")

    def _init_agents(self) -> None:
        """Initialize all agents."""
        self.query_handler = QueryHandlerAgent(llm_client=self.gemini_client)
        self.research_agent = ResearchAgent(
            llm_client=self.gemini_client,
            serp_client=self.serp_client,
        )
        # Blog writer now includes image generation capability
        self.blog_writer = BlogWriterAgent(
            llm_client=self.gemini_client,
            image_client=self.imagen_client,
        )
        self.linkedin_writer = LinkedInWriterAgent(llm_client=self.gemini_client)
        self.instagram_writer = InstagramWriterAgent(llm_client=self.gemini_client)
        self.image_generator = ImageGeneratorAgent(
            llm_client=self.gemini_client,
            image_client=self.imagen_client,
        )
        self.content_strategist = ContentStrategistAgent(llm_client=self.gemini_client)

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        # Create the graph
        workflow = StateGraph(GraphState)

        # Add nodes
        workflow.add_node("guardrails", self._guardrails_node)
        workflow.add_node("route", self._route_node)
        workflow.add_node("research", self._research_node)
        workflow.add_node("blog", self._blog_node)
        workflow.add_node("linkedin", self._linkedin_node)
        workflow.add_node("instagram", self._instagram_node)
        workflow.add_node("image", self._image_node)
        workflow.add_node("strategy", self._strategy_node)
        workflow.add_node("general", self._general_node)

        # Set entry point to guardrails
        workflow.set_entry_point("guardrails")

        # Add conditional edge from guardrails
        workflow.add_conditional_edges(
            "guardrails",
            self._check_guardrails_passed,
            {
                "passed": "route",
                "blocked": END,
            },
        )

        # Add conditional edges from route
        workflow.add_conditional_edges(
            "route",
            self._determine_next_node,
            {
                "research": "research",
                "blog": "blog",
                "linkedin": "linkedin",
                "instagram": "instagram",
                "image": "image",
                "strategy": "strategy",
                "general": "general",
                "end": END,
            },
        )

        # Add edges from content nodes to end
        workflow.add_edge("research", END)
        workflow.add_edge("blog", END)
        workflow.add_edge("linkedin", END)
        workflow.add_edge("instagram", END)
        workflow.add_edge("image", END)
        workflow.add_edge("strategy", END)
        workflow.add_edge("general", END)

        return workflow.compile()

    def _check_guardrails_passed(
        self,
        state: GraphState,
    ) -> Literal["passed", "blocked"]:
        """Check if guardrails validation passed."""
        guardrails_result = state.get("guardrails_result")

        if guardrails_result and not guardrails_result.get("passed", True):
            return "blocked"

        return "passed"

    def _determine_next_node(
        self,
        state: GraphState,
    ) -> Literal["research", "blog", "linkedin", "instagram", "image", "strategy", "general", "end"]:
        """Determine the next node based on route decision."""
        if state.get("error"):
            return "end"

        route = state.get("route_decision")
        if not route:
            return "general"

        content_type = route.content_type.value if hasattr(route.content_type, "value") else str(route.content_type)

        if content_type == "research":
            return "research"
        if content_type == "blog":
            return "blog"
        if content_type == "linkedin":
            return "linkedin"
        if content_type == "instagram":
            return "instagram"
        if content_type == "image":
            return "image"
        if content_type == "strategy":
            return "strategy"
        return "general"

    async def _guardrails_node(self, state: GraphState) -> GraphState:
        """
        Validate user input against guardrails.
        
        Checks:
        1. Safety - blocks profanity and inappropriate content
        2. Topical - ensures request is about Real Estate
        """
        if not self.guardrails:
            return {
                **state,
                "guardrails_result": {"passed": True, "message": None},
            }

        try:
            user_input = state["user_input"]

            # Determine content type for validation
            content_type = "text"
            if any(word in user_input.lower() for word in ["image", "picture", "photo", "generate image"]):
                content_type = "image"

            # Validate input
            result = await self.guardrails.validate_input(user_input, content_type)

            if not result["passed"]:
                logger.info(f"Guardrails blocked request: {result['blocked_by']}")
                return {
                    **state,
                    "guardrails_result": result,
                    "generated_content": result["message"],
                    "content_type": "guardrails_blocked",
                    "error": None,
                }

            return {
                **state,
                "guardrails_result": result,
            }

        except Exception as e:
            logger.error(f"Guardrails error: {str(e)}")
            # On error, allow the request to proceed
            return {
                **state,
                "guardrails_result": {"passed": True, "message": None, "error": str(e)},
            }

    async def _route_node(self, state: GraphState) -> GraphState:
        """Route the user input to the appropriate agent."""
        try:
            user_input = state["user_input"]
            history = state.get("conversation_history", [])

            route_decision = self.router.route(
                user_input,
                conversation_history=history,
            )

            return {
                **state,
                "route_decision": route_decision,
            }
        except Exception as e:
            logger.error(f"Routing error: {str(e)}")
            return {
                **state,
                "error": f"Routing failed: {str(e)}",
            }

    async def _research_node(self, state: GraphState) -> GraphState:
        """Execute research agent."""
        try:
            user_input = state["user_input"]
            context = state.get("context", {})

            result = await self.research_agent.generate(user_input, context)

            # Validate output
            if self.guardrails:
                output_check = await self.guardrails.validate_output(result)
                if not output_check["passed"]:
                    result = "I apologize, but I cannot provide that response. Please try a different query."

            return {
                **state,
                "generated_content": result,
                "content_type": "research",
                "research_results": {"summary": result},
            }
        except Exception as e:
            logger.error(f"Research error: {str(e)}")
            return {
                **state,
                "error": f"Research failed: {str(e)}",
            }

    async def _blog_node(self, state: GraphState) -> GraphState:
        """Execute blog writer agent."""
        try:
            user_input = state["user_input"]
            context = state.get("context", {})

            # Include research results if available
            if state.get("research_results"):
                context["research_results"] = state["research_results"]

            result = await self.blog_writer.generate(user_input, context)

            # Validate output
            if self.guardrails:
                output_check = await self.guardrails.validate_output(result)
                if not output_check["passed"]:
                    result = "I apologize, but I cannot provide that response. Please try a different query."

            return {
                **state,
                "generated_content": result,
                "content_type": "blog",
            }
        except Exception as e:
            logger.error(f"Blog writing error: {str(e)}")
            return {
                **state,
                "error": f"Blog writing failed: {str(e)}",
            }

    async def _linkedin_node(self, state: GraphState) -> GraphState:
        """Execute LinkedIn writer agent."""
        try:
            user_input = state["user_input"]
            context = state.get("context", {})

            result = await self.linkedin_writer.generate(user_input, context)

            # Validate output
            if self.guardrails:
                output_check = await self.guardrails.validate_output(result)
                if not output_check["passed"]:
                    result = "I apologize, but I cannot provide that response. Please try a different query."

            return {
                **state,
                "generated_content": result,
                "content_type": "linkedin",
            }
        except Exception as e:
            logger.error(f"LinkedIn writing error: {str(e)}")
            return {
                **state,
                "error": f"LinkedIn writing failed: {str(e)}",
            }

    async def _instagram_node(self, state: GraphState) -> GraphState:
        """Execute Instagram caption writer agent."""
        try:
            user_input = state["user_input"]
            context = state.get("context", {})

            result = await self.instagram_writer.generate(user_input, context)

            # Validate output
            if self.guardrails:
                output_check = await self.guardrails.validate_output(result)
                if not output_check["passed"]:
                    result = "I apologize, but I cannot provide that response. Please try a different query."

            return {
                **state,
                "generated_content": result,
                "content_type": "instagram",
            }
        except Exception as e:
            logger.error(f"Instagram caption writing error: {str(e)}")
            return {
                **state,
                "error": f"Instagram caption writing failed: {str(e)}",
            }

    async def _image_node(self, state: GraphState) -> GraphState:
        """Execute image generator agent."""
        try:
            user_input = state["user_input"]
            context = state.get("context", {})

            # Additional image safety check
            if self.guardrails:
                image_check = await self.guardrails.validate_image_request(user_input)
                if not image_check["passed"]:
                    return {
                        **state,
                        "generated_content": image_check["message"],
                        "content_type": "image_blocked",
                    }

            result = await self.image_generator.generate(user_input, context)

            return {
                **state,
                "generated_content": result,
                "content_type": "image",
            }
        except Exception as e:
            logger.error(f"Image generation error: {str(e)}")
            return {
                **state,
                "error": f"Image generation failed: {str(e)}",
            }

    async def _strategy_node(self, state: GraphState) -> GraphState:
        """Execute content strategist agent."""
        try:
            user_input = state["user_input"]
            context = state.get("context", {})

            result = await self.content_strategist.generate(user_input, context)

            # Validate output
            if self.guardrails:
                output_check = await self.guardrails.validate_output(result)
                if not output_check["passed"]:
                    result = "I apologize, but I cannot provide that response. Please try a different query."

            return {
                **state,
                "generated_content": result,
                "content_type": "strategy",
            }
        except Exception as e:
            logger.error(f"Strategy error: {str(e)}")
            return {
                **state,
                "error": f"Strategy generation failed: {str(e)}",
            }

    async def _general_node(self, state: GraphState) -> GraphState:
        """Handle general queries."""
        try:
            user_input = state["user_input"]
            context = state.get("context", {})

            result = await self.query_handler.generate(user_input, context)

            # Validate output
            if self.guardrails:
                output_check = await self.guardrails.validate_output(result)
                if not output_check["passed"]:
                    result = "I apologize, but I cannot provide that response. Please try a different query."

            return {
                **state,
                "generated_content": result,
                "content_type": "general",
            }
        except Exception as e:
            logger.error(f"General query error: {str(e)}")
            return {
                **state,
                "error": f"Query handling failed: {str(e)}",
            }

    async def run(
        self,
        user_input: str,
        session_id: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Run the content creation workflow.
        
        Args:
            user_input: User's request
            session_id: Optional session ID for conversation continuity
            context: Optional additional context
            
        Returns:
            Dictionary with generated content and metadata
        """
        # Get or create session
        session = self.session_manager.get_or_create_session(
            session_id or "default",
            initial_context=context,
        )

        # Add user message to history
        session.add_message("user", user_input)

        # Prepare initial state
        initial_state: GraphState = {
            "user_input": user_input,
            "route_decision": None,
            "research_results": session.context.get("research_results"),
            "generated_content": None,
            "content_type": None,
            "error": None,
            "conversation_history": session.get_history(limit=10),
            "context": {**session.context, **(context or {})},
            "guardrails_result": None,
        }

        # Run the graph
        try:
            result = await self.graph.ainvoke(initial_state)

            # Check if blocked by guardrails
            guardrails_result = result.get("guardrails_result", {})
            was_blocked = not guardrails_result.get("passed", True)

            # Store generated content
            if result.get("generated_content"):
                session.store_content(
                    result.get("content_type", "general"),
                    result["generated_content"],
                )
                session.add_message("assistant", result["generated_content"])

            # Update context with research results
            if result.get("research_results"):
                session.update_context("research_results", result["research_results"])

            return {
                "success": not result.get("error") and not was_blocked,
                "content": result.get("generated_content", ""),
                "content_type": result.get("content_type"),
                "route": result.get("route_decision"),
                "error": result.get("error"),
                "session_id": session.conversation_id,
                "guardrails": {
                    "blocked": was_blocked,
                    "blocked_by": guardrails_result.get("blocked_by"),
                },
            }

        except Exception as e:
            logger.error(f"Workflow execution error: {str(e)}")
            error_message = f"An error occurred: {str(e)}"
            session.add_message("assistant", error_message)

            return {
                "success": False,
                "content": "",
                "content_type": None,
                "error": str(e),
                "session_id": session.conversation_id,
                "guardrails": {"blocked": False},
            }

    async def run_with_research(
        self,
        topic: str,
        content_type: str = "blog",
        session_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Run a research-first workflow.
        
        Args:
            topic: Topic to research and create content about
            content_type: Type of content to create after research
            session_id: Optional session ID
            
        Returns:
            Dictionary with research and content results
        """
        # First, do research
        research_result = await self.run(
            f"Research: {topic}",
            session_id=session_id,
        )

        if not research_result["success"]:
            return research_result

        # Then create content based on research
        content_prompts = {
            "blog": f"Write a blog post about: {topic}",
            "linkedin": f"Create a LinkedIn post about: {topic}",
            "strategy": f"Create a content strategy for: {topic}",
        }

        content_prompt = content_prompts.get(content_type, content_prompts["blog"])

        content_result = await self.run(
            content_prompt,
            session_id=session_id,
        )

        return {
            "success": content_result["success"],
            "research": research_result.get("content"),
            "content": content_result.get("content"),
            "content_type": content_type,
            "session_id": content_result.get("session_id"),
            "error": content_result.get("error"),
            "guardrails": content_result.get("guardrails"),
        }

    def get_session(self, session_id: str) -> Optional[ConversationState]:
        """Get a session by ID."""
        return self.session_manager.get_session(session_id)

    def clear_session(self, session_id: str) -> bool:
        """Clear a session's history."""
        session = self.session_manager.get_session(session_id)
        if session:
            session.clear_history()
            return True
        return False

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        return self.session_manager.delete_session(session_id)

    def get_guardrails_status(self) -> dict[str, Any]:
        """Get the current guardrails status."""
        if self.guardrails:
            return self.guardrails.get_status()
        return {"enabled": False}

    def get_topic_suggestions(self) -> list[str]:
        """Get suggestions for on-topic requests."""
        if self.guardrails:
            return self.guardrails.get_topic_suggestions()
        return []

    async def generate_instagram_post(
        self,
        image_description: str,
        property_details: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Generate a complete Instagram post with image and caption.
        
        This method generates both a property image and an engaging
        Instagram caption with relevant hashtags.
        
        Args:
            image_description: Description of the property image to generate
            property_details: Optional property details (location, price, features)
            session_id: Optional session ID
            
        Returns:
            Dictionary with image URL/data and caption with hashtags
        """
        property_details = property_details or {}

        # Validate with guardrails first
        if self.guardrails:
            # Check topical relevance
            input_check = await self.guardrails.validate_input(image_description, "image")
            if not input_check["passed"]:
                return {
                    "success": False,
                    "error": input_check["message"],
                    "guardrails": {"blocked": True, "blocked_by": input_check["blocked_by"]},
                }

            # Check image safety
            image_check = await self.guardrails.validate_image_request(image_description)
            if not image_check["passed"]:
                return {
                    "success": False,
                    "error": image_check["message"],
                    "guardrails": {"blocked": True, "blocked_by": "safety"},
                }

        try:
            # Step 1: Generate the image
            logger.info(f"Generating image for: {image_description}")
            image_result = await self.image_generator.generate(
                f"Generate a real estate image: {image_description}",
                context=property_details,
            )

            # Step 2: Generate Instagram caption with hashtags
            logger.info("Generating Instagram caption...")
            caption_result = await self.instagram_writer.generate_for_image(
                image_prompt=image_description,
                image_url=image_result if isinstance(image_result, str) and image_result.startswith("http") else None,
                property_details=property_details,
            )

            # Validate caption output
            if self.guardrails:
                output_check = await self.guardrails.validate_output(caption_result["full_post"])
                if not output_check["passed"]:
                    caption_result = {
                        "caption": "Beautiful property! Contact us for more details. 🏠",
                        "hashtags": "#realestate #property #home #dreamhome #realtor",
                        "full_post": "Beautiful property! Contact us for more details. 🏠\n\n#realestate #property #home #dreamhome #realtor",
                    }

            return {
                "success": True,
                "image": image_result,
                "caption": caption_result["caption"],
                "hashtags": caption_result["hashtags"],
                "full_post": caption_result["full_post"],
                "session_id": session_id,
                "guardrails": {"blocked": False},
            }

        except Exception as e:
            logger.error(f"Instagram post generation error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "guardrails": {"blocked": False},
            }

    def run_stream(
        self,
        user_input: str,
        session_id: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ):
        """
        Run the content creation workflow with streaming output.
        
        This is a synchronous generator that yields text chunks as they are generated.
        It bypasses the full LangGraph workflow for direct streaming from the LLM.
        
        Args:
            user_input: User's request
            session_id: Optional session ID for conversation continuity
            context: Optional additional context
            
        Yields:
            Text chunks as they are generated
        """
        # Get or create session
        session = self.session_manager.get_or_create_session(
            session_id or "default",
            initial_context=context,
        )

        # Add user message to history
        session.add_message("user", user_input)

        # Route the request to determine content type
        try:
            route_decision = self.router.route(
                user_input,
                conversation_history=session.get_history(limit=10),
            )
            content_type = route_decision.content_type.value if hasattr(route_decision.content_type, "value") else str(route_decision.content_type)
        except Exception as e:
            logger.error(f"Routing error in streaming: {str(e)}")
            content_type = "general"

        # Get the appropriate system prompt based on content type
        system_prompts = {
            "blog": """You are an expert SEO content writer specializing in real estate. 
Create engaging, informative blog posts optimized for search engines. 
Use proper headings, include keywords naturally, and provide valuable information.""",
            "linkedin": """You are an expert LinkedIn content creator for real estate professionals.
Create engaging, professional posts that drive engagement and showcase expertise.""",
            "instagram": """You are an Instagram content expert for real estate.
Create engaging captions with relevant hashtags for property posts.""",
            "research": """You are a research analyst specializing in real estate.
Provide comprehensive, well-researched information with key insights.""",
            "strategy": """You are a content strategist for real estate marketing.
Create actionable content strategies and marketing plans.""",
            "general": """You are REACH, an AI assistant for real estate content creation.
Help users create high-quality real estate marketing content.""",
        }

        system_prompt = system_prompts.get(content_type, system_prompts["general"])

        # Stream the response
        full_content = ""
        try:
            for chunk in self.gemini_client.generate_stream(
                prompt=user_input,
                system_prompt=system_prompt,
            ):
                full_content += chunk
                yield chunk

            # Store the complete content in session
            if full_content:
                session.store_content(content_type, full_content)
                session.add_message("assistant", full_content)

        except Exception as e:
            logger.error(f"Streaming error: {str(e)}")
            error_msg = f"Error generating content: {str(e)}"
            yield error_msg

    def get_streaming_metadata(
        self,
        user_input: str,
        session_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Get metadata for a streaming request without generating content.
        
        This is useful for getting the content type and other metadata
        before starting the streaming process.
        
        Args:
            user_input: User's request
            session_id: Optional session ID
            
        Returns:
            Dictionary with routing metadata
        """
        # Get or create session
        session = self.session_manager.get_or_create_session(
            session_id or "default",
        )

        # Route the request
        try:
            route_decision = self.router.route(
                user_input,
                conversation_history=session.get_history(limit=10),
            )
            content_type = route_decision.content_type.value if hasattr(route_decision.content_type, "value") else str(route_decision.content_type)
            
            return {
                "content_type": content_type,
                "confidence": route_decision.confidence,
                "session_id": session.conversation_id,
            }
        except Exception as e:
            logger.error(f"Metadata error: {str(e)}")
            return {
                "content_type": "general",
                "confidence": 0.5,
                "session_id": session.conversation_id if session else None,
                "error": str(e),
            }

    async def generate_instagram_caption(
        self,
        content_description: str,
        context: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Generate only an Instagram caption with hashtags.
        
        Args:
            content_description: Description of the content
            context: Optional context (property details, etc.)
            session_id: Optional session ID
            
        Returns:
            Dictionary with caption and hashtags
        """
        context = context or {}

        # Validate with guardrails
        if self.guardrails:
            input_check = await self.guardrails.validate_input(content_description, "text")
            if not input_check["passed"]:
                return {
                    "success": False,
                    "error": input_check["message"],
                    "guardrails": {"blocked": True, "blocked_by": input_check["blocked_by"]},
                }

        try:
            caption = await self.instagram_writer.generate(content_description, context)

            # Validate output
            if self.guardrails:
                output_check = await self.guardrails.validate_output(caption)
                if not output_check["passed"]:
                    caption = "Beautiful property! Contact us for more details. 🏠\n\n#realestate #property #home #dreamhome #realtor"

            # Split caption and hashtags
            parts = caption.rsplit("\n\n", 1)
            main_caption = parts[0]
            hashtags = parts[1] if len(parts) > 1 and "#" in parts[1] else ""

            return {
                "success": True,
                "caption": main_caption,
                "hashtags": hashtags,
                "full_post": caption,
                "session_id": session_id,
                "guardrails": {"blocked": False},
            }

        except Exception as e:
            logger.error(f"Instagram caption generation error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "guardrails": {"blocked": False},
            }
