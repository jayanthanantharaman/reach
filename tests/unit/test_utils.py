"""
Unit tests for REACH utilities.

"""

import pytest

from src.utils.content_optimization import ContentOptimizer
from src.utils.quality_validation import QualityValidator
from src.utils.export_tools import ContentExporter


class TestContentOptimizer:
    """Tests for ContentOptimizer class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.optimizer = ContentOptimizer()

    def test_analyze_keywords_basic(self):
        """Test basic keyword analysis."""
        content = "Python is a great programming language. Python is easy to learn."
        result = self.optimizer.analyze_keywords(content)

        assert "word_count" in result
        assert "top_keywords" in result
        assert result["word_count"] > 0

    def test_analyze_keywords_with_targets(self):
        """Test keyword analysis with target keywords."""
        content = "Python programming is fun. Learn Python today for better coding skills."
        result = self.optimizer.analyze_keywords(content, target_keywords=["Python", "coding"])

        assert "target_keyword_analysis" in result
        assert len(result["target_keyword_analysis"]) == 2

        python_analysis = next(
            k for k in result["target_keyword_analysis"] if k["keyword"] == "Python"
        )
        assert python_analysis["count"] >= 2

    def test_analyze_readability(self):
        """Test readability analysis."""
        content = """
        This is a simple sentence. It is easy to read.
        Short sentences are good for readability.
        """
        result = self.optimizer.analyze_readability(content)

        assert "word_count" in result
        assert "sentence_count" in result
        assert "flesch_reading_ease" in result
        assert "reading_level" in result
        assert 0 <= result["flesch_reading_ease"] <= 100

    def test_analyze_structure(self):
        """Test structure analysis."""
        content = """
# Main Title

## Section One

This is some content with a [link](https://example.com).

- Bullet point one
- Bullet point two

## Section Two

More content here.
        """
        result = self.optimizer.analyze_structure(content)

        assert result["headings"]["h1_count"] == 1
        assert result["headings"]["h2_count"] == 2
        assert result["lists"]["bullet_items"] == 2
        assert result["links"]["count"] == 1

    def test_get_seo_score(self):
        """Test SEO score calculation."""
        content = """
# How to Learn Python Programming

## Introduction

Python is a versatile programming language that is perfect for beginners.
This guide will help you learn Python step by step.

## Getting Started

First, you need to install Python on your computer.

- Download Python from python.org
- Install the package
- Verify the installation

## Conclusion

Learning Python is a great investment in your career.
        """
        result = self.optimizer.get_seo_score(content, target_keywords=["Python", "programming"])

        assert "total_score" in result
        assert "grade" in result
        assert "breakdown" in result
        assert result["total_score"] >= 0
        assert result["grade"] in ["A", "B", "C", "D", "F"]


class TestQualityValidator:
    """Tests for QualityValidator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = QualityValidator()

    def test_validate_blog_content(self):
        """Test blog content validation."""
        content = """
# Blog Title

## Introduction

This is the introduction paragraph with enough words to pass the length check.
We need to make sure we have sufficient content for a proper blog post.

## Main Content

Here is the main content section with more detailed information.
This section provides value to the reader and covers the topic thoroughly.

## Conclusion

In conclusion, this blog post has covered the main points effectively.
        """ * 5  # Repeat to meet word count

        result = self.validator.validate_content(content, "blog")

        assert "is_valid" in result
        assert "overall_score" in result
        assert "checks" in result

    def test_validate_linkedin_content(self):
        """Test LinkedIn content validation."""
        content = """
Here's what I learned about leadership this week...

Great leaders don't just manage - they inspire.

What's your take on leadership? Share your thoughts below!

#Leadership #Business #Growth
        """
        result = self.validator.validate_content(content, "linkedin")

        assert "is_valid" in result
        assert "checks" in result

    def test_calculate_quality_score(self):
        """Test quality score calculation."""
        content = """
# Quality Content

This is a well-structured piece of content that should score well.
It has proper formatting and engages the reader with questions.

What do you think about this approach?

We believe in providing value to our readers through quality content.
        """
        result = self.validator.calculate_quality_score(content, "blog")

        assert "total_score" in result
        assert "breakdown" in result
        assert "grade" in result
        assert 0 <= result["total_score"] <= 100

    def test_check_brand_voice(self):
        """Test brand voice checking."""
        content = "We are committed to helping you succeed. Together, we can achieve great things."
        guidelines = {
            "tone": "friendly",
            "required_phrases": ["we", "together"],
            "forbidden_phrases": ["must", "required"],
        }

        result = self.validator.check_brand_voice(content, guidelines)

        assert "passed" in result
        assert "matches" in result
        assert "issues" in result


class TestContentExporter:
    """Tests for ContentExporter class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.exporter = ContentExporter()

    def test_export_to_markdown(self):
        """Test Markdown export."""
        content = "# Title\n\nThis is content."
        metadata = {"title": "Test", "author": "AI"}

        result = self.exporter.export_to_markdown(content, metadata)

        assert "---" in result  # Frontmatter
        assert "title: Test" in result
        assert "# Title" in result

    def test_export_to_markdown_no_frontmatter(self):
        """Test Markdown export without frontmatter."""
        content = "# Title\n\nThis is content."

        result = self.exporter.export_to_markdown(content, include_frontmatter=False)

        assert "---" not in result
        assert "# Title" in result

    def test_export_to_html(self):
        """Test HTML export."""
        content = "# Title\n\nThis is a paragraph."

        result = self.exporter.export_to_html(content, title="Test Page")

        assert "<!DOCTYPE html>" in result
        assert "<title>Test Page</title>" in result
        assert "<h1>Title</h1>" in result

    def test_export_to_json(self):
        """Test JSON export."""
        content = "Test content"

        result = self.exporter.export_to_json(content, "blog")

        assert '"content": "Test content"' in result
        assert '"content_type": "blog"' in result
        assert '"word_count":' in result

    def test_export_for_linkedin(self):
        """Test LinkedIn export."""
        content = "**Bold text** and *italic* with [link](https://example.com)\n\n#Hashtag"

        result = self.exporter.export_for_linkedin(content)

        assert "content" in result
        assert "hashtags" in result
        assert "is_within_limit" in result
        assert "#Hashtag" in result["hashtags"]

    def test_create_content_package(self):
        """Test content package creation."""
        content = "# Test\n\nContent here."

        result = self.exporter.create_content_package(
            content, "blog", "Test Title"
        )

        assert "formats" in result
        assert "markdown" in result["formats"]
        assert "html" in result["formats"]
        assert "json" in result["formats"]

    def test_generate_social_snippets(self):
        """Test social snippet generation."""
        content = "This is the first paragraph with important information.\n\nMore content here."

        result = self.exporter.generate_social_snippets(content, "Test Title")

        assert "twitter" in result
        assert "linkedin" in result
        assert "facebook" in result
        assert len(result["twitter"]) <= 280