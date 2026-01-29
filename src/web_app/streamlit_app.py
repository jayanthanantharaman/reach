"""
Streamlit Web Application for REACH - Real Estate Automated Content Hub.


This module provides an interactive web interface for the
multi-agent real estate content creation system.
"""

import asyncio
import base64
import sys
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

import streamlit as st

# Ensure repo root is on sys.path so `src.*` imports work when run as a script.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Asset paths
ASSETS_DIR = Path(__file__).resolve().parent / "assets"
LOGO_PATH = ASSETS_DIR / "ask_reach.png"

# Import REACH components
from src.workflow import REACHGraph
from src.utils import ContentOptimizer, ContentStorage, QualityValidator, ContentExporter


def get_or_create_event_loop():
    """Get or create an event loop for async operations."""
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


def run_async(coro):
    """Run an async coroutine in the event loop."""
    loop = get_or_create_event_loop()
    return loop.run_until_complete(coro)


@lru_cache
def _logo_data_uri(path: Path) -> str:
    """Return a data URI for the logo image, or empty string if missing."""
    if not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def init_session_state():
    """Initialize Streamlit session state."""
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "graph" not in st.session_state:
        st.session_state.graph = REACHGraph()

    if "generated_content" not in st.session_state:
        st.session_state.generated_content = {}

    if "optimizer" not in st.session_state:
        st.session_state.optimizer = ContentOptimizer()

    if "validator" not in st.session_state:
        st.session_state.validator = QualityValidator()

    if "exporter" not in st.session_state:
        st.session_state.exporter = ContentExporter()

    if "content_storage" not in st.session_state:
        st.session_state.content_storage = ContentStorage()


def save_content_to_storage(content: str, content_type: str, prompt: str = None):
    """Save generated content to persistent storage."""
    try:
        st.session_state.content_storage.save_content(
            session_id=st.session_state.session_id,
            content_type=content_type,
            content=content,
            prompt=prompt,
        )
    except Exception as e:
        # Log error but don't interrupt the user experience
        st.warning(f"Could not save to history: {str(e)}")


def render_sidebar():
    """Render the sidebar with options and settings."""
    with st.sidebar:
        logo_exists = LOGO_PATH.exists()
        if logo_exists:
            logo_uri = _logo_data_uri(LOGO_PATH)
            if logo_uri:
                st.markdown(
                    f"""
                    <div style="display:flex; align-items:center; gap:10px;">
                      <img src="{logo_uri}" alt="REACH" style="width:36px; height:36px; object-fit:contain;" />
                      <h2 style="margin:0; padding:0;">REACH</h2>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.title("REACH")
        else:
            st.title("REACH")
        st.markdown("*Real Estate Automated Content Hub*")
        st.caption("AI-Powered Content Creation for Real Estate")

        st.divider()

        # Content type selector
        st.subheader("Quick Actions")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📝 Blog", use_container_width=True):
                st.session_state.quick_action = "blog"
        with col2:
            if st.button("💼 LinkedIn", use_container_width=True):
                st.session_state.quick_action = "linkedin"

        col3, col4 = st.columns(2)
        with col3:
            if st.button("🔍 Research", use_container_width=True):
                st.session_state.quick_action = "research"
        with col4:
            if st.button("🖼️ Image", use_container_width=True):
                st.session_state.quick_action = "image"

        col5, col6 = st.columns(2)
        with col5:
            if st.button("📸 Instagram", use_container_width=True):
                st.session_state.quick_action = "instagram"
        with col6:
            if st.button("📊 Strategy", use_container_width=True):
                st.session_state.quick_action = "strategy"

        # Instagram Post Generator (Image + Caption)
        st.divider()
        st.subheader("📸 Instagram Post")
        if st.button("🎨 Generate Post", use_container_width=True, help="Generate image + caption with hashtags"):
            st.session_state.show_instagram_generator = True

        st.divider()

        # Guardrails status
        st.subheader("🛡️ Guardrails")
        guardrails_status = st.session_state.graph.get_guardrails_status()
        if guardrails_status.get("topical_enabled"):
            st.success("✅ Real Estate Topics Only")
        if guardrails_status.get("safety_enabled"):
            st.success("✅ Safety Filters Active")

        st.divider()

        # Session management
        st.subheader("Session")
        st.text(f"ID: {st.session_state.session_id[:8]}...")

        if st.button("🔄 New Session", use_container_width=True):
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.session_state.generated_content = {}
            st.rerun()

        if st.button("🗑️ Clear History", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

        st.divider()

        # Settings
        st.subheader("Settings")
        st.session_state.use_streaming = st.checkbox(
            "🚀 Enable Streaming",
            value=st.session_state.get("use_streaming", True),
            help="Stream text as it's generated for a more interactive experience",
        )
        st.session_state.show_analysis = st.checkbox(
            "Show Content Analysis",
            value=True,
        )
        st.session_state.auto_optimize = st.checkbox(
            "Auto-optimize Content",
            value=False,
        )

        st.divider()

        # Topic suggestions
        st.subheader("💡 Topic Ideas")
        suggestions = st.session_state.graph.get_topic_suggestions()
        if suggestions:
            for suggestion in suggestions[:4]:
                st.caption(f"• {suggestion}")


def render_copy_button(content: str, key: str):
    """Render a copy button that copies content to clipboard."""
    # Create a unique ID for this copy button
    button_id = f"copy_btn_{key}"
    
    # JavaScript to copy text to clipboard
    copy_js = f"""
    <script>
    function copyToClipboard_{key.replace('-', '_')}() {{
        const text = {repr(content)};
        navigator.clipboard.writeText(text).then(function() {{
            const btn = document.getElementById('{button_id}');
            btn.innerHTML = '✅ Copied!';
            setTimeout(function() {{
                btn.innerHTML = '📋 Copy';
            }}, 2000);
        }}).catch(function(err) {{
            console.error('Failed to copy: ', err);
        }});
    }}
    </script>
    <button id="{button_id}" onclick="copyToClipboard_{key.replace('-', '_')}()" 
            style="background-color: #262730; color: white; border: 1px solid #4a4a5a; 
                   padding: 4px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;
                   transition: background-color 0.2s;">
        📋 Copy
    </button>
    """
    st.markdown(copy_js, unsafe_allow_html=True)


def render_chat_interface():
    """Render the main chat interface with streaming support."""
    logo_exists = LOGO_PATH.exists()
    if logo_exists:
        logo_uri = _logo_data_uri(LOGO_PATH)
        if logo_uri:
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; gap:12px;">
                  <img src="{logo_uri}" alt="Ask REACH" style="width:56px; height:56px; object-fit:contain;" />
                  <h1 style="margin:0; padding:0;">Ask REACH</h1>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.title("Ask REACH")
    else:
        st.title("Ask REACH")
    st.caption("Create property listings, blogs, LinkedIn posts, and more!")

    # Streaming toggle in sidebar
    if "use_streaming" not in st.session_state:
        st.session_state.use_streaming = True

    # Display chat messages
    for idx, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            # Show content type badge and copy button for assistant messages
            if message["role"] == "assistant":
                col1, col2 = st.columns([3, 1])
                with col1:
                    if message.get("content_type"):
                        content_type = message['content_type']
                        if content_type == "guardrails_blocked":
                            st.caption("🛡️ Blocked by Guardrails")
                        else:
                            st.caption(f"📌 {content_type.title()}")
                with col2:
                    # Add copy button for assistant messages
                    if message.get("content_type") != "guardrails_blocked":
                        render_copy_button(message["content"], f"msg_{idx}")
            elif message.get("content_type"):
                content_type = message['content_type']
                if content_type == "guardrails_blocked":
                    st.caption("🛡️ Blocked by Guardrails")
                else:
                    st.caption(f"📌 {content_type.title()}")

    # Chat input
    if prompt := st.chat_input("What real estate content would you like to create?"):
        # Handle quick actions
        if hasattr(st.session_state, "quick_action"):
            action = st.session_state.quick_action
            del st.session_state.quick_action

            action_prompts = {
                "blog": f"Write a real estate blog post about: {prompt}",
                "linkedin": f"Create a LinkedIn post for realtors about: {prompt}",
                "instagram": f"Create an Instagram caption with hashtags for: {prompt}",
                "research": f"Research real estate topic: {prompt}",
                "image": f"Generate a property image of: {prompt}",
                "strategy": f"Create a real estate content strategy for: {prompt}",
            }
            prompt = action_prompts.get(action, prompt)

        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
        })

        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response with streaming
        with st.chat_message("assistant"):
            # Check if this is an image request (don't stream for images)
            is_image_request = any(word in prompt.lower() for word in ["image", "picture", "photo", "generate image"])
            
            if st.session_state.use_streaming and not is_image_request:
                # Use streaming for text generation
                try:
                    # Get metadata first (content type)
                    metadata = st.session_state.graph.get_streaming_metadata(
                        prompt,
                        session_id=st.session_state.session_id,
                    )
                    content_type = metadata.get("content_type", "general")
                    
                    # Stream the response
                    response_placeholder = st.empty()
                    full_content = ""
                    
                    for chunk in st.session_state.graph.run_stream(
                        prompt,
                        session_id=st.session_state.session_id,
                    ):
                        full_content += chunk
                        response_placeholder.markdown(full_content + "▌")
                    
                    # Final update without cursor
                    response_placeholder.markdown(full_content)
                    st.caption(f"📌 {content_type.title()}")
                    
                    # Store in session
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": full_content,
                        "content_type": content_type,
                    })
                    
                    # Store generated content
                    if content_type not in st.session_state.generated_content:
                        st.session_state.generated_content[content_type] = []
                    st.session_state.generated_content[content_type].append(full_content)
                    
                    # Save to persistent storage (SQLite)
                    save_content_to_storage(full_content, content_type, prompt)
                    
                    # Show analysis if enabled
                    if st.session_state.show_analysis and content_type in ["blog", "linkedin", "instagram"]:
                        render_content_analysis(full_content, content_type)
                        
                except Exception as e:
                    st.error(f"❌ Streaming error: {str(e)}")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"Error: {str(e)}",
                    })
            else:
                # Use non-streaming for images or when streaming is disabled
                with st.spinner("Creating content..."):
                    result = run_async(
                        st.session_state.graph.run(
                            prompt,
                            session_id=st.session_state.session_id,
                        )
                    )

                    content = result.get("content", "")
                    content_type = result.get("content_type", "general")
                    guardrails = result.get("guardrails", {})

                    if guardrails.get("blocked"):
                        # Show guardrails blocked message
                        st.warning(content)
                        st.caption(f"🛡️ Blocked by: {guardrails.get('blocked_by', 'guardrails').title()}")

                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": content,
                            "content_type": "guardrails_blocked",
                        })
                    elif result["success"]:
                        st.markdown(content)
                        st.caption(f"📌 {content_type.title()}")

                        # Store in session
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": content,
                            "content_type": content_type,
                        })

                        # Store generated content
                        if content_type not in st.session_state.generated_content:
                            st.session_state.generated_content[content_type] = []
                        st.session_state.generated_content[content_type].append(content)

                        # Save to persistent storage (SQLite)
                        save_content_to_storage(content, content_type, prompt)

                        # Show analysis if enabled
                        if st.session_state.show_analysis and content_type in ["blog", "linkedin", "instagram"]:
                            render_content_analysis(content, content_type)
                    else:
                        error_msg = f"❌ Error: {result.get('error', 'Unknown error')}"
                        st.error(error_msg)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": error_msg,
                        })


def render_content_analysis(content: str, content_type: str):
    """Render content analysis section."""
    with st.expander("📊 Content Analysis", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            # Quality validation
            validation = st.session_state.validator.validate_content(
                content, content_type
            )
            score = validation["overall_score"] * 100

            st.metric("Quality Score", f"{score:.0f}%")

            if validation["is_valid"]:
                st.success("✅ Content passes quality checks")
            else:
                st.warning("⚠️ Some quality issues found")

            if validation["issues"]:
                st.write("**Issues:**")
                for issue in validation["issues"]:
                    st.write(f"- {issue}")

        with col2:
            # SEO analysis for blogs
            if content_type == "blog":
                seo = st.session_state.optimizer.get_seo_score(content)
                st.metric("SEO Score", f"{seo['total_score']}/100")
                st.write(f"**Grade:** {seo['grade']}")

            # Readability
            readability = st.session_state.optimizer.analyze_readability(content)
            st.write(f"**Reading Level:** {readability['reading_level']}")
            st.write(f"**Word Count:** {readability['word_count']}")


def render_content_dashboard():
    """Render the content dashboard tab."""
    st.header("📋 Content Dashboard")

    if not st.session_state.generated_content:
        st.info("No content generated yet. Start chatting to create real estate content!")

        # Show example prompts
        st.subheader("💡 Try these prompts:")
        examples = [
            "Write a property listing for a 3-bedroom house in Austin",
            "Create a LinkedIn post about home staging tips",
            "Research current housing market trends",
            "Generate an image for a luxury condo listing",
        ]
        for example in examples:
            st.caption(f"• {example}")
        return

    # Content type tabs
    content_types = list(st.session_state.generated_content.keys())
    tabs = st.tabs([ct.title() for ct in content_types])

    for tab, content_type in zip(tabs, content_types):
        with tab:
            contents = st.session_state.generated_content[content_type]

            for i, content in enumerate(contents):
                with st.expander(f"{content_type.title()} #{i + 1}", expanded=(i == len(contents) - 1)):
                    st.markdown(content)

                    # Action buttons
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        if st.button(f"📋 Copy", key=f"copy_{content_type}_{i}"):
                            st.code(content)
                            st.success("Content displayed above - copy from there!")

                    with col2:
                        if st.button(f"📊 Analyze", key=f"analyze_{content_type}_{i}"):
                            render_content_analysis(content, content_type)

                    with col3:
                        if st.button(f"📤 Export", key=f"export_{content_type}_{i}"):
                            export_data = st.session_state.exporter.export_to_json(
                                content, content_type
                            )
                            st.download_button(
                                "Download JSON",
                                export_data,
                                f"{content_type}_{i + 1}.json",
                                "application/json",
                            )


def render_instagram_generator(key_prefix: str = "ig"):
    """Render the Instagram post generator."""
    st.header("📸 Instagram Post Generator")
    st.caption("Generate property images with engaging captions and hashtags")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Property Details")
        image_description = st.text_area(
            "Describe the property image:",
            placeholder="Modern luxury home with pool and landscaped garden",
            height=100,
            key=f"{key_prefix}_image_desc",
        )

        property_type = st.selectbox(
            "Property Type:",
            ["House", "Condo", "Apartment", "Townhouse", "Villa", "Commercial", "Land"],
            key=f"{key_prefix}_property_type",
        )

        location = st.text_input(
            "Location:",
            placeholder="Austin, TX",
            key=f"{key_prefix}_location",
        )

        price = st.text_input(
            "Price (optional):",
            placeholder="$500,000",
            key=f"{key_prefix}_price",
        )

        features = st.text_input(
            "Key Features (comma-separated):",
            placeholder="3 bedrooms, 2 bathrooms, pool, garden",
            key=f"{key_prefix}_features",
        )

    with col2:
        st.subheader("Generation Options")

        generate_image = st.checkbox(
            "Generate Image",
            value=True,
            key=f"{key_prefix}_gen_image",
        )
        generate_caption = st.checkbox(
            "Generate Caption",
            value=True,
            key=f"{key_prefix}_gen_caption",
        )

        caption_style = st.selectbox(
            "Caption Style:",
            ["Professional", "Casual", "Luxury", "Friendly", "Informative"],
            key=f"{key_prefix}_caption_style",
        )

        include_cta = st.checkbox(
            "Include Call-to-Action",
            value=True,
            key=f"{key_prefix}_include_cta",
        )

    if st.button(
        "🚀 Generate Instagram Post",
        use_container_width=True,
        type="primary",
        key=f"{key_prefix}_generate",
    ):
        if not image_description:
            st.warning("Please describe the property image.")
            return

        property_details = {
            "property_type": property_type,
            "location": location,
            "price": price,
            "features": [f.strip() for f in features.split(",") if f.strip()],
            "caption_style": caption_style,
            "include_cta": include_cta,
        }

        with st.spinner("Generating Instagram post..."):
            if generate_image and generate_caption:
                # Generate both image and caption
                result = run_async(
                    st.session_state.graph.generate_instagram_post(
                        image_description=image_description,
                        property_details=property_details,
                        session_id=st.session_state.session_id,
                    )
                )
            elif generate_caption:
                # Generate only caption
                result = run_async(
                    st.session_state.graph.generate_instagram_caption(
                        content_description=image_description,
                        context=property_details,
                        session_id=st.session_state.session_id,
                    )
                )
            else:
                # Generate only image
                result = run_async(
                    st.session_state.graph.run(
                        f"Generate a property image: {image_description}",
                        session_id=st.session_state.session_id,
                    )
                )

            if result.get("guardrails", {}).get("blocked"):
                st.error(f"🛡️ Blocked: {result.get('error', 'Content not allowed')}")
                return

            if result.get("success"):
                st.success("✅ Instagram post generated!")

                # Display results
                result_col1, result_col2 = st.columns(2)

                with result_col1:
                    if result.get("image"):
                        st.subheader("🖼️ Generated Image")
                        image_data = result["image"]
                        
                        # Handle different image data formats
                        if isinstance(image_data, str):
                            if image_data.startswith("http"):
                                # URL - display directly
                                st.image(image_data, use_container_width=True)
                            elif image_data.startswith("data:image"):
                                # Data URI (base64) - display directly
                                st.image(image_data, use_container_width=True)
                                
                                # Add download button for base64 image
                                # Extract the base64 data and mime type
                                try:
                                    header, b64_data = image_data.split(",", 1)
                                    mime_type = header.split(":")[1].split(";")[0]
                                    image_bytes = base64.b64decode(b64_data)
                                    
                                    st.download_button(
                                        "📥 Download Image",
                                        image_bytes,
                                        f"generated_image.{mime_type.split('/')[-1]}",
                                        mime_type,
                                        key=f"{key_prefix}_download_image",
                                    )
                                except Exception as e:
                                    st.caption(f"Could not prepare download: {e}")
                            else:
                                # Plain base64 string without data URI prefix
                                try:
                                    image_bytes = base64.b64decode(image_data)
                                    st.image(image_bytes, use_container_width=True)
                                    
                                    st.download_button(
                                        "📥 Download Image",
                                        image_bytes,
                                        "generated_image.png",
                                        "image/png",
                                        key=f"{key_prefix}_download_image",
                                    )
                                except Exception as e:
                                    st.error(f"Could not display image: {e}")
                                    st.code(str(image_data)[:200] + "..." if len(str(image_data)) > 200 else str(image_data))
                        elif isinstance(image_data, bytes):
                            # Raw bytes
                            st.image(image_data, use_container_width=True)
                            st.download_button(
                                "📥 Download Image",
                                image_data,
                                "generated_image.png",
                                "image/png",
                                key=f"{key_prefix}_download_image",
                            )
                        else:
                            st.warning("Unknown image format")
                            st.code(str(image_data)[:200] + "..." if len(str(image_data)) > 200 else str(image_data))

                with result_col2:
                    if result.get("caption") or result.get("full_post"):
                        st.subheader("📝 Caption")
                        caption = result.get("caption", result.get("full_post", ""))
                        st.text_area(
                            "Caption:",
                            value=caption,
                            height=200,
                            key=f"{key_prefix}_result_caption",
                        )

                        if result.get("hashtags"):
                            st.subheader("#️⃣ Hashtags")
                            st.code(result["hashtags"])

                # Full post preview
                if result.get("full_post"):
                    st.subheader("📱 Full Post Preview")
                    with st.expander("View Full Post", expanded=True):
                        st.markdown(result["full_post"])

                # Store in generated content
                if "instagram" not in st.session_state.generated_content:
                    st.session_state.generated_content["instagram"] = []
                st.session_state.generated_content["instagram"].append(result.get("full_post", ""))

                # Copy buttons
                col1, col2 = st.columns(2)
                with col1:
                    if result.get("caption"):
                        st.download_button(
                            "📋 Download Caption",
                            result.get("caption", ""),
                            "instagram_caption.txt",
                            "text/plain",
                            key=f"{key_prefix}_download_caption",
                        )
                with col2:
                    if result.get("full_post"):
                        st.download_button(
                            "📋 Download Full Post",
                            result.get("full_post", ""),
                            "instagram_post.txt",
                            "text/plain",
                            key=f"{key_prefix}_download_post",
                        )
            else:
                st.error(f"❌ Error: {result.get('error', 'Unknown error')}")


def render_tools_tab():
    """Render the tools tab."""
    st.header("🛠️ Content Tools")

    tool_tabs = st.tabs(["SEO Analyzer", "Quality Checker", "Export", "Instagram Generator"])

    # SEO Analyzer
    with tool_tabs[0]:
        st.subheader("SEO Content Analyzer")
        st.caption("Optimize your real estate content for search engines")

        content_input = st.text_area(
            "Paste your content here:",
            height=200,
            key="seo_content",
        )

        keywords_input = st.text_input(
            "Target keywords (comma-separated):",
            placeholder="real estate, home buying, property listing",
            key="seo_keywords",
        )

        if st.button("Analyze SEO", key="analyze_seo"):
            if content_input:
                keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]

                with st.spinner("Analyzing..."):
                    seo_result = st.session_state.optimizer.get_seo_score(
                        content_input,
                        target_keywords=keywords if keywords else None,
                    )

                    col1, col2 = st.columns(2)

                    with col1:
                        st.metric("SEO Score", f"{seo_result['total_score']}/100")
                        st.metric("Grade", seo_result["grade"])

                    with col2:
                        st.write("**Score Breakdown:**")
                        for key, value in seo_result["breakdown"].items():
                            st.write(f"- {key.title()}: {value}")

                    if seo_result.get("recommendations"):
                        st.write("**Recommendations:**")
                        for rec in seo_result["recommendations"]:
                            st.write(f"- {rec}")
            else:
                st.warning("Please enter content to analyze.")

    # Quality Checker
    with tool_tabs[1]:
        st.subheader("Content Quality Checker")
        st.caption("Ensure your real estate content meets quality standards")

        quality_content = st.text_area(
            "Paste your content here:",
            height=200,
            key="quality_content",
        )

        content_type = st.selectbox(
            "Content Type:",
            ["blog", "linkedin", "general"],
            key="quality_type",
        )

        if st.button("Check Quality", key="check_quality"):
            if quality_content:
                with st.spinner("Checking quality..."):
                    quality_result = st.session_state.validator.validate_content(
                        quality_content, content_type
                    )

                    score = quality_result["overall_score"] * 100

                    if quality_result["is_valid"]:
                        st.success(f"✅ Quality Score: {score:.0f}%")
                    else:
                        st.warning(f"⚠️ Quality Score: {score:.0f}%")

                    st.write("**Check Results:**")
                    for check_name, check_data in quality_result["checks"].items():
                        status = "✅" if check_data["passed"] else "❌"
                        st.write(f"{status} {check_data['name']}: {check_data['message']}")

                    if quality_result["suggestions"]:
                        st.write("**Suggestions:**")
                        for suggestion in quality_result["suggestions"]:
                            st.write(f"- {suggestion}")
            else:
                st.warning("Please enter content to check.")

    # Export
    with tool_tabs[2]:
        st.subheader("Export Content")
        st.caption("Export your real estate content in various formats")

        export_content = st.text_area(
            "Content to export:",
            height=200,
            key="export_content",
        )

        export_title = st.text_input("Title:", key="export_title")

        export_format = st.selectbox(
            "Export Format:",
            ["Markdown", "HTML", "JSON"],
            key="export_format",
        )

        if st.button("Export", key="do_export"):
            if export_content:
                exporter = st.session_state.exporter

                if export_format == "Markdown":
                    result = exporter.export_to_markdown(
                        export_content,
                        metadata={"title": export_title} if export_title else None,
                    )
                    filename = "content.md"
                    mime = "text/markdown"
                elif export_format == "HTML":
                    result = exporter.export_to_html(export_content, export_title)
                    filename = "content.html"
                    mime = "text/html"
                else:
                    result = exporter.export_to_json(export_content, "general")
                    filename = "content.json"
                    mime = "application/json"

                st.download_button(
                    f"Download {export_format}",
                    result,
                    filename,
                    mime,
                )
            else:
                st.warning("Please enter content to export.")

    # Instagram Generator
    with tool_tabs[3]:
        render_instagram_generator(key_prefix="ig_tools")


def render_history_tab():
    """Render the content history tab showing saved content from SQLite."""
    st.header("📚 Content History")
    st.caption("View your last 5 generated content items per type (persisted across sessions)")

    storage = st.session_state.content_storage

    # Get storage stats
    stats = storage.get_stats()
    
    # Display stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Items", stats["total_items"])
    with col2:
        st.metric("Content Types", len(stats["items_by_type"]))
    with col3:
        if stats["latest_entry"]:
            st.metric("Latest Entry", stats["latest_entry"][:10])
        else:
            st.metric("Latest Entry", "None")

    st.divider()

    # Filter options
    col1, col2 = st.columns([2, 1])
    with col1:
        content_types = storage.get_content_types()
        if content_types:
            selected_type = st.selectbox(
                "Filter by Content Type:",
                ["All"] + content_types,
                key="history_filter_type",
            )
        else:
            selected_type = "All"
    
    with col2:
        limit = st.number_input(
            "Items to show:",
            min_value=1,
            max_value=20,
            value=5,
            key="history_limit",
        )

    # Get content based on filter
    filter_type = None if selected_type == "All" else selected_type
    history_items = storage.get_recent_content(
        content_type=filter_type,
        limit=limit,
    )

    if not history_items:
        st.info("No content history yet. Generate some content to see it here!")
        return

    # Display content items
    for idx, item in enumerate(history_items):
        content_type = item["content_type"]
        created_at = item["created_at"]
        content = item["content"]
        prompt = item.get("prompt", "")
        
        # Create a nice header
        type_emoji = {
            "blog": "📝",
            "linkedin": "💼",
            "instagram": "📸",
            "research": "🔍",
            "strategy": "📊",
            "image": "🖼️",
            "general": "💬",
        }.get(content_type, "📄")
        
        with st.expander(
            f"{type_emoji} {content_type.title()} - {created_at[:16] if created_at else 'Unknown'}",
            expanded=(idx == 0),
        ):
            # Show prompt if available
            if prompt:
                st.caption(f"**Prompt:** {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
            
            # Show content
            st.markdown(content)
            
            # Action buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                render_copy_button(content, f"history_{item['id']}")
            
            with col2:
                st.download_button(
                    "📥 Download",
                    content,
                    f"{content_type}_{item['id']}.txt",
                    "text/plain",
                    key=f"download_history_{item['id']}",
                )
            
            with col3:
                if st.button("🗑️ Delete", key=f"delete_history_{item['id']}"):
                    storage.delete_content(item["id"])
                    st.success("Deleted!")
                    st.rerun()

    st.divider()

    # Clear history options
    st.subheader("⚠️ Manage History")
    col1, col2 = st.columns(2)
    
    with col1:
        if content_types:
            clear_type = st.selectbox(
                "Clear by type:",
                content_types,
                key="clear_type_select",
            )
            if st.button("Clear Selected Type", key="clear_type_btn"):
                deleted = storage.clear_by_type(clear_type)
                st.success(f"Deleted {deleted} items of type '{clear_type}'")
                st.rerun()
    
    with col2:
        if st.button("🗑️ Clear All History", type="secondary", key="clear_all_btn"):
            deleted = storage.clear_all()
            st.success(f"Deleted {deleted} items from history")
            st.rerun()


def main():
    """Main application entry point."""
    # Page config
    st.set_page_config(
        page_title="REACH - Real Estate Content Hub",
        page_icon="🏠",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Initialize session state
    init_session_state()

    # Render sidebar
    render_sidebar()

    # Main content area with tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["💬 Chat", "📸 Instagram", "📋 Dashboard", "📚 History", "🛠️ Tools"])

    with tab1:
        render_chat_interface()

    with tab2:
        render_instagram_generator(key_prefix="ig_main")

    with tab3:
        render_content_dashboard()

    with tab4:
        render_history_tab()

    with tab5:
        render_tools_tab()


if __name__ == "__main__":
    main()
