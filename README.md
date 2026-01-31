# 🏠 REACH - Real Estate Automated Content Hub

**AI-Powered Multi-Agent Content Creation System for Real Estate**

REACH is a sophisticated multi-agent system built with LangGraph that transforms your real estate content creation workflow. It leverages specialized AI agents to research topics, write SEO-optimized blogs, create engaging LinkedIn posts, generate images, and develop comprehensive content strategies - all focused exclusively on the real estate industry.

## 🌟 Features

### Content Generation
- **🔍 Deep Research Agent**: Conducts comprehensive web research using SERP API
- **📝 SEO Blog Writer**: Creates search-optimized long-form real estate content with auto-generated featured images
- **💼 LinkedIn Post Writer**: Generates engaging professional social content for realtors
- **📸 Instagram Caption Writer**: Creates engaging captions with relevant hashtags for property posts
- **🖼️ Image Generation**: Produces custom property visuals with Google Imagen
- **📊 Content Strategist**: Develops real estate marketing plans and content calendars
- **🎨 Instagram Post Generator**: Combined image + caption generation for complete Instagram posts

### User Experience
- **🚀 Streaming Text Generation**: Real-time text streaming for a ChatGPT-like experience
- **📋 One-Click Copy**: Copy buttons on all generated content for easy clipboard access
- **📚 Content History**: SQLite-based persistent storage of last 5 items per content type
- **🤖 Intelligent Routing**: Automatically routes requests to the right agent

### Safety & Quality
- **🛡️ NeMo Guardrails**: Topical (Real Estate only) and Safety (profanity blocking) guardrails
- **📊 Quality Validation**: Automatic content quality scoring and analysis
- **🔍 SEO Analysis**: Built-in SEO scoring for blog content

## 🏗️ Architecture

### System Architecture Diagram

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#58a6ff', 'primaryTextColor': '#ffffff', 'primaryBorderColor': '#58a6ff', 'lineColor': '#8b949e', 'secondaryColor': '#21262d', 'tertiaryColor': '#161b22', 'background': '#0d1117'}}}%%
graph TB
    subgraph UI_LAYER["🖥️ User Interface"]
        UI[Streamlit Web App]
        STREAM[🚀 Streaming Display]
        COPY[📋 Copy Buttons]
    end

    subgraph ORCH_LAYER["🔄 Orchestration Layer"]
        WF[LangGraph Workflow]
        SM[📊 Session Manager]
        RT[🎯 Content Router]
    end

    subgraph STORAGE_LAYER["💾 Storage Layer"]
        CS[📚 Content Storage<br/>SQLite]
    end

    subgraph GUARD_LAYER["🛡️ Guardrails Layer"]
        GR[Guardrails Manager]
        TG[📋 Topical Guard<br/>Real Estate Only]
        SG[🔒 Safety Guard<br/>Profanity Blocking]
    end

    subgraph AGENT_LAYER["🤖 Agent Layer"]
        QH[Query Handler]
        RA[🔍 Research Agent]
        BW[📝 Blog Writer]
        LW[💼 LinkedIn Writer]
        IW[📸 Instagram Writer]
        IG[🖼️ Image Generator]
        CST[📊 Content Strategist]
    end

    subgraph INT_LAYER["🔌 Integration Layer"]
        GC[🧠 Gemini Client<br/>+ Streaming]
        IC[🎨 Imagen Client]
        SC[🔎 SERP Client]
    end

    subgraph EXT_LAYER["☁️ External Services"]
        GEMINI[Google Gemini API]
        IMAGEN[Google Imagen API]
        SERP[SERP API]
    end

    UI --> WF
    UI --> STREAM
    UI --> COPY
    WF --> SM
    WF --> RT
    WF --> GR
    WF --> CS
    
    GR --> TG
    GR --> SG
    
    RT --> QH
    RT --> RA
    RT --> BW
    RT --> LW
    RT --> IW
    RT --> IG
    RT --> CST
    
    QH --> GC
    RA --> GC
    RA --> SC
    BW --> GC
    LW --> GC
    IW --> GC
    IG --> GC
    IG --> IC
    CST --> GC
    
    GC --> GEMINI
    IC --> IMAGEN
    SC --> SERP

    style UI fill:#58a6ff,stroke:#79c0ff,stroke-width:2px,color:#ffffff
    style STREAM fill:#58a6ff,stroke:#79c0ff,stroke-width:2px,color:#ffffff
    style COPY fill:#58a6ff,stroke:#79c0ff,stroke-width:2px,color:#ffffff
    style CS fill:#e3b341,stroke:#f0d75e,stroke-width:2px,color:#0d1117
    style WF fill:#fb8f44,stroke:#ffa657,stroke-width:2px,color:#ffffff
    style SM fill:#8b949e,stroke:#b1bac4,stroke-width:2px,color:#ffffff
    style RT fill:#a371f7,stroke:#bc8cff,stroke-width:2px,color:#ffffff
    style GR fill:#f85149,stroke:#ff7b72,stroke-width:2px,color:#ffffff
    style TG fill:#da3633,stroke:#f85149,stroke-width:2px,color:#ffffff
    style SG fill:#da3633,stroke:#f85149,stroke-width:2px,color:#ffffff
    style QH fill:#39d353,stroke:#56d364,stroke-width:2px,color:#ffffff
    style RA fill:#39d353,stroke:#56d364,stroke-width:2px,color:#ffffff
    style BW fill:#39d353,stroke:#56d364,stroke-width:2px,color:#ffffff
    style LW fill:#39d353,stroke:#56d364,stroke-width:2px,color:#ffffff
    style IW fill:#f778ba,stroke:#ff9bce,stroke-width:2px,color:#ffffff
    style IG fill:#39d353,stroke:#56d364,stroke-width:2px,color:#ffffff
    style CST fill:#39d353,stroke:#56d364,stroke-width:2px,color:#ffffff
    style GC fill:#3fb950,stroke:#56d364,stroke-width:2px,color:#ffffff
    style IC fill:#3fb950,stroke:#56d364,stroke-width:2px,color:#ffffff
    style SC fill:#3fb950,stroke:#56d364,stroke-width:2px,color:#ffffff
    style GEMINI fill:#238636,stroke:#3fb950,stroke-width:2px,color:#ffffff
    style IMAGEN fill:#238636,stroke:#3fb950,stroke-width:2px,color:#ffffff
    style SERP fill:#238636,stroke:#3fb950,stroke-width:2px,color:#ffffff
```

### Component Overview

| Layer | Component | Description |
|-------|-----------|-------------|
| **UI** | Streamlit App | Interactive web interface with chat, dashboard, history, and tools |
| **UI** | Streaming Display | Real-time text streaming with typing cursor effect |
| **UI** | Copy Buttons | One-click clipboard copy for all generated content |
| **Storage** | Content Storage | SQLite-based persistent storage (last 5 items per type) |
| **Orchestration** | LangGraph Workflow | Multi-agent orchestration with state management |
| **Orchestration** | Content Router | Intelligent routing based on user intent |
| **Guardrails** | Topical Guard | Restricts content to Real Estate topics |
| **Guardrails** | Safety Guard | Blocks profanity and inappropriate content |
| **Agents** | 7 Specialized Agents | Query, Research, Blog, LinkedIn, Instagram, Image, Strategy |
| **Integration** | Gemini Client | LLM with streaming support via google-genai |
| **Integration** | Imagen Client | Image generation via google-genai |
| **Integration** | SERP Client | Web research via SERP API |

### Data Flow

```mermaid
sequenceDiagram
    participant U as User
    participant UI as Streamlit
    participant WF as LangGraph
    participant GR as Guardrails
    participant RT as Router
    participant AG as Agent
    participant API as External API

    U->>UI: Enter request
    UI->>WF: Submit to workflow
    WF->>GR: Validate input
    
    alt Guardrails Blocked
        GR-->>WF: Blocked (off-topic/unsafe)
        WF-->>UI: Return error message
        UI-->>U: Display blocked message
    else Guardrails Passed
        GR-->>WF: Passed
        WF->>RT: Route request
        RT->>AG: Select appropriate agent
        AG->>API: Call external service
        API-->>AG: Return response
        AG->>GR: Validate output
        GR-->>AG: Output validated
        AG-->>WF: Return content
        WF-->>UI: Return result
        UI-->>U: Display content
    end
```

> 📖 **For detailed flowcharts** of the LangGraph agent decision-making process, see [docs/langgraph_flowchart.md](docs/langgraph_flowchart.md)

### 📊 Viewing the Diagrams

The architecture diagrams use **Mermaid** syntax. Here's how to view them:

#### Option 1: GitHub (Automatic)
GitHub automatically renders Mermaid diagrams in Markdown files. Simply view the README.md or flowchart files on GitHub.

#### Option 2: VS Code Extension
Install the [Markdown Preview Mermaid Support](https://marketplace.visualstudio.com/items?itemName=bierner.markdown-mermaid) extension:
```bash
code --install-extension bierner.markdown-mermaid
```
Then use `Cmd+Shift+V` (Mac) or `Ctrl+Shift+V` (Windows/Linux) to preview.

#### Option 3: Mermaid Live Editor
Copy the Mermaid code blocks to [Mermaid Live Editor](https://mermaid.live/) for interactive viewing and editing.

#### Option 4: Generate PNG/SVG Images
Use the Mermaid CLI to generate static images:
```bash
# Install Mermaid CLI
npm install -g @mermaid-js/mermaid-cli

# Generate PNG from the flowchart
mmdc -i docs/langgraph_flowchart.md -o docs/flowchart.png

# Generate SVG
mmdc -i docs/langgraph_flowchart.md -o docs/flowchart.svg -f svg
```

#### Option 5: Jupyter Notebook
If using Jupyter, install the mermaid extension:
```bash
pip install jupyterlab-mermaid
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- API Keys for:
  - Google Gemini (for LLM and Imagen image generation)
  - SERP API (for web research)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd reach
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

5. **Run the application**
   ```bash
   streamlit run src/web_app/streamlit_app.py
   ```

## 📖 Usage

### Web Interface

The Streamlit web interface provides three main tabs:

1. **💬 Chat**: Conversational interface with intelligent routing - all content generation happens here
2. **📚 History**: Browse persistent content history (last 5 items per type)
3. **🛠️ Tools**: SEO analyzer, quality checker, export tools, and Instagram generator form

**Note:** All content generation (blogs, LinkedIn posts, Instagram posts, images, research, strategy) is handled through the Chat interface. The router automatically detects your intent and routes to the appropriate agent.

### Streaming Text Generation

REACH features real-time text streaming for a ChatGPT-like experience:

- **Live Text Display**: Watch content appear character-by-character
- **Typing Cursor**: Visual cursor indicator (▌) during generation
- **Toggle Control**: Enable/disable streaming in sidebar settings
- **Smart Detection**: Automatically uses non-streaming for image requests

### Copy Buttons

Every generated content item includes a one-click copy button:

- **Chat Messages**: Copy button appears next to each assistant response
- **History Tab**: Copy, download, or delete any saved content
- **Instant Feedback**: Button shows "✅ Copied!" confirmation

### Content History

The History tab provides persistent storage across sessions:

- **Automatic Saving**: All generated content is saved to SQLite
- **Last 5 Per Type**: Keeps the 5 most recent items for each content type
- **Filter & Search**: Filter by content type (blog, linkedin, instagram, etc.)
- **Management**: Delete individual items or clear by type
- **Statistics**: View total items, content types, and latest entry

### Intelligent Content Routing

REACH automatically detects your intent and routes to the appropriate agent. Just type naturally in the chat:

| Content Type | Trigger Keywords | What You Get |
|--------------|------------------|--------------|
| **📝 Blog** | blog, article, write, guide | SEO-optimized blog post + header image (16:9) |
| **💼 LinkedIn** | linkedin, professional, b2b | Professional LinkedIn post |
| **📸 Instagram** | instagram, ig, insta, caption | Image (1:1) + caption with 20-30 hashtags |
| **🔍 Research** | research, find, analyze, what is | Comprehensive research summary |
| **🖼️ Image** | image, picture, photo, generate | Custom property image |
| **📊 Strategy** | strategy, plan, campaign | Content marketing strategy |

### Example Prompts

```
# Research
"Research the latest trends in luxury real estate"

# Blog Post
"Write a blog post about first-time home buyer tips"

# LinkedIn Post
"Create a LinkedIn post about home staging secrets"

# Instagram Caption
"Create an Instagram caption for a luxury home listing"

# Image Generation
"Generate an image for a luxury condo listing"

# Content Strategy
"Create a content strategy for a real estate agency"
```

### Programmatic Usage

```python
import asyncio
from src.workflow import REACHGraph

# Initialize the graph
graph = REACHGraph()

# Run a content creation request
async def create_content():
    result = await graph.run(
        "Write a blog post about home buying tips",
        session_id="my-session"
    )
    print(result["content"])

asyncio.run(create_content())
```

## 🔧 Configuration

### Environment Variables

All configuration is centralized through environment variables. Copy `.env.example` to `.env` and configure your settings.

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `GOOGLE_API_KEY` | Google API key for Gemini LLM and Imagen | Yes | - |
| `SERP_API_KEY` | SERP API key for research | Yes | - |
| `GEMINI_MODEL` | Gemini model name | No | gemini-1.5-pro |
| `GEMINI_TEMPERATURE` | Temperature for LLM responses | No | 0.7 |
| `GEMINI_MAX_TOKENS` | Maximum tokens for responses | No | 8192 |
| `IMAGEN_MODEL` | Imagen model name | No | imagen-3.0-generate-002 |
| `DEBUG` | Enable debug mode | No | false |
| `LOG_LEVEL` | Logging level | No | INFO |
| `MAX_BLOG_LENGTH` | Maximum blog post length (words) | No | 2000 |
| `MAX_LINKEDIN_LENGTH` | Maximum LinkedIn post length (chars) | No | 3000 |
| `RATE_LIMIT_REQUESTS` | Max requests per minute | No | 60 |
| `RATE_LIMIT_TOKENS` | Max tokens per minute | No | 100000 |
| `MIN_QUALITY_SCORE` | Minimum quality score for content | No | 0.7 |

### Centralized Configuration

All agents automatically inherit settings from the centralized configuration. This means:

- **Model settings** (model name, temperature, max tokens) are configured once in `.env`
- **All agents** use these defaults automatically
- **Individual calls** can still override settings when needed

```python
# Settings are automatically loaded from .env
from src.core.config import get_settings

settings = get_settings()
print(settings.gemini_model)       # gemini-1.5-pro
print(settings.gemini_temperature) # 0.7
print(settings.gemini_max_tokens)  # 8192
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_agents.py
```

## 📊 Content Quality Features

### SEO Optimization
- Keyword density analysis
- Readability scoring (Flesch Reading Ease)
- Structure analysis (headings, lists, links)
- Meta description recommendations

### Quality Validation
- Length validation
- Structure checking
- Completeness verification
- Brand voice consistency

### Export Options
- Markdown with frontmatter
- HTML with styling
- JSON for API integration
- Platform-specific formats (WordPress, LinkedIn)

## 🛠️ Development

### Code Style

```bash
# Format code
black src/

# Lint code
ruff check src/

# Type checking
mypy src/
```

### Project Structure Guidelines

- Each agent inherits from `BaseAgent`
- All async operations use `asyncio`
- Configuration via Pydantic settings
- State management through `SessionManager`

## 📚 API Documentation

### Agents

| Agent | Purpose | Key Methods |
|-------|---------|-------------|
| `QueryHandlerAgent` | Routes and handles queries | `generate()`, `classify_intent()` |
| `ResearchAgent` | Web research | `generate()`, `research()` |
| `BlogWriterAgent` | SEO blog writing with images | `generate()`, `generate_with_image()`, `generate_outline()` |
| `LinkedInWriterAgent` | LinkedIn posts | `generate()`, `generate_variations()` |
| `ImageGeneratorAgent` | Image creation with Imagen | `generate()`, `optimize_prompt()` |
| `ImagePromptAgent` | Creates optimized image prompts from content | `generate()`, `generate_from_blog()`, `generate_from_summary()` |
| `InstagramWriterAgent` | Instagram captions with hashtags | `generate()`, `generate_for_image()`, `generate_variations()` |
| `ContentStrategistAgent` | Strategy planning | `generate()`, `create_content_calendar()` |

### Workflow

```python
from src.workflow import REACHGraph

graph = REACHGraph()

# Simple run
result = await graph.run("Your request")

# Research-first workflow
result = await graph.run_with_research(
    topic="Real Estate Market Trends",
    content_type="blog"
)

# Generate complete Instagram post (image + caption)
result = await graph.generate_instagram_post(
    image_description="Modern luxury home with pool",
    property_details={
        "property_type": "House",
        "location": "Austin, TX",
        "price": "$1,200,000",
        "features": ["4 bedrooms", "pool", "smart home"]
    }
)

# Generate only Instagram caption
result = await graph.generate_instagram_caption(
    content_description="Stunning waterfront property",
    context={"location": "Miami, FL"}
)
```

## 📝 Blog Post Generation with Images

The Blog Writer Agent now automatically generates a relevant featured image for each blog post using a two-step process with the **ImagePromptAgent**.

### Image Generation Flow

```
1. BlogWriterAgent → Generates full blog content
2. ImagePromptAgent → Analyzes blog, extracts title/summary/themes
3. ImagePromptAgent → Creates optimized image prompt
4. ImageGeneratorAgent → Generates ONE header image (16:9)
5. Image inserted into blog content
```

### Features

- **Automatic Image Generation**: Each blog post includes a relevant header image
- **Smart Image Prompts**: Uses `ImagePromptAgent` to analyze blog and create optimized prompts
- **Single Image**: Only ONE image is generated per blog (no duplicates)
- **16:9 Aspect Ratio**: Blog header images are generated in wide landscape format
- **Configurable**: Enable/disable image generation via context parameters
- **Separate Image Access**: Use `generate_with_image()` to get blog and image data separately

### Example Usage

```python
from src.agents import BlogWriterAgent

# Initialize with image client
blog_writer = BlogWriterAgent(
    llm_client=gemini_client,
    image_client=imagen_client,
)

# Generate blog with image (default behavior)
result = await blog_writer.generate(
    "Write a blog post about home staging tips",
    context={
        "include_image": True,  # Default is True
        "image_style": "professional",
    }
)

# Generate blog and image separately
result = await blog_writer.generate_with_image(
    "Write a blog post about luxury real estate trends",
    context={"image_style": "luxury"}
)

print(result["blog_content"])  # Full blog post
print(result["image_data"])    # Generated image
print(result["image_prompt"])  # Prompt used for image
print(result["title"])         # Extracted blog title
```

### Disabling Image Generation

To generate a blog without an image:

```python
result = await blog_writer.generate(
    "Write a blog post about mortgage rates",
    context={"include_image": False}
)
```

### Image Styles

The blog writer supports these image styles:
- `professional` (default) - Clean, modern, corporate style
- `luxury` - Luxurious, premium, sophisticated
- `warm` - Warm tones, inviting, friendly
- `creative` - Artistic, vibrant colors
- `minimalist` - Simple, clean lines, elegant

## 📸 Instagram Post Generation

REACH includes a powerful Instagram post generator that creates both property images and engaging captions with hashtags.

### Features

- **Complete Post Generation**: Generate image + caption in one call
- **Smart Hashtags**: Automatically generates 20-30 relevant real estate hashtags
- **Caption Styles**: Professional, Casual, Luxury, Friendly, Informative
- **Property Context**: Include property type, location, price, and features
- **Caption Variations**: Generate multiple caption options for A/B testing
- **Story & Reel Support**: Optimized captions for different Instagram formats

### Example Usage

```python
from src.workflow import REACHGraph

graph = REACHGraph()

# Generate complete Instagram post
result = await graph.generate_instagram_post(
    image_description="Modern luxury home with infinity pool overlooking the city",
    property_details={
        "property_type": "Villa",
        "location": "Los Angeles, CA",
        "price": "$3,500,000",
        "features": ["5 bedrooms", "infinity pool", "home theater", "wine cellar"]
    }
)

print(result["caption"])  # Engaging caption text
print(result["hashtags"])  # #realestate #luxuryhomes #losangeles ...
print(result["image"])     # Generated image URL or data
```

### Hashtag Categories

The Instagram agent automatically selects hashtags from these categories:
- **General**: #realestate, #realtor, #property, #home
- **Buying**: #homebuyer, #firsttimehomebuyer, #dreamhome
- **Selling**: #forsale, #justlisted, #openhouse
- **Luxury**: #luxuryrealestate, #luxuryhomes, #milliondollarlisting
- **Investment**: #realestateinvesting, #investmentproperty
- **Interior/Exterior**: #interiordesign, #curbappeal, #landscaping

## 🖼️ Image Generation with Google Imagen

REACH uses Google Imagen for high-quality property image generation. Imagen supports:

- **Aspect Ratios**: 1:1, 16:9, 9:16, 4:3, 3:4
- **Negative Prompts**: Specify what to avoid in images
- **Style Presets**: Professional, creative, minimalist, bold, warm, tech, natural, luxury

### Example Image Generation

```python
from src.integrations import ImagenClient

client = ImagenClient()

# Generate a property image
result = await client.generate_image(
    prompt="Modern luxury home exterior with landscaped garden",
    aspect_ratio="16:9",
    negative_prompt="text, watermark, low quality"
)
```

## 🛡️ Guardrails

REACH implements NeMo Guardrails to ensure safe and on-topic content generation:

### Topical Guardrails (Real Estate Only)

The system is restricted to Real Estate topics only. If you ask about off-topic subjects, you'll receive:

```
"Sorry! I cannot help you with that topic. My expertise is in Real Estate. 
I can help you with property listings, real estate marketing, home buying/selling content, 
property descriptions, and real estate social media posts."
```

**Allowed Topics:**
- Property buying, selling, renting, investing
- Real estate marketing and content creation
- Property descriptions and listings
- Mortgage and financing
- Property management
- Real estate social media and blog content

**Blocked Topics:**
- Programming/coding
- Cooking/recipes
- Sports/entertainment
- Politics
- Medical advice
- Cryptocurrency

### Safety Guardrails (Profanity Blocking)

The system blocks profanity and inappropriate content using semantic analysis:

- **Profanity Detection**: Blocks offensive language including leetspeak variations
- **Hate Speech**: Blocks discriminatory content
- **Violence**: Blocks violent or threatening content
- **Adult Content**: Blocks explicit or inappropriate material
- **Semantic Analysis**: Uses LLM to detect disguised inappropriate content

### Configuration

Guardrails are enabled by default. To disable:

```python
from src.workflow import REACHGraph

# Disable guardrails (not recommended for production)
graph = REACHGraph(enable_guardrails=False)
```

### NeMo Configuration Files

The guardrails configuration is stored in `rails_config/`:
- `config.yaml` - Main configuration with model settings and rail definitions
- `rails.co` - CoLang rules for conversation flows and content filtering

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [LangGraph](https://github.com/langchain-ai/langgraph) for multi-agent orchestration
- [Google GenAI](https://ai.google.dev/) for Gemini language model and Imagen image generation
- [NeMo Guardrails](https://github.com/NVIDIA/NeMo-Guardrails) for content safety
- [SERP API](https://serpapi.com/) for web research
- [Streamlit](https://streamlit.io/) for the web interface
