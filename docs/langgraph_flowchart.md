# 🔄 REACH LangGraph Architecture Documentation

This documentation explains the decision-making process and architecture of the multi-agent system in REACH (Real Estate Automated Content Hub).

## Overview

REACH uses LangGraph to orchestrate multiple specialized agents. The workflow follows a structured decision tree that ensures:
1. All requests pass through guardrails validation
2. Requests are routed to the most appropriate agent
3. Generated content is validated before returning to the user
4. Content is streamed in real-time for better UX (text-only content)
5. Images are generated alongside content (blogs, Instagram posts)
6. All generated content is persisted to SQLite storage

## New Features (v1.2)

### 🖼️ Automatic Image Generation
- **Blog posts** now include auto-generated header images based on the blog title
- **Instagram posts** generate both image AND caption in a single request
- Images are embedded as base64 data URIs in the response

### 📸 Enhanced Instagram Flow
- Single prompt generates complete Instagram post (image + caption + hashtags)
- Captions limited to 150 words with 20-30 hashtags
- Square (1:1) aspect ratio for Instagram-optimized images

### 🎯 Improved Content Routing
- Instagram keywords prioritized in router
- Pattern matching for "instagram", "ig", "insta" keywords
- Automatic detection of content type from prompt

### 🚀 Streaming Text Generation
- Real-time text streaming via `generate_stream()` method
- ChatGPT-like typing cursor effect in UI
- Automatic fallback to non-streaming for image/blog/Instagram requests

### 📋 One-Click Copy
- Copy buttons on all generated content
- JavaScript-based clipboard integration
- Visual feedback on successful copy

### 📚 Persistent Content History
- SQLite-based storage (`content_history.db`)
- Automatically keeps last 5 items per content type
- Filter, search, and manage saved content

## Documentation Index

### Core Architecture

| Document | Description |
|----------|-------------|
| [📄 Main Workflow](./architecture/01_main_workflow.md) | Complete workflow from user request to content delivery |
| [📊 GraphState Structure](./architecture/02_graph_state.md) | State management structure and data models |
| [🛡️ Guardrails](./architecture/03_guardrails.md) | Safety and topical guardrails validation |
| [🎯 Content Router](./architecture/04_content_router.md) | Routing logic and agent selection |

### Specialized Workflows

| Document | Description |
|----------|-------------|
| [📸 Instagram Flow](./architecture/05_instagram_flow.md) | Instagram post and caption generation |
| [🤖 Agent Routing](./architecture/06_agent_routing.md) | How requests are routed to specific agents |
| [📚 Research Workflow](./architecture/08_research_workflow.md) | Research-first content creation |

### System Components

| Document | Description |
|----------|-------------|
| [📋 State Management](./architecture/07_state_management.md) | Session and conversation state management |
| [⚠️ Error Handling](./architecture/09_error_handling.md) | Error handling and recovery mechanisms |
| [📖 API Reference](./architecture/10_api_reference.md) | Complete API documentation |

## Quick Reference

### Main Workflow Diagram

```mermaid
flowchart TD
    START([🚀 User Request]) --> GUARDRAILS{🛡️ Guardrails}
    GUARDRAILS -->|Blocked| END_BLOCKED([❌ Return Error])
    GUARDRAILS -->|Passed| ROUTER{🎯 Router}
    
    ROUTER -->|research| RESEARCH[🔍 Research Agent]
    ROUTER -->|blog| BLOG[📝 Blog Writer]
    ROUTER -->|linkedin| LINKEDIN[💼 LinkedIn Writer]
    ROUTER -->|instagram| INSTAGRAM[📸 Instagram Writer]
    ROUTER -->|image| IMAGE[🖼️ Image Generator]
    ROUTER -->|strategy| STRATEGY[📊 Content Strategist]
    ROUTER -->|general| GENERAL[🤖 Query Handler]
    
    BLOG --> BLOG_IMG[🖼️ Generate Header Image]
    BLOG_IMG --> VALIDATE
    
    INSTAGRAM --> IG_IMG[🖼️ Generate Post Image]
    IG_IMG --> IG_CAPTION[📝 Generate Caption]
    IG_CAPTION --> VALIDATE
    
    RESEARCH --> VALIDATE{🛡️ Validate Output}
    LINKEDIN --> VALIDATE
    IMAGE --> VALIDATE
    STRATEGY --> VALIDATE
    GENERAL --> VALIDATE
    
    VALIDATE --> SUCCESS([✅ Return Content])

    style START fill:#e3f2fd
    style END_BLOCKED fill:#ffcdd2
    style SUCCESS fill:#c8e6c9
    style BLOG_IMG fill:#fff3e0
    style IG_IMG fill:#fff3e0
    style IG_CAPTION fill:#e8f5e9
```

### Blog Generation Flow

```mermaid
flowchart TD
    START([📝 Blog Request]) --> WRITE[Generate Blog Content]
    WRITE --> EXTRACT[Extract Title & Summary]
    EXTRACT --> CHECK{Guardrails Check}
    CHECK -->|Passed| GENERATE[Generate Header Image]
    CHECK -->|Blocked| SKIP[Skip Image]
    GENERATE --> COMBINE[Combine Image + Blog]
    SKIP --> COMBINE
    COMBINE --> RETURN([Return Complete Blog])
    
    style START fill:#e3f2fd
    style GENERATE fill:#fff3e0
    style RETURN fill:#c8e6c9
```

### Instagram Generation Flow

```mermaid
flowchart TD
    START([📸 Instagram Request]) --> CHECK{Guardrails Check}
    CHECK -->|Passed| IMAGE[Generate 1:1 Image]
    CHECK -->|Blocked| CAPTION_ONLY[Caption Only]
    IMAGE --> CAPTION[Generate Caption + Hashtags]
    CAPTION_ONLY --> CAPTION
    CAPTION --> VALIDATE{Validate Output}
    VALIDATE -->|Passed| FORMAT[Format as Instagram Post]
    VALIDATE -->|Blocked| DEFAULT[Use Default Caption]
    FORMAT --> RETURN([Return Complete Post])
    DEFAULT --> RETURN
    
    style START fill:#e3f2fd
    style IMAGE fill:#fff3e0
    style CAPTION fill:#e8f5e9
    style RETURN fill:#c8e6c9
```

### Available Agents

| Agent | Purpose | Trigger Keywords | Image Generation |
|-------|---------|------------------|------------------|
| 🔍 Research Agent | Research topics using SERP API | research, find, analyze | ❌ |
| 📝 Blog Writer | SEO-optimized blog posts | blog, article, write | ✅ Header Image (16:9) |
| 💼 LinkedIn Writer | Professional LinkedIn posts | linkedin, professional | ❌ |
| 📸 Instagram Writer | Captions with hashtags | instagram, ig, insta, caption | ✅ Post Image (1:1) |
| 🖼️ Image Generator | Property images via Imagen | image, picture, generate | ✅ Custom |
| 📊 Content Strategist | Marketing strategies | strategy, plan, campaign | ❌ |
| 🤖 Query Handler | General queries (fallback) | (default) | ❌ |

### Content Type Detection Priority

The router checks content types in this order (first match wins):

1. **Instagram** (highest priority)
   - Keywords: instagram, ig post, ig caption, insta, hashtag, caption, reel, story
   - Patterns: `create instagram post`, `instagram caption for`, `photorealistic instagram`

2. **Research**
   - Keywords: research, find, search, look up, investigate, analyze
   - Patterns: `research about`, `what is`, `tell me about`

3. **Blog**
   - Keywords: blog, article, seo, guide, tutorial, how-to
   - Patterns: `write a blog`, `blog post about`

4. **LinkedIn**
   - Keywords: linkedin, professional, b2b, corporate
   - Patterns: `linkedin post`, `professional post`

5. **Image**
   - Keywords: image, picture, photo, visual, graphic
   - Patterns: `generate image`, `create picture`

6. **Strategy**
   - Keywords: strategy, plan, campaign, marketing
   - Patterns: `content strategy`, `marketing plan`

7. **General** (fallback)
   - Default when no specific type detected

### Key Decision Points

1. **Guardrails Gate** - Safety check → Topical check
2. **Pattern Matching** - High confidence routing (0.9)
3. **Keyword Scoring** - Medium confidence routing (0.3-0.8)
4. **History Context** - Low confidence routing (0.6)
5. **Output Validation** - Ensure safe content

### Streaming vs Non-Streaming

| Content Type | Streaming | Reason |
|--------------|-----------|--------|
| Research | ✅ Yes | Text-only output |
| LinkedIn | ✅ Yes | Text-only output |
| Strategy | ✅ Yes | Text-only output |
| General | ✅ Yes | Text-only output |
| Blog | ❌ No | Generates header image |
| Instagram | ❌ No | Generates post image |
| Image | ❌ No | Image generation |

### API Quick Start

```python
from src.workflow.langgraph_workflow import REACHGraph

# Initialize
graph = REACHGraph()

# Basic usage - auto-routes to appropriate agent
result = await graph.run("Write a blog post about home staging")
# Returns: Blog content with header image

# Instagram post - generates image + caption
result = await graph.run("Create an Instagram post for a luxury condo")
# Returns: Image + caption with hashtags

# With research
result = await graph.run_with_research("market trends", content_type="blog")

# Direct Instagram post generation
result = await graph.generate_instagram_post("Modern kitchen photo")
```

## Performance Considerations

- **Sequential Validation**: Safety check runs before topical check (fail-fast)
- **Pattern Matching First**: High-confidence routing without scoring overhead
- **Caching**: Session state caches conversation history for context
- **Lazy Loading**: Agents are initialized on-demand
- **Async Operations**: All API calls are asynchronous
- **Image Generation**: Runs after text generation to avoid blocking

## File Structure

```
docs/
├── langgraph_flowchart.md          # This index file
└── architecture/
    ├── 01_main_workflow.md         # Main workflow documentation
    ├── 02_graph_state.md           # GraphState structure
    ├── 03_guardrails.md            # Guardrails documentation
    ├── 04_content_router.md        # Content router logic
    ├── 05_instagram_flow.md        # Instagram generation flow
    ├── 06_agent_routing.md         # Agent routing details
    ├── 07_state_management.md      # Session management
    ├── 08_research_workflow.md     # Research-first workflow
    ├── 09_error_handling.md        # Error handling
    └── 10_api_reference.md         # API reference
```

## Related Source Files

### Core Workflow
| File | Description |
|------|-------------|
| `src/workflow/langgraph_workflow.py` | Main workflow with blog/Instagram image generation |
| `src/workflow/state_management.py` | Session and state management |
| `src/core/router.py` | Content routing logic with Instagram priority |

### Agents
| File | Description |
|------|-------------|
| `src/agents/blog_writer.py` | Blog writer agent |
| `src/agents/instagram_writer.py` | Instagram caption writer |
| `src/agents/image_generator.py` | Image generation agent |
| `src/agents/linkedin_writer.py` | LinkedIn post writer |
| `src/agents/research_agent.py` | Research agent |
| `src/agents/content_strategist.py` | Content strategy agent |
| `src/agents/query_handler.py` | General query handler |

### Guardrails
| File | Description |
|------|-------------|
| `src/guardrails/guardrails_manager.py` | Guardrails manager |
| `src/guardrails/safety_guard.py` | Safety guardrail (profanity filter) |
| `src/guardrails/topical_guard.py` | Topical guardrail (Real Estate only) |

### Integrations
| File | Description |
|------|-------------|
| `src/integrations/gemini_client.py` | Gemini LLM client with streaming support |
| `src/integrations/imagen_client.py` | Google Imagen image generation |
| `src/integrations/serp_client.py` | SERP API for web research |

### Utilities
| File | Description |
|------|-------------|
| `src/utils/content_storage.py` | SQLite-based content history storage |
| `src/utils/content_optimization.py` | SEO and content optimization |
| `src/utils/quality_validation.py` | Content quality validation |
| `src/utils/export_tools.py` | Content export (Markdown, HTML, JSON) |

### Web Application
| File | Description |
|------|-------------|
| `src/web_app/streamlit_app.py` | Streamlit UI with chat, history, and tools tabs |