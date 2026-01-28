# 📖 API Reference

This document provides a complete API reference for the REACH LangGraph workflow.

## REACHGraph Class

The main class for the REACH workflow.

### Constructor

```python
class REACHGraph:
    def __init__(
        self,
        gemini_client: Optional[GeminiClient] = None,
        imagen_client: Optional[ImagenClient] = None,
        serp_client: Optional[SerpClient] = None,
        enable_guardrails: bool = True,
    ):
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `gemini_client` | `Optional[GeminiClient]` | `None` | Gemini LLM client (auto-created if None) |
| `imagen_client` | `Optional[ImagenClient]` | `None` | Imagen client for image generation |
| `serp_client` | `Optional[SerpClient]` | `None` | SERP API client for research |
| `enable_guardrails` | `bool` | `True` | Enable topical and safety guardrails |

**Example:**
```python
from src.workflow.langgraph_workflow import REACHGraph

# Default initialization
graph = REACHGraph()

# Custom initialization
graph = REACHGraph(
    gemini_client=my_gemini_client,
    imagen_client=my_imagen_client,
    serp_client=my_serp_client,
    enable_guardrails=True,
)
```

---

## Core Methods

### run

Main workflow execution method.

```python
async def run(
    self,
    user_input: str,
    session_id: Optional[str] = None,
    context: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `user_input` | `str` | Required | User's request |
| `session_id` | `Optional[str]` | `None` | Session ID for conversation continuity |
| `context` | `Optional[dict]` | `None` | Additional context data |

**Returns:**
```python
{
    "success": bool,
    "content": str,
    "content_type": str | None,
    "route": RoutingDecision | None,
    "error": str | None,
    "session_id": str,
    "guardrails": {
        "blocked": bool,
        "blocked_by": str | None
    }
}
```

**Example:**
```python
result = await graph.run(
    user_input="Write a blog post about home staging tips",
    session_id="user-123",
    context={"property_type": "residential"}
)

if result["success"]:
    print(result["content"])
else:
    print(f"Error: {result['error']}")
```

---

### run_with_research

Research-first workflow execution.

```python
async def run_with_research(
    self,
    topic: str,
    content_type: str = "blog",
    session_id: Optional[str] = None,
) -> dict[str, Any]:
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `topic` | `str` | Required | Topic to research and create content about |
| `content_type` | `str` | `"blog"` | Type of content ("blog", "linkedin", "strategy") |
| `session_id` | `Optional[str]` | `None` | Session ID |

**Returns:**
```python
{
    "success": bool,
    "research": str,
    "content": str,
    "content_type": str,
    "session_id": str,
    "error": str | None,
    "guardrails": {
        "blocked": bool,
        "blocked_by": str | None
    }
}
```

**Example:**
```python
result = await graph.run_with_research(
    topic="2024 real estate market trends",
    content_type="blog",
    session_id="user-123"
)

print(f"Research: {result['research']}")
print(f"Content: {result['content']}")
```

---

## Instagram Methods

### generate_instagram_post

Generate a complete Instagram post with image and caption.

```python
async def generate_instagram_post(
    self,
    image_description: str,
    property_details: Optional[dict[str, Any]] = None,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `image_description` | `str` | Required | Description of the property image |
| `property_details` | `Optional[dict]` | `None` | Property details (location, price, features) |
| `session_id` | `Optional[str]` | `None` | Session ID |

**Returns:**
```python
{
    "success": bool,
    "image": str,
    "caption": str,
    "hashtags": str,
    "full_post": str,
    "session_id": str,
    "guardrails": {
        "blocked": bool,
        "blocked_by": str | None
    }
}
```

**Example:**
```python
result = await graph.generate_instagram_post(
    image_description="Modern kitchen with granite countertops",
    property_details={
        "location": "San Francisco, CA",
        "price": "$1,200,000",
        "bedrooms": 3
    }
)

print(f"Image: {result['image']}")
print(f"Caption: {result['full_post']}")
```

---

### generate_instagram_caption

Generate only an Instagram caption with hashtags.

```python
async def generate_instagram_caption(
    self,
    content_description: str,
    context: Optional[dict[str, Any]] = None,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
```

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `content_description` | `str` | Required | Description of the content |
| `context` | `Optional[dict]` | `None` | Additional context |
| `session_id` | `Optional[str]` | `None` | Session ID |

**Returns:**
```python
{
    "success": bool,
    "caption": str,
    "hashtags": str,
    "full_post": str,
    "session_id": str,
    "guardrails": {
        "blocked": bool,
        "blocked_by": str | None
    }
}
```

**Example:**
```python
result = await graph.generate_instagram_caption(
    content_description="Just sold this beautiful 3-bedroom home",
    context={"sale_type": "just_sold"}
)

print(result["full_post"])
```

---

## Session Management Methods

### get_session

Get a session by ID.

```python
def get_session(self, session_id: str) -> Optional[ConversationState]:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | `str` | Session ID to retrieve |

**Returns:** `ConversationState` or `None`

**Example:**
```python
session = graph.get_session("user-123")
if session:
    history = session.get_history()
    print(f"Messages: {len(history)}")
```

---

### clear_session

Clear a session's history.

```python
def clear_session(self, session_id: str) -> bool:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | `str` | Session ID to clear |

**Returns:** `bool` - True if cleared, False if not found

**Example:**
```python
success = graph.clear_session("user-123")
print(f"Session cleared: {success}")
```

---

### delete_session

Delete a session.

```python
def delete_session(self, session_id: str) -> bool:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | `str` | Session ID to delete |

**Returns:** `bool` - True if deleted, False if not found

**Example:**
```python
success = graph.delete_session("user-123")
print(f"Session deleted: {success}")
```

---

## Guardrails Methods

### get_guardrails_status

Get the current guardrails status.

```python
def get_guardrails_status(self) -> dict[str, Any]:
```

**Returns:**
```python
{
    "topical_enabled": bool,
    "safety_enabled": bool,
    "llm_client_available": bool,
    "topical_guard_active": bool,
    "safety_guard_active": bool
}
```

**Example:**
```python
status = graph.get_guardrails_status()
print(f"Safety enabled: {status['safety_enabled']}")
```

---

### get_topic_suggestions

Get suggestions for on-topic requests.

```python
def get_topic_suggestions(self) -> list[str]:
```

**Returns:** List of example real estate topics

**Example:**
```python
suggestions = graph.get_topic_suggestions()
for suggestion in suggestions:
    print(f"- {suggestion}")
```

---

## API Methods Summary Table

| Method | Description | Returns |
|--------|-------------|---------|
| `run(user_input, session_id, context)` | Main workflow execution | `{success, content, content_type, route, error, session_id, guardrails}` |
| `run_with_research(topic, content_type, session_id)` | Research-first workflow | `{success, research, content, content_type, session_id, error, guardrails}` |
| `generate_instagram_post(image_description, property_details, session_id)` | Full Instagram post | `{success, image, caption, hashtags, full_post, session_id, guardrails}` |
| `generate_instagram_caption(content_description, context, session_id)` | Caption only | `{success, caption, hashtags, full_post, session_id, guardrails}` |
| `get_session(session_id)` | Get session by ID | `ConversationState` or `None` |
| `clear_session(session_id)` | Clear session history | `bool` |
| `delete_session(session_id)` | Delete session | `bool` |
| `get_guardrails_status()` | Get guardrails status | `{topical_enabled, safety_enabled, ...}` |
| `get_topic_suggestions()` | Get on-topic suggestions | `list[str]` |

---

## Data Models

### RoutingDecision

```python
class RoutingDecision(BaseModel):
    content_type: ContentType
    confidence: float  # 0.0 to 1.0
    reasoning: str
    requires_research: bool
    follow_up_types: list[ContentType]
```

### ContentType

```python
class ContentType(str, Enum):
    RESEARCH = "research"
    BLOG = "blog"
    LINKEDIN = "linkedin"
    IMAGE = "image"
    STRATEGY = "strategy"
    GENERAL = "general"
```

### GraphState

```python
class GraphState(TypedDict):
    user_input: str
    route_decision: Optional[RoutingDecision]
    research_results: Optional[dict[str, Any]]
    generated_content: Optional[str]
    content_type: Optional[str]
    error: Optional[str]
    conversation_history: list[dict[str, str]]
    context: dict[str, Any]
    guardrails_result: Optional[dict[str, Any]]
```

### ConversationState

```python
@dataclass
class ConversationState:
    conversation_id: str
    messages: list[Message]
    context: dict[str, Any]
    current_agent: Optional[str]
    generated_content: dict[str, Any]
    created_at: datetime
    updated_at: datetime
```

### Message

```python
@dataclass
class Message:
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    metadata: dict[str, Any]
```

---

## Error Codes

| Error Type | blocked_by | Description |
|------------|------------|-------------|
| Safety Block | `"safety"` | Content contains profanity or inappropriate material |
| Topical Block | `"topical"` | Content is not related to real estate |
| Image Safety | `"image_safety"` | Image prompt contains inappropriate content |
| Agent Error | `None` | Agent execution failed |
| Routing Error | `None` | Routing failed |
| Workflow Error | `None` | General workflow error |

---

## Related Documentation

- [Main Workflow](./01_main_workflow.md)
- [GraphState Structure](./02_graph_state.md)
- [State Management](./07_state_management.md)