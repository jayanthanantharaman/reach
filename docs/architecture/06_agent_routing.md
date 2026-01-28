# 🤖 Agent Routing

This document describes how requests are routed to specific agents in the REACH workflow.

## Overview

After the Content Router determines the content type, the workflow's `_determine_next_node` method maps the routing decision to a specific agent node.

## Agent Routing Flow

```mermaid
flowchart TD
    ROUTE_DECISION[RoutingDecision] --> DETERMINE{_determine_next_node}
    
    DETERMINE -->|error in state| END_NODE[END]
    DETERMINE -->|no route_decision| GENERAL_NODE[general]
    
    DETERMINE -->|"research" in agent_type| RESEARCH_NODE[research]
    DETERMINE -->|"blog" in agent_type| BLOG_NODE[blog]
    DETERMINE -->|"linkedin" in agent_type| LINKEDIN_NODE[linkedin]
    DETERMINE -->|"instagram" or "caption" in agent_type| INSTAGRAM_NODE[instagram]
    DETERMINE -->|"image" in agent_type| IMAGE_NODE[image]
    DETERMINE -->|"strateg" in agent_type| STRATEGY_NODE[strategy]
    DETERMINE -->|default| GENERAL_NODE
    
    RESEARCH_NODE --> RESEARCH_AGENT[🔍 ResearchAgent]
    BLOG_NODE --> BLOG_AGENT[📝 BlogWriterAgent]
    LINKEDIN_NODE --> LINKEDIN_AGENT[💼 LinkedInWriterAgent]
    INSTAGRAM_NODE --> INSTAGRAM_AGENT[📸 InstagramWriterAgent]
    IMAGE_NODE --> IMAGE_AGENT[🖼️ ImageGeneratorAgent]
    STRATEGY_NODE --> STRATEGY_AGENT[📊 ContentStrategistAgent]
    GENERAL_NODE --> QUERY_AGENT[🤖 QueryHandlerAgent]

    style DETERMINE fill:#fff3e0
    style RESEARCH_AGENT fill:#e8f5e9
    style BLOG_AGENT fill:#e8f5e9
    style LINKEDIN_AGENT fill:#e8f5e9
    style INSTAGRAM_AGENT fill:#e8f5e9
    style IMAGE_AGENT fill:#e8f5e9
    style STRATEGY_AGENT fill:#e8f5e9
    style QUERY_AGENT fill:#fff3e0
```

## _determine_next_node Implementation

```python
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

    agent_type = route.agent_type.lower()

    if "research" in agent_type:
        return "research"
    elif "blog" in agent_type:
        return "blog"
    elif "linkedin" in agent_type:
        return "linkedin"
    elif "instagram" in agent_type or "caption" in agent_type:
        return "instagram"
    elif "image" in agent_type:
        return "image"
    elif "strateg" in agent_type:
        return "strategy"
    else:
        return "general"
```

## Available Agents

### 🔍 Research Agent

**Purpose:** Research topics using SERP API and synthesize findings.

**Initialization:**
```python
self.research_agent = ResearchAgent(
    llm_client=self.gemini_client,
    serp_client=self.serp_client,
)
```

**Node Implementation:**
```python
async def _research_node(self, state: GraphState) -> GraphState:
    result = await self.research_agent.generate(user_input, context)
    return {
        **state,
        "generated_content": result,
        "content_type": "research",
        "research_results": {"summary": result},
    }
```

### 📝 Blog Writer Agent

**Purpose:** Write SEO-optimized blog posts with optional images.

**Initialization:**
```python
self.blog_writer = BlogWriterAgent(
    llm_client=self.gemini_client,
    image_client=self.imagen_client,  # For inline images
)
```

**Node Implementation:**
```python
async def _blog_node(self, state: GraphState) -> GraphState:
    # Include research results if available
    if state.get("research_results"):
        context["research_results"] = state["research_results"]
    
    result = await self.blog_writer.generate(user_input, context)
    return {
        **state,
        "generated_content": result,
        "content_type": "blog",
    }
```

### 💼 LinkedIn Writer Agent

**Purpose:** Create professional LinkedIn posts.

**Initialization:**
```python
self.linkedin_writer = LinkedInWriterAgent(llm_client=self.gemini_client)
```

**Node Implementation:**
```python
async def _linkedin_node(self, state: GraphState) -> GraphState:
    result = await self.linkedin_writer.generate(user_input, context)
    return {
        **state,
        "generated_content": result,
        "content_type": "linkedin",
    }
```

### 📸 Instagram Writer Agent

**Purpose:** Generate Instagram captions with hashtags.

**Initialization:**
```python
self.instagram_writer = InstagramWriterAgent(llm_client=self.gemini_client)
```

**Node Implementation:**
```python
async def _instagram_node(self, state: GraphState) -> GraphState:
    result = await self.instagram_writer.generate(user_input, context)
    return {
        **state,
        "generated_content": result,
        "content_type": "instagram",
    }
```

### 🖼️ Image Generator Agent

**Purpose:** Generate property images using Imagen.

**Initialization:**
```python
self.image_generator = ImageGeneratorAgent(
    llm_client=self.gemini_client,
    image_client=self.imagen_client,
)
```

**Node Implementation:**
```python
async def _image_node(self, state: GraphState) -> GraphState:
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
```

### 📊 Content Strategist Agent

**Purpose:** Create content strategies and marketing plans.

**Initialization:**
```python
self.content_strategist = ContentStrategistAgent(llm_client=self.gemini_client)
```

**Node Implementation:**
```python
async def _strategy_node(self, state: GraphState) -> GraphState:
    result = await self.content_strategist.generate(user_input, context)
    return {
        **state,
        "generated_content": result,
        "content_type": "strategy",
    }
```

### 🤖 Query Handler Agent

**Purpose:** Handle general queries and fallback requests.

**Initialization:**
```python
self.query_handler = QueryHandlerAgent(llm_client=self.gemini_client)
```

**Node Implementation:**
```python
async def _general_node(self, state: GraphState) -> GraphState:
    result = await self.query_handler.generate(user_input, context)
    return {
        **state,
        "generated_content": result,
        "content_type": "general",
    }
```

## Output Validation

All agent nodes (except image) validate output against safety guardrails:

```python
# Validate output
if self.guardrails:
    output_check = await self.guardrails.validate_output(result)
    if not output_check["passed"]:
        result = "I apologize, but I cannot provide that response. Please try a different query."
```

## Graph Node Configuration

The LangGraph workflow is configured with conditional edges:

```python
def _build_graph(self) -> StateGraph:
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

    # Set entry point
    workflow.set_entry_point("guardrails")

    # Conditional edges from guardrails
    workflow.add_conditional_edges(
        "guardrails",
        self._check_guardrails_passed,
        {"passed": "route", "blocked": END},
    )

    # Conditional edges from route
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

    # All content nodes go to END
    workflow.add_edge("research", END)
    workflow.add_edge("blog", END)
    workflow.add_edge("linkedin", END)
    workflow.add_edge("instagram", END)
    workflow.add_edge("image", END)
    workflow.add_edge("strategy", END)
    workflow.add_edge("general", END)

    return workflow.compile()
```

## Agent Initialization

All agents are initialized in `_init_agents()`:

```python
def _init_agents(self) -> None:
    """Initialize all agents."""
    self.query_handler = QueryHandlerAgent(llm_client=self.gemini_client)
    self.research_agent = ResearchAgent(
        llm_client=self.gemini_client,
        serp_client=self.serp_client,
    )
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
```

## Related Documentation

- [Main Workflow](./01_main_workflow.md)
- [Content Router](./04_content_router.md)
- [GraphState Structure](./02_graph_state.md)