# 🚀 Deploying REACH to Hugging Face Spaces (Docker)

This guide provides step-by-step instructions to deploy REACH on Hugging Face Spaces using Docker on the free tier.

## Prerequisites

1. **Hugging Face Account**: Create a free account at [huggingface.co](https://huggingface.co/join)
2. **Git**: Installed on your local machine
3. **API Keys**: You'll need:
   - Google Gemini API Key (for LLM and Imagen)
   - SERP API Key (for research - optional)

## Step 1: Create a New Space

1. Go to [huggingface.co/spaces](https://huggingface.co/spaces)
2. Click **"Create new Space"**
3. Fill in the details:
   - **Space name**: `reach` (or your preferred name)
   - **License**: MIT (or your preference)
   - **SDK**: Select **Docker**
   - **Hardware**: **CPU basic** (free tier)
   - **Visibility**: Public or Private (your choice)
4. Click **"Create Space"**

## Step 2: Clone the Space Repository

After creating the space, clone it to your local machine:

```bash
# Clone your new space
git clone https://huggingface.co/spaces/YOUR_USERNAME/reach
cd reach
```

## Step 2.5: Set Up Git LFS for Binary Files

Hugging Face requires Git LFS (Large File Storage) for binary files like images. Set it up:

```bash
# Install Git LFS (if not already installed)
# On macOS:
brew install git-lfs

# On Ubuntu/Debian:
sudo apt-get install git-lfs

# On Windows (with Git Bash):
# Download from https://git-lfs.github.com/

# Initialize Git LFS in your repository
git lfs install

# Track image files with Git LFS
git lfs track "*.png"
git lfs track "*.jpg"
git lfs track "*.jpeg"
git lfs track "*.gif"
git lfs track "*.ico"

# This creates a .gitattributes file - commit it
git add .gitattributes
git commit -m "Configure Git LFS for binary files"
```

**Alternative: Remove the logo file**

If you don't want to use Git LFS, you can remove the logo file:

```bash
# Remove the logo file from the space
rm -rf src/web_app/assets/ask_reach.png

# Or exclude it when copying files (see Step 3)
```

The app will work without the logo - it will just show text instead.

## Step 3: Copy REACH Files

Copy all the REACH project files to your cloned space directory:

```bash
# From your REACH project directory, copy everything to the space
cp -r src/ YOUR_SPACE_DIRECTORY/
cp -r rails_config/ YOUR_SPACE_DIRECTORY/
cp requirements.txt YOUR_SPACE_DIRECTORY/
cp Dockerfile YOUR_SPACE_DIRECTORY/
cp .dockerignore YOUR_SPACE_DIRECTORY/
```

Or if you're in the REACH project directory:

```bash
# Copy to your space directory
rsync -av --exclude='.git' --exclude='venv' --exclude='__pycache__' \
    --exclude='.env' --exclude='*.db' --exclude='*.sqlite' \
    . YOUR_SPACE_DIRECTORY/
```

## Step 4: Verify Dockerfile

Ensure the `Dockerfile` is in the root of your space directory:

```dockerfile
# REACH - Real Estate Automated Content Hub
# Docker deployment for Hugging Face Spaces

FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create a non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose Streamlit port (Hugging Face Spaces uses 7860)
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:7860/_stcore/health || exit 1

# Run the Streamlit app
CMD ["streamlit", "run", "src/web_app/streamlit_app.py", \
     "--server.port=7860", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false", \
     "--server.fileWatcherType=none"]
```

## Step 5: Create Space README

Create a `README.md` file in the root of your space with the required metadata:

```markdown
---
title: REACH - Real Estate Content Hub
emoji: 🏠
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
license: mit
---

# 🏠 REACH - Real Estate Automated Content Hub

AI-Powered Multi-Agent Content Creation System for Real Estate

## Features
- 📝 SEO Blog Writer with auto-generated header images
- 💼 LinkedIn Post Writer
- 📸 Instagram Post Generator (image + caption with hashtags)
- 🔍 Research Agent with SERP API
- 🖼️ Image Generation with Google Imagen
- 📊 Content Strategist
- 🛡️ NeMo Guardrails (Real Estate only, profanity blocking)

## Usage
Simply type your request in the chat, and REACH will automatically route it to the appropriate agent.

### Example Prompts
- "Write a blog post about home staging tips"
- "Create a LinkedIn post about market trends"
- "Generate an Instagram post for a luxury condo"
- "Research current housing market in Austin"
- "Create a content strategy for a real estate agency"

## Technology Stack
- **LLM**: Google Gemini 1.5
- **Image Generation**: Google Imagen 3
- **Orchestration**: LangGraph
- **UI**: Streamlit
- **Guardrails**: NeMo Guardrails
```

## Step 6: Configure Secrets

Hugging Face Spaces uses **Secrets** for environment variables (API keys).

1. Go to your Space's **Settings** tab
2. Scroll down to **Repository secrets**
3. Add the following secrets:

| Secret Name | Value | Required |
|-------------|-------|----------|
| `GOOGLE_API_KEY` | Your Google Gemini API key | ✅ Yes |
| `SERP_API_KEY` | Your SERP API key | ❌ Optional |
| `GEMINI_MODEL` | `gemini-1.5-flash` | ❌ Optional |
| `GEMINI_TEMPERATURE` | `0.7` | ❌ Optional |
| `GEMINI_MAX_TOKENS` | `4096` | ❌ Optional |
| `IMAGEN_MODEL` | `imagen-3.0-generate-002` | ❌ Optional |

### Getting API Keys

#### Google Gemini API Key
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the key and add it as `GOOGLE_API_KEY` secret

#### SERP API Key (Optional)
1. Go to [SerpAPI](https://serpapi.com/)
2. Sign up for a free account (100 searches/month)
3. Copy your API key and add it as `SERP_API_KEY` secret

## Step 7: Push to Hugging Face

Push your files to the Hugging Face Space:

```bash
cd YOUR_SPACE_DIRECTORY

# Add all files
git add .

# Commit
git commit -m "Initial REACH deployment with Docker"

# Push to Hugging Face
git push
```

## Step 8: Monitor Deployment

1. Go to your Space page on Hugging Face
2. Click on the **"Logs"** tab to monitor the build process
3. The Docker build typically takes 3-7 minutes
4. Once complete, your app will be live at `https://huggingface.co/spaces/YOUR_USERNAME/reach`

### Build Stages

You'll see these stages in the logs:
1. **Building Docker image** - Installing dependencies
2. **Starting container** - Launching the app
3. **Health check** - Verifying the app is running
4. **Ready** - App is live!

## File Structure

Your space directory should look like this:

```
your-space/
├── Dockerfile              # Docker configuration (required)
├── .dockerignore           # Files to exclude from Docker build
├── README.md               # Space metadata (required)
├── requirements.txt        # Python dependencies
├── src/
│   ├── __init__.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py
│   │   ├── blog_writer.py
│   │   ├── content_strategist.py
│   │   ├── image_generator.py
│   │   ├── instagram_writer.py
│   │   ├── linkedin_writer.py
│   │   ├── query_handler.py
│   │   └── research_agent.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── router.py
│   ├── guardrails/
│   │   ├── __init__.py
│   │   ├── guardrails_manager.py
│   │   ├── safety_guard.py
│   │   └── topical_guard.py
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── gemini_client.py
│   │   ├── imagen_client.py
│   │   └── serp_client.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── content_optimization.py
│   │   ├── content_storage.py
│   │   ├── export_tools.py
│   │   └── quality_validation.py
│   ├── web_app/
│   │   ├── __init__.py
│   │   ├── streamlit_app.py
│   │   └── assets/
│   │       └── ask_reach.png
│   └── workflow/
│       ├── __init__.py
│       ├── langgraph_workflow.py
│       └── state_management.py
└── rails_config/
    ├── config.yaml
    └── rails.co
```

## Troubleshooting

### Common Issues

#### 1. Build Fails - Memory Error
The free tier has limited memory (16GB). Try:
- Use `gemini-1.5-flash` instead of `gemini-1.5-pro`
- Reduce `GEMINI_MAX_TOKENS` to `2048`

#### 2. Container Fails to Start
Check the logs for errors. Common issues:
- Missing secrets (API keys)
- Import errors (check Python paths)
- Port conflicts (ensure port 7860 is used)

#### 3. API Key Not Found
Ensure secrets are properly configured. The app reads them from environment variables:
```python
import os
api_key = os.environ.get("GOOGLE_API_KEY")
```

#### 4. Timeout Errors
Free tier has a 60-second timeout for requests. For long-running tasks:
- Use streaming for text generation (enabled by default)
- Reduce image generation quality
- Add progress indicators

#### 5. Health Check Fails
If the health check fails, the container will restart. Ensure:
- Streamlit is running on port 7860
- The app starts within 5 minutes (start-period)

### Viewing Logs

To debug issues:
1. Go to your Space page
2. Click the **"Logs"** tab
3. Look for error messages in red
4. Check both build logs and runtime logs

## Performance Tips for Free Tier

1. **Use Flash Model**: Set `GEMINI_MODEL=gemini-1.5-flash` for faster responses
2. **Reduce Token Limits**: Set `GEMINI_MAX_TOKENS=2048` for quicker generation
3. **Enable Streaming**: Already enabled by default for text content
4. **Optimize Images**: Images are generated at standard quality

## Updating Your Space

To update your deployed app:

```bash
# Make changes locally
# ...

# Commit and push
git add .
git commit -m "Update: description of changes"
git push
```

The Space will automatically rebuild and redeploy (takes 3-7 minutes).

## Local Docker Testing

Before pushing to Hugging Face, test locally:

```bash
# Build the image
docker build -t reach .

# Run with environment variables
docker run -p 7860:7860 \
    -e GOOGLE_API_KEY=your-api-key \
    -e SERP_API_KEY=your-serp-key \
    reach

# Open http://localhost:7860 in your browser
```

## Cost Considerations

| Feature | Free Tier | Pro ($9/month) |
|---------|-----------|----------------|
| CPU | Basic (2 vCPU) | Upgraded (4 vCPU) |
| RAM | 16GB | 32GB |
| Storage | 50GB | 100GB |
| Timeout | 60s | 5min |
| Private Spaces | Limited | Unlimited |
| Persistent Storage | No | Yes |

For production use with heavy traffic, consider upgrading to Pro.

## Quick Reference

### Essential Commands

```bash
# Clone space
git clone https://huggingface.co/spaces/YOUR_USERNAME/reach

# Push updates
git add . && git commit -m "Update" && git push

# View logs (in browser)
# Go to: https://huggingface.co/spaces/YOUR_USERNAME/reach → Logs tab
```

### Required Secrets

| Secret | Description |
|--------|-------------|
| `GOOGLE_API_KEY` | Google Gemini API key (required) |
| `SERP_API_KEY` | SERP API key (optional, for research) |

### Recommended Settings

| Setting | Value | Reason |
|---------|-------|--------|
| `GEMINI_MODEL` | `gemini-1.5-flash` | Faster, less memory |
| `GEMINI_MAX_TOKENS` | `2048-4096` | Balance speed/quality |
| Hardware | CPU basic | Free tier |

## Support

- **Hugging Face Docs**: [huggingface.co/docs/hub/spaces](https://huggingface.co/docs/hub/spaces)
- **Docker on Spaces**: [huggingface.co/docs/hub/spaces-sdks-docker](https://huggingface.co/docs/hub/spaces-sdks-docker)
- **Community Forum**: [discuss.huggingface.co](https://discuss.huggingface.co)
- **Streamlit Docs**: [docs.streamlit.io](https://docs.streamlit.io)