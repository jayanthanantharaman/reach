# 🛡️ Guardrails Decision Flow

This document describes the guardrails validation system in REACH that ensures all content is safe and on-topic.

## Overview

REACH implements two types of guardrails:
1. **Safety Guard** - Blocks profanity, offensive language, and inappropriate content
2. **Topical Guard** - Ensures requests are related to Real Estate

The guardrails run sequentially with safety checks first (fail-fast pattern).

## Guardrails Flow Diagram

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#58a6ff', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#58a6ff', 'lineColor': '#8b949e', 'secondaryColor': '#21262d', 'tertiaryColor': '#161b22', 'background': '#0d1117'}}}%%
flowchart TD
    INPUT([📥 User Input]) --> SAFETY_CHECK{🔒 Safety Check<br/>Runs First}
    
    subgraph SAFETY["Safety Guard"]
        SAFETY_CHECK -->|Check| PROFANITY{Contains<br/>Profanity?}
        PROFANITY -->|Yes| BLOCK_PROF[❌ Block]
        PROFANITY -->|No| LEETSPEAK{Check<br/>Leetspeak?}
        LEETSPEAK -->|Detected| BLOCK_PROF
        LEETSPEAK -->|Clean| INAPPROPRIATE{Inappropriate<br/>Content?}
        INAPPROPRIATE -->|Violence/Hate/Adult/Illegal| BLOCK_INAPP[❌ Block]
        INAPPROPRIATE -->|Clean| STRICT_MODE{Strict Mode<br/>+ LLM Available?}
        STRICT_MODE -->|Yes| SEMANTIC_SAFETY{🤖 LLM<br/>Semantic Check}
        SEMANTIC_SAFETY -->|Unsafe| BLOCK_SEMANTIC[❌ Block]
        SEMANTIC_SAFETY -->|Safe| PASS_SAFETY[✅ Pass Safety]
        STRICT_MODE -->|No| PASS_SAFETY
    end
    
    PASS_SAFETY --> TOPIC_CHECK{📋 Topic Check}
    
    subgraph TOPICAL["Topical Guard"]
        TOPIC_CHECK -->|Analyze| RE_KEYWORDS{Real Estate<br/>Keywords?}
        RE_KEYWORDS -->|Found| PASS_TOPIC[✅ Pass Topic]
        RE_KEYWORDS -->|Not Found| OFF_TOPIC{Off-Topic<br/>Keywords?}
        OFF_TOPIC -->|Programming/Cooking/etc| BLOCK_TOPIC[❌ Block]
        OFF_TOPIC -->|Ambiguous| CONFIDENCE{Confidence<br/>< 0.6?}
        CONFIDENCE -->|Yes + LLM| LLM_CHECK{🤖 LLM<br/>Semantic Check}
        CONFIDENCE -->|No LLM| ALLOW_DEFAULT[✅ Allow by Default]
        LLM_CHECK -->|Real Estate| PASS_TOPIC
        LLM_CHECK -->|Off-Topic| BLOCK_TOPIC
    end
    
    BLOCK_PROF --> RETURN_ERROR([Return Safety Error])
    BLOCK_INAPP --> RETURN_ERROR
    BLOCK_SEMANTIC --> RETURN_ERROR
    BLOCK_TOPIC --> RETURN_TOPIC_ERROR([Return Topic Error])
    ALLOW_DEFAULT --> CONTINUE([Continue to Router])
    PASS_TOPIC --> CONTINUE

    style INPUT fill:#58a6ff,stroke:#79c0ff,stroke-width:2px,color:#ffffff
    style SAFETY_CHECK fill:#f85149,stroke:#ff7b72,stroke-width:2px,color:#ffffff
    style PROFANITY fill:#d29922,stroke:#e3b341,stroke-width:2px,color:#ffffff
    style LEETSPEAK fill:#d29922,stroke:#e3b341,stroke-width:2px,color:#ffffff
    style INAPPROPRIATE fill:#d29922,stroke:#e3b341,stroke-width:2px,color:#ffffff
    style STRICT_MODE fill:#a371f7,stroke:#bc8cff,stroke-width:2px,color:#ffffff
    style SEMANTIC_SAFETY fill:#a371f7,stroke:#bc8cff,stroke-width:2px,color:#ffffff
    style BLOCK_PROF fill:#da3633,stroke:#f85149,stroke-width:2px,color:#ffffff
    style BLOCK_INAPP fill:#da3633,stroke:#f85149,stroke-width:2px,color:#ffffff
    style BLOCK_SEMANTIC fill:#da3633,stroke:#f85149,stroke-width:2px,color:#ffffff
    style PASS_SAFETY fill:#3fb950,stroke:#56d364,stroke-width:2px,color:#ffffff
    style TOPIC_CHECK fill:#d29922,stroke:#e3b341,stroke-width:2px,color:#ffffff
    style RE_KEYWORDS fill:#79c0ff,stroke:#a5d6ff,stroke-width:2px,color:#0d1117
    style OFF_TOPIC fill:#d29922,stroke:#e3b341,stroke-width:2px,color:#ffffff
    style CONFIDENCE fill:#a371f7,stroke:#bc8cff,stroke-width:2px,color:#ffffff
    style LLM_CHECK fill:#a371f7,stroke:#bc8cff,stroke-width:2px,color:#ffffff
    style BLOCK_TOPIC fill:#da3633,stroke:#f85149,stroke-width:2px,color:#ffffff
    style PASS_TOPIC fill:#3fb950,stroke:#56d364,stroke-width:2px,color:#ffffff
    style ALLOW_DEFAULT fill:#3fb950,stroke:#56d364,stroke-width:2px,color:#ffffff
    style RETURN_ERROR fill:#da3633,stroke:#f85149,stroke-width:2px,color:#ffffff
    style RETURN_TOPIC_ERROR fill:#da3633,stroke:#f85149,stroke-width:2px,color:#ffffff
    style CONTINUE fill:#3fb950,stroke:#56d364,stroke-width:2px,color:#ffffff
```

## Safety Guard

The Safety Guard blocks inappropriate content using multiple detection methods.

### Detection Methods

1. **Direct Profanity Matching**
   - Regex pattern matching against known profanity words
   - Case-insensitive matching

2. **Leetspeak Detection**
   - Detects obfuscated profanity (e.g., "f*ck", "sh1t")
   - Pattern-based detection for common substitutions

3. **Inappropriate Content Categories**
   - Adult content (pornography, nudity, explicit)
   - Violence (gore, torture, abuse)
   - Illegal activities (drugs, fraud, hacking)
   - Discrimination (hate speech, slurs)

4. **Semantic Analysis (Strict Mode)**
   - Uses LLM to detect disguised or contextual inappropriate content
   - Only runs if `strict_mode=True` and LLM client is available

### Blocked Response

```
I cannot help create content with profanity, offensive language, 
or inappropriate material. Please rephrase your request using 
professional and appropriate language.
```

### Image-Specific Safety

For image generation requests, additional checks are performed:

```
I cannot generate images containing inappropriate, offensive, 
violent, or explicit content. Please describe a professional 
and appropriate image for your real estate needs.
```

## Topical Guard

The Topical Guard ensures all requests are related to Real Estate.

### Real Estate Keywords (Sample)

- **Property Types**: property, house, apartment, condo, townhouse, villa, mansion
- **Actions**: buy, sell, rent, invest, mortgage, financing
- **Professionals**: realtor, agent, broker, landlord, tenant
- **Concepts**: listing, appraisal, equity, foreclosure, staging

### Off-Topic Indicators (Sample)

- **Technology**: programming, coding, cryptocurrency, video games
- **Entertainment**: movies, music, celebrities, sports
- **Other**: recipes, cooking, fashion, travel, automotive

### Topic Detection Logic

1. **Keyword Matching**
   - Count real estate keywords in input
   - Count off-topic indicators in input
   - Calculate confidence score

2. **Semantic Analysis (Low Confidence)**
   - If confidence < 0.6 and LLM available
   - LLM determines if request is real estate related

3. **Default Behavior**
   - If no clear indicators and no LLM, allow by default

### Off-Topic Response

```
Sorry! I cannot help you with that topic. My expertise is in Real Estate. 
I can help you with property listings, real estate marketing, 
home buying/selling content, property descriptions, 
and real estate social media posts.
```

## GuardrailsManager

The `GuardrailsManager` class provides a unified interface for both guards.

### Initialization

```python
guardrails = GuardrailsManager(
    llm_client=gemini_client,
    enable_topical=True,
    enable_safety=True,
    strict_mode=True,
)
```

### Validation Methods

| Method | Description |
|--------|-------------|
| `validate_input(user_input, content_type)` | Validate user input against all guards |
| `validate_output(output, content_type)` | Validate generated output (safety only) |
| `validate_image_request(prompt)` | Validate image generation prompt |

### Validation Result

```python
{
    "passed": bool,           # True if all validations passed
    "message": str | None,    # Error message if blocked
    "blocked_by": str | None, # "safety" or "topical"
    "details": {
        "safety": {...},      # Safety check details
        "topical": {...},     # Topical check details
    }
}
```

## Configuration

### Enable/Disable Guards

```python
# Disable topical guard
guardrails.disable_guardrail("topical")

# Enable safety guard
guardrails.enable_guardrail("safety")
```

### Check Status

```python
status = guardrails.get_status()
# {
#     "topical_enabled": True,
#     "safety_enabled": True,
#     "llm_client_available": True,
#     "topical_guard_active": True,
#     "safety_guard_active": True,
# }
```

## Topic Suggestions

When a request is blocked as off-topic, users can get suggestions:

```python
suggestions = guardrails.get_topic_suggestions()
# [
#     "Write a property listing description for a 3-bedroom house",
#     "Create a LinkedIn post about home buying tips",
#     "Research current real estate market trends",
#     ...
# ]
```

## Related Documentation

- [Main Workflow](./01_main_workflow.md)
- [Error Handling](./09_error_handling.md)