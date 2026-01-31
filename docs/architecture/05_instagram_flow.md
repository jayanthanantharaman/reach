# 📸 Instagram Post Generation Flow

This document describes the Instagram post generation workflow in REACH.

## Overview

REACH provides specialized methods for generating Instagram content:
- **Full Instagram Post** - Image + Caption + Hashtags (via chat or API)
- **Caption Only** - Caption + Hashtags (no image)
- **Image Only** - Via the standard image generation flow

## Key Features (v1.2)

- **Single Prompt Generation**: Type "Create an Instagram post for a luxury condo" and get both image AND caption
- **Square Images**: 1:1 aspect ratio optimized for Instagram
- **Concise Captions**: Max 150 words with 20-30 hashtags
- **Automatic Routing**: Router prioritizes Instagram keywords

## Instagram Post Generation Flow (Chat)

When a user types an Instagram-related prompt in the chat, the following flow is executed:

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#58a6ff', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#58a6ff', 'lineColor': '#8b949e', 'secondaryColor': '#21262d', 'tertiaryColor': '#161b22', 'background': '#0d1117'}}}%%
flowchart TD
    START([📸 User: "Create Instagram post for..."]) --> ROUTER{🎯 Content Router}
    
    ROUTER -->|Detects instagram/ig/insta| INSTAGRAM_NODE[📸 Instagram Node]
    
    INSTAGRAM_NODE --> GUARDRAILS{🛡️ Image Safety Check}
    
    GUARDRAILS -->|Blocked| CAPTION_ONLY[Caption Only Mode]
    GUARDRAILS -->|Passed| GEN_IMAGE[🖼️ Generate Image<br/>1:1 aspect ratio]
    
    GEN_IMAGE --> EXTRACT_URI[Extract Data URI<br/>from Image Result]
    EXTRACT_URI --> GEN_CAPTION[📝 Generate Caption<br/>via InstagramWriter]
    CAPTION_ONLY --> GEN_CAPTION
    
    GEN_CAPTION --> VALIDATE{🛡️ Validate Caption}
    
    VALIDATE -->|Safe| FORMAT[📦 Format Response]
    VALIDATE -->|Unsafe| FALLBACK[🔄 Use Fallback Caption]
    FALLBACK --> FORMAT
    
    FORMAT --> COMBINE[Combine Image + Caption<br/>as Markdown]
    
    COMBINE --> RETURN([✅ Return Complete Post])

    style START fill:#f778ba,stroke:#ff9bce,stroke-width:2px,color:#ffffff
    style ROUTER fill:#a371f7,stroke:#bc8cff,stroke-width:2px,color:#ffffff
    style INSTAGRAM_NODE fill:#f778ba,stroke:#ff9bce,stroke-width:2px,color:#ffffff
    style GUARDRAILS fill:#d29922,stroke:#e3b341,stroke-width:2px,color:#ffffff
    style CAPTION_ONLY fill:#8b949e,stroke:#b1bac4,stroke-width:2px,color:#ffffff
    style GEN_IMAGE fill:#fb8f44,stroke:#ffa657,stroke-width:2px,color:#ffffff
    style EXTRACT_URI fill:#79c0ff,stroke:#a5d6ff,stroke-width:2px,color:#0d1117
    style GEN_CAPTION fill:#3fb950,stroke:#56d364,stroke-width:2px,color:#ffffff
    style VALIDATE fill:#d29922,stroke:#e3b341,stroke-width:2px,color:#ffffff
    style FORMAT fill:#a371f7,stroke:#bc8cff,stroke-width:2px,color:#ffffff
    style FALLBACK fill:#fb8f44,stroke:#ffa657,stroke-width:2px,color:#ffffff
    style COMBINE fill:#a371f7,stroke:#bc8cff,stroke-width:2px,color:#ffffff
    style RETURN fill:#3fb950,stroke:#56d364,stroke-width:2px,color:#ffffff
```

## Instagram Node Implementation

The `_instagram_node` in `langgraph_workflow.py` handles Instagram post generation:

```python
async def _instagram_node(self, state: GraphState) -> GraphState:
    """Execute Instagram post generation (image + caption)."""
    
    # Step 1: Validate and generate image
    should_generate_image = True
    if self.guardrails:
        image_check = await self.guardrails.validate_image_request(user_input)
        if not image_check["passed"]:
            should_generate_image = False
    
    if should_generate_image:
        image_result = await self.image_generator.generate(
            f"Generate a photorealistic real estate image for Instagram: {user_input}",
            context={"style": "professional", "aspect_ratio": "1:1"},
        )
        
        # Extract data URI from result
        data_uri_match = re.search(r'(data:image/[^;\s]+;base64,[A-Za-z0-9+/=]+)', str(image_result))
        if data_uri_match:
            image_data_uri = data_uri_match.group(1)
    
    # Step 2: Generate caption with hashtags
    caption_result = await self.instagram_writer.generate(user_input, context)
    
    # Step 3: Validate caption
    if self.guardrails:
        output_check = await self.guardrails.validate_output(caption_result)
        if not output_check["passed"]:
            caption_result = "Beautiful property! Contact us for more details. 🏠\n\n#realestate #property #home"
    
    # Step 4: Format response
    if image_data_uri:
        full_content = f"""## 📸 Instagram Post

### 🖼️ Generated Image

![Instagram Image]({image_data_uri})

### 📝 Caption

{caption_result}
"""
    else:
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
```

## Content Router Priority

Instagram keywords are checked **first** in the router to ensure proper routing:

```python
# Keywords (checked first)
ContentType.INSTAGRAM: [
    "instagram", "instagram post", "instagram caption",
    "ig post", "ig caption", "insta", "insta post",
    "hashtag", "hashtags", "caption", "reel", "story",
],

# Patterns (checked first)
ContentType.INSTAGRAM: [
    r"(?:create|write|generate|make) (?:a |an )?(?:instagram|ig|insta) (?:post|caption|content)\s*.*",
    r"instagram (?:post|caption|content) (?:for|about|to)\s+.+",
    r"(?:photorealistic |photo realistic )?instagram\s+.+",
],
```

## API Methods

### generate_instagram_post (Direct API)

Generates a complete Instagram post with image and caption.

```python
async def generate_instagram_post(
    self,
    image_description: str,
    property_details: Optional[dict[str, Any]] = None,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `image_description` | `str` | Description of the property image to generate |
| `property_details` | `Optional[dict]` | Property details (location, price, features) |
| `session_id` | `Optional[str]` | Session ID for conversation continuity |

**Returns:**
```python
{
    "success": bool,
    "image": str,           # Image URL or base64 data
    "caption": str,         # Main caption text
    "hashtags": str,        # Hashtag string
    "full_post": str,       # Caption + Hashtags combined
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
    }
)
```

### generate_instagram_caption (Caption Only)

Generates only an Instagram caption with hashtags (no image).

```python
async def generate_instagram_caption(
    self,
    content_description: str,
    context: Optional[dict[str, Any]] = None,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
```

### run (Chat Interface)

Use the standard `run` method with Instagram keywords:

```python
# This automatically routes to Instagram node
result = await graph.run("Create an Instagram post for a luxury condo")
# Returns: Image + Caption with hashtags
```

## Caption Requirements

The Instagram Writer Agent follows these requirements:

1. **Max 150 words** (excluding hashtags)
2. **20-30 hashtags** at the end
3. **Emoji usage** for visual appeal
4. **Call-to-action** included
5. **Hashtags separated** by blank line

Example output:
```
✨ Welcome to your dream home! 🏠

This stunning 3-bedroom luxury condo features breathtaking city views, 
modern finishes, and an open floor plan perfect for entertaining.

📍 Prime downtown location
🛏️ 3 bedrooms, 2 bathrooms
✨ Floor-to-ceiling windows
🏊 Pool & fitness center access

Ready to make this your new home? DM us for a private showing! 💬

#realestate #luxurycondo #dreamhome #cityviews #modernliving 
#realtorlife #homesweethome #propertyforrent #luxuryliving 
#interiordesign #homegoals #apartmentliving #condoliving 
#downtownliving #realestateinvesting #househunting #newhome 
#luxuryrealestate #homeforsale #realestateagent
```

## Fallback Caption

If output validation fails, a safe fallback caption is used:

```python
{
    "caption": "Beautiful property! Contact us for more details. 🏠",
    "hashtags": "#realestate #property #home #dreamhome #realtor",
    "full_post": "Beautiful property! Contact us for more details. 🏠\n\n#realestate #property #home #dreamhome #realtor"
}
```

## Streaming Behavior

Instagram requests **do not use streaming** because they generate images:

```python
# In streamlit_app.py
is_instagram_request = any(word in prompt_lower for word in ["instagram", "ig post", "insta"])

if st.session_state.use_streaming and not is_instagram_request:
    # Use streaming
else:
    # Use non-streaming (for Instagram)
```

## Error Handling

Errors are caught and returned with appropriate messages:

```python
except Exception as e:
    logger.error(f"Instagram post generation error: {str(e)}")
    return {
        **state,
        "error": f"Instagram post generation failed: {str(e)}",
    }
```

## Related Documentation

- [Main Workflow](./01_main_workflow.md)
- [Content Router](./04_content_router.md)
- [Guardrails](./03_guardrails.md)
- [Agent Routing](./06_agent_routing.md)