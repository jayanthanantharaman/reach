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

            # Note: Output validation removed - only user input is validated by guardrails
            # Agent-generated content is trusted and not blocked

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
        """
        Execute blog writer agent with header image generation.
        
        The BlogWriterAgent handles image generation internally using:
        1. ImagePromptAgent to analyze blog and create optimized prompt
        2. ImageGeneratorAgent to generate ONE header image (16:9)
        
        We disable image generation in the workflow to avoid duplicates.
        """
        try:
            user_input = state["user_input"]
            context = state.get("context", {})

            # Include research results if available
            if state.get("research_results"):
                context["research_results"] = state["research_results"]

            # Check if image generation should be enabled
            # Default to True, but can be disabled via context
            include_image = context.get("include_image", True)
            
            # Validate image request if image generation is enabled
            if include_image and self.guardrails:
                image_check = await self.guardrails.validate_image_request(user_input)
                if not image_check["passed"]:
                    logger.warning(f"Blog image blocked by guardrails: {image_check.get('message', 'Unknown')}")
                    include_image = False

            # Set image generation flag in context
            # The BlogWriterAgent will handle image generation internally
            context["include_image"] = include_image
            context["image_style"] = context.get("image_style", "professional")

            # Generate the blog content with image (handled by BlogWriterAgent)
            # BlogWriterAgent uses ImagePromptAgent -> ImageGeneratorAgent flow
            logger.info(f"Generating blog content for: {user_input}")
            blog_content = await self.blog_writer.generate(user_input, context)

            # Note: Output validation removed - only user input is validated by guardrails
            # Agent-generated content is trusted and not blocked
            # Note: Image generation is handled by BlogWriterAgent internally
            # No additional image generation needed here

            return {
                **state,
                "generated_content": blog_content,
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

            # Note: Output validation removed - only user input is validated by guardrails
            # Agent-generated content is trusted and not blocked

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
        """Execute Instagram post generation (image + caption)."""
        import re
        
        try:
            user_input = state["user_input"]
            context = state.get("context", {})

            # Generate both image and caption for Instagram posts
            logger.info(f"Generating Instagram post for: {user_input}")
            
            # Step 1: Generate the image
            image_data_uri = None
            try:
                # Additional image safety check
                should_generate_image = True
                if self.guardrails:
                    image_check = await self.guardrails.validate_image_request(user_input)
                    if not image_check["passed"]:
                        logger.warning(f"Image blocked by guardrails: {image_check.get('message', 'Unknown')}")
                        should_generate_image = False
                
                if should_generate_image:
                    image_result = await self.image_generator.generate(
                        f"Generate a photorealistic real estate image for Instagram: {user_input}",
                        context={"style": "professional", "aspect_ratio": "1:1"},
                    )
                    
                    # Extract the data URI from the image result
                    # The image generator returns a formatted string with "Image URL: data:image/..."
                    if image_result:
                        # Try to extract data URI from the result
                        data_uri_match = re.search(r'(data:image/[^;\s]+;base64,[A-Za-z0-9+/=]+)', str(image_result))
                        if data_uri_match:
                            image_data_uri = data_uri_match.group(1)
                        elif image_result.startswith("data:image"):
                            image_data_uri = image_result
                        else:
                            logger.info(f"Image result format: {str(image_result)[:100]}...")
                            
            except Exception as img_error:
                logger.error(f"Image generation failed: {str(img_error)}")
                # Continue without image

            # Step 2: Generate the caption with hashtags
            caption_result = await self.instagram_writer.generate(user_input, context)

            # Note: Output validation removed - only user input is validated by guardrails
            # Agent-generated content is trusted and not blocked

            # Combine image and caption into a formatted response
            if image_data_uri:
                # Format as a complete Instagram post with image
                full_content = f"""## 📸 Instagram Post

### 🖼️ Generated Image

![Instagram Image]({image_data_uri})

### 📝 Caption

{caption_result}
"""
            else:
                # Caption only (image generation failed or was blocked)
                full_content = f"""## 📸 Instagram Post

### 📝 Caption

{caption_result}

*Note: Image generation was not available for this request.*
"""

            return {
                **state,
                "generated_content": full_content,
                "content_type": "instagram",
            }
        except Exception as e:
            logger.error(f"Instagram post generation error: {str(e)}")
            return {
                **state,
                "error": f"Instagram post generation failed: {str(e)}",
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

            # Note: Output validation removed - only user input is validated by guardrails
            # Agent-generated content is trusted and not blocked

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

            # Note: Output validation removed - only user input is validated by guardrails
            # Agent-generated content is trusted and not blocked

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

            # Note: Output validation removed - only user input is validated by guardrails
            # Agent-generated content is trusted and not blocked

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
            "instagram": """You are an expert Instagram content creator specializing in real estate marketing.
Your role is to create engaging, scroll-stopping Instagram captions that:

1. CAPTURE ATTENTION: Start with a hook that makes people stop scrolling
2. TELL A STORY: Connect emotionally with the audience
3. PROVIDE VALUE: Share useful information about the property or real estate tips
4. INCLUDE CTA: End with a clear call-to-action
5. USE EMOJIS: Strategically place emojis to break up text and add visual appeal
6. ALWAYS INCLUDE HASHTAGS: Include 20-30 relevant, high-performing real estate hashtags

**CRITICAL REQUIREMENTS:**
- Caption text MUST be 150 words or less (excluding hashtags)
- ALWAYS include 20-30 hashtags at the end
- Hashtags should be separated from caption by a blank line

Keep it concise - Instagram users prefer shorter, punchier captions.""",
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

            # Note: Output validation removed - only user input is validated by guardrails
            # Agent-generated content is trusted and not blocked

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
