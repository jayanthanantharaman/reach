"""
Export Tools for REACH.


This module provides tools for exporting content in various formats.
"""

import json
import re
from datetime import datetime
from typing import Any, Optional


class ContentExporter:
    """
    Content export utilities.
    
    This class provides:
    - Export to various formats (Markdown, HTML, JSON)
    - Content packaging for different platforms
    - Metadata generation
    """

    def __init__(self):
        """Initialize the content exporter."""
        pass

    def export_to_markdown(
        self,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
        include_frontmatter: bool = True,
    ) -> str:
        """
        Export content as Markdown with optional frontmatter.
        
        Args:
            content: Content to export
            metadata: Optional metadata for frontmatter
            include_frontmatter: Whether to include YAML frontmatter
            
        Returns:
            Markdown string
        """
        output_parts = []

        if include_frontmatter and metadata:
            frontmatter = self._generate_frontmatter(metadata)
            output_parts.append(frontmatter)

        output_parts.append(content)

        return "\n".join(output_parts)

    def _generate_frontmatter(self, metadata: dict[str, Any]) -> str:
        """Generate YAML frontmatter from metadata."""
        lines = ["---"]

        for key, value in metadata.items():
            if isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
            elif isinstance(value, dict):
                lines.append(f"{key}:")
                for k, v in value.items():
                    lines.append(f"  {k}: {v}")
            elif isinstance(value, datetime):
                lines.append(f"{key}: {value.isoformat()}")
            else:
                lines.append(f"{key}: {value}")

        lines.append("---")
        lines.append("")

        return "\n".join(lines)

    def export_to_html(
        self,
        content: str,
        title: Optional[str] = None,
        include_styles: bool = True,
    ) -> str:
        """
        Export content as HTML.
        
        Args:
            content: Markdown content to convert
            title: Optional page title
            include_styles: Whether to include basic CSS styles
            
        Returns:
            HTML string
        """
        # Convert markdown to HTML (basic conversion)
        html_content = self._markdown_to_html(content)

        # Build full HTML document
        styles = self._get_default_styles() if include_styles else ""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title or 'Content'}</title>
    {styles}
</head>
<body>
    <article class="content">
        {html_content}
    </article>
</body>
</html>"""

        return html

    def _markdown_to_html(self, markdown: str) -> str:
        """Convert markdown to HTML (basic conversion)."""
        html = markdown

        # Convert headings
        html = re.sub(r'^######\s+(.+)$', r'<h6>\1</h6>', html, flags=re.MULTILINE)
        html = re.sub(r'^#####\s+(.+)$', r'<h5>\1</h5>', html, flags=re.MULTILINE)
        html = re.sub(r'^####\s+(.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
        html = re.sub(r'^###\s+(.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^##\s+(.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^#\s+(.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

        # Convert bold and italic
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

        # Convert links
        html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)

        # Convert images
        html = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1">', html)

        # Convert bullet lists
        html = re.sub(r'^[-*]\s+(.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)

        # Wrap consecutive list items
        html = re.sub(r'(<li>.*?</li>\n?)+', r'<ul>\g<0></ul>', html)

        # Convert paragraphs
        paragraphs = html.split('\n\n')
        processed = []
        for p in paragraphs:
            p = p.strip()
            if p and not p.startswith('<'):
                p = f'<p>{p}</p>'
            processed.append(p)
        html = '\n'.join(processed)

        return html

    def _get_default_styles(self) -> str:
        """Get default CSS styles."""
        return """<style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }
        h1, h2, h3, h4, h5, h6 {
            margin-top: 1.5em;
            margin-bottom: 0.5em;
            color: #1a1a1a;
        }
        h1 { font-size: 2.5em; }
        h2 { font-size: 2em; }
        h3 { font-size: 1.5em; }
        p { margin-bottom: 1em; }
        ul, ol { margin-bottom: 1em; padding-left: 2em; }
        li { margin-bottom: 0.5em; }
        a { color: #0066cc; text-decoration: none; }
        a:hover { text-decoration: underline; }
        img { max-width: 100%; height: auto; }
        blockquote {
            border-left: 4px solid #ddd;
            margin: 1em 0;
            padding-left: 1em;
            color: #666;
        }
        code {
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: monospace;
        }
    </style>"""

    def export_to_json(
        self,
        content: str,
        content_type: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Export content as JSON.
        
        Args:
            content: Content to export
            content_type: Type of content
            metadata: Optional metadata
            
        Returns:
            JSON string
        """
        export_data = {
            "content": content,
            "content_type": content_type,
            "metadata": metadata or {},
            "exported_at": datetime.now().isoformat(),
            "word_count": len(content.split()),
            "char_count": len(content),
        }

        return json.dumps(export_data, indent=2, ensure_ascii=False)

    def export_for_wordpress(
        self,
        content: str,
        title: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Export content formatted for WordPress.
        
        Args:
            content: Content to export
            title: Post title
            metadata: Optional metadata
            
        Returns:
            Dictionary with WordPress-compatible data
        """
        metadata = metadata or {}

        # Convert markdown to HTML for WordPress
        html_content = self._markdown_to_html(content)

        return {
            "title": title,
            "content": html_content,
            "status": "draft",
            "categories": metadata.get("categories", []),
            "tags": metadata.get("tags", []),
            "meta": {
                "description": metadata.get("meta_description", ""),
                "keywords": metadata.get("keywords", []),
            },
            "featured_media": metadata.get("featured_image", None),
        }

    def export_for_linkedin(
        self,
        content: str,
        include_formatting: bool = True,
    ) -> dict[str, Any]:
        """
        Export content formatted for LinkedIn.
        
        Args:
            content: Content to export
            include_formatting: Whether to include LinkedIn-specific formatting
            
        Returns:
            Dictionary with LinkedIn-compatible data
        """
        # Clean content for LinkedIn
        linkedin_content = content

        if include_formatting:
            # Remove markdown formatting that LinkedIn doesn't support
            linkedin_content = re.sub(r'^#{1,6}\s+', '', linkedin_content, flags=re.MULTILINE)
            linkedin_content = re.sub(r'\*\*(.+?)\*\*', r'\1', linkedin_content)
            linkedin_content = re.sub(r'\*(.+?)\*', r'\1', linkedin_content)
            linkedin_content = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 (\2)', linkedin_content)

        # Extract hashtags
        hashtags = re.findall(r'#\w+', content)

        return {
            "content": linkedin_content,
            "hashtags": hashtags,
            "char_count": len(linkedin_content),
            "is_within_limit": len(linkedin_content) <= 3000,
        }

    def create_content_package(
        self,
        content: str,
        content_type: str,
        title: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Create a complete content package with multiple formats.
        
        Args:
            content: Content to package
            content_type: Type of content
            title: Content title
            metadata: Optional metadata
            
        Returns:
            Dictionary with content in multiple formats
        """
        metadata = metadata or {}
        metadata["title"] = title
        metadata["content_type"] = content_type
        metadata["created_at"] = datetime.now().isoformat()

        package = {
            "title": title,
            "content_type": content_type,
            "metadata": metadata,
            "formats": {
                "markdown": self.export_to_markdown(content, metadata),
                "html": self.export_to_html(content, title),
                "json": self.export_to_json(content, content_type, metadata),
                "plain_text": self._strip_formatting(content),
            },
        }

        # Add platform-specific exports
        if content_type == "blog":
            package["platforms"] = {
                "wordpress": self.export_for_wordpress(content, title, metadata),
            }
        elif content_type == "linkedin":
            package["platforms"] = {
                "linkedin": self.export_for_linkedin(content),
            }

        return package

    def _strip_formatting(self, content: str) -> str:
        """Strip all formatting from content."""
        # Remove markdown formatting
        text = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', text)
        text = re.sub(r'^[-*]\s+', '', text, flags=re.MULTILINE)

        return text.strip()

    def generate_social_snippets(
        self,
        content: str,
        title: str,
    ) -> dict[str, str]:
        """
        Generate social media snippets from content.
        
        Args:
            content: Source content
            title: Content title
            
        Returns:
            Dictionary with platform-specific snippets
        """
        # Extract first paragraph for summary
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        summary = paragraphs[0] if paragraphs else content[:200]

        # Clean summary
        summary = self._strip_formatting(summary)

        return {
            "twitter": self._create_twitter_snippet(title, summary),
            "linkedin": self._create_linkedin_snippet(title, summary),
            "facebook": self._create_facebook_snippet(title, summary),
        }

    def _create_twitter_snippet(self, title: str, summary: str) -> str:
        """Create Twitter/X snippet."""
        max_length = 280
        snippet = f"{title}\n\n{summary}"

        if len(snippet) > max_length:
            snippet = snippet[:max_length - 3] + "..."

        return snippet

    def _create_linkedin_snippet(self, title: str, summary: str) -> str:
        """Create LinkedIn snippet."""
        return f"{title}\n\n{summary[:500]}\n\n#ContentMarketing #Business"

    def _create_facebook_snippet(self, title: str, summary: str) -> str:
        """Create Facebook snippet."""
        return f"📝 {title}\n\n{summary[:300]}\n\nRead more 👇"