"""
Quality Validation utilities for REACH.


This module provides tools for validating content quality
and ensuring it meets predefined standards.
"""

import re
from typing import Any, Optional


class QualityValidator:
    """
    Content quality validation utilities.
    
    This class provides:
    - Content quality scoring
    - Plagiarism-like pattern detection
    - Brand voice consistency checking
    - Content completeness validation
    """

    # Quality thresholds
    MIN_BLOG_WORDS = 500
    MIN_LINKEDIN_CHARS = 100
    MAX_LINKEDIN_CHARS = 3000
    MIN_QUALITY_SCORE = 0.7

    def __init__(self):
        """Initialize the quality validator."""
        pass

    def validate_content(
        self,
        content: str,
        content_type: str = "blog",
        requirements: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Validate content against quality standards.
        
        Args:
            content: Content to validate
            content_type: Type of content (blog, linkedin, etc.)
            requirements: Optional specific requirements
            
        Returns:
            Dictionary with validation results
        """
        requirements = requirements or {}

        # Run all validations
        length_check = self._validate_length(content, content_type, requirements)
        structure_check = self._validate_structure(content, content_type)
        quality_check = self._validate_quality_indicators(content)
        completeness_check = self._validate_completeness(content, content_type)

        # Calculate overall score
        checks = [length_check, structure_check, quality_check, completeness_check]
        passed_checks = sum(1 for c in checks if c["passed"])
        overall_score = passed_checks / len(checks)

        # Determine if content passes
        is_valid = overall_score >= self.MIN_QUALITY_SCORE

        return {
            "is_valid": is_valid,
            "overall_score": round(overall_score, 2),
            "checks": {
                "length": length_check,
                "structure": structure_check,
                "quality": quality_check,
                "completeness": completeness_check,
            },
            "issues": self._collect_issues(checks),
            "suggestions": self._generate_suggestions(checks, content_type),
        }

    def _validate_length(
        self,
        content: str,
        content_type: str,
        requirements: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate content length."""
        word_count = len(content.split())
        char_count = len(content)

        if content_type == "blog":
            min_words = requirements.get("min_words", self.MIN_BLOG_WORDS)
            passed = word_count >= min_words
            message = f"Word count: {word_count} (minimum: {min_words})"
        elif content_type == "linkedin":
            passed = self.MIN_LINKEDIN_CHARS <= char_count <= self.MAX_LINKEDIN_CHARS
            message = f"Character count: {char_count} (range: {self.MIN_LINKEDIN_CHARS}-{self.MAX_LINKEDIN_CHARS})"
        else:
            passed = word_count >= 50
            message = f"Word count: {word_count}"

        return {
            "name": "Length Check",
            "passed": passed,
            "message": message,
            "details": {
                "word_count": word_count,
                "char_count": char_count,
            },
        }

    def _validate_structure(
        self,
        content: str,
        content_type: str,
    ) -> dict[str, Any]:
        """Validate content structure."""
        issues = []

        if content_type == "blog":
            # Check for headings
            has_h1 = bool(re.search(r'^#\s+', content, re.MULTILINE))
            has_h2 = bool(re.search(r'^##\s+', content, re.MULTILINE))

            if not has_h1:
                issues.append("Missing main heading (H1)")
            if not has_h2:
                issues.append("Missing subheadings (H2)")

            # Check for paragraphs
            paragraphs = [p for p in content.split('\n\n') if p.strip()]
            if len(paragraphs) < 3:
                issues.append("Content should have at least 3 paragraphs")

        elif content_type == "linkedin":
            # Check for hook (first line should be engaging)
            lines = content.strip().split('\n')
            if lines and len(lines[0]) < 20:
                issues.append("Opening hook may be too short")

            # Check for call-to-action
            cta_patterns = [r'\?$', r'comment', r'share', r'thoughts', r'agree']
            has_cta = any(
                re.search(pattern, content.lower())
                for pattern in cta_patterns
            )
            if not has_cta:
                issues.append("Consider adding a call-to-action")

        passed = len(issues) == 0

        return {
            "name": "Structure Check",
            "passed": passed,
            "message": "Structure is valid" if passed else f"Found {len(issues)} structure issue(s)",
            "issues": issues,
        }

    def _validate_quality_indicators(self, content: str) -> dict[str, Any]:
        """Validate quality indicators in content."""
        issues = []
        warnings = []

        # Check for repetitive content
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip().lower() for s in sentences if s.strip()]

        if len(sentences) != len(set(sentences)):
            warnings.append("Possible repetitive sentences detected")

        # Check for filler words
        filler_patterns = [
            r'\bvery\s+very\b',
            r'\breally\s+really\b',
            r'\bjust\s+just\b',
        ]
        for pattern in filler_patterns:
            if re.search(pattern, content.lower()):
                warnings.append("Excessive filler words detected")
                break

        # Check for incomplete sentences
        incomplete_patterns = [
            r'\.\s*\.\s*\.',  # Multiple periods
            r'\s{3,}',  # Multiple spaces
        ]
        for pattern in incomplete_patterns:
            if re.search(pattern, content):
                issues.append("Possible incomplete or malformed content")
                break

        # Check for placeholder text
        placeholder_patterns = [
            r'\[.*?\]',  # Bracketed placeholders
            r'lorem ipsum',
            r'TODO',
            r'FIXME',
        ]
        for pattern in placeholder_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                issues.append("Placeholder text detected")
                break

        passed = len(issues) == 0

        return {
            "name": "Quality Indicators",
            "passed": passed,
            "message": "Quality indicators pass" if passed else f"Found {len(issues)} quality issue(s)",
            "issues": issues,
            "warnings": warnings,
        }

    def _validate_completeness(
        self,
        content: str,
        content_type: str,
    ) -> dict[str, Any]:
        """Validate content completeness."""
        issues = []

        if content_type == "blog":
            # Check for introduction
            paragraphs = [p for p in content.split('\n\n') if p.strip()]
            if paragraphs:
                first_para = paragraphs[0]
                if len(first_para.split()) < 30:
                    issues.append("Introduction may be too brief")

            # Check for conclusion
            if paragraphs:
                last_para = paragraphs[-1]
                conclusion_indicators = ['conclusion', 'summary', 'finally', 'in closing']
                has_conclusion = any(
                    indicator in last_para.lower()
                    for indicator in conclusion_indicators
                )
                if not has_conclusion and len(last_para.split()) < 30:
                    issues.append("Content may be missing a proper conclusion")

        elif content_type == "linkedin":
            # Check for hashtags
            if '#' not in content:
                issues.append("Consider adding relevant hashtags")

        passed = len(issues) == 0

        return {
            "name": "Completeness Check",
            "passed": passed,
            "message": "Content appears complete" if passed else f"Found {len(issues)} completeness issue(s)",
            "issues": issues,
        }

    def _collect_issues(self, checks: list[dict[str, Any]]) -> list[str]:
        """Collect all issues from checks."""
        issues = []
        for check in checks:
            if "issues" in check:
                issues.extend(check["issues"])
        return issues

    def _generate_suggestions(
        self,
        checks: list[dict[str, Any]],
        content_type: str,
    ) -> list[str]:
        """Generate improvement suggestions."""
        suggestions = []

        for check in checks:
            if not check["passed"]:
                if check["name"] == "Length Check":
                    if content_type == "blog":
                        suggestions.append("Add more content to reach the minimum word count")
                    elif content_type == "linkedin":
                        suggestions.append("Adjust content length to fit LinkedIn's optimal range")

                elif check["name"] == "Structure Check":
                    if content_type == "blog":
                        suggestions.append("Add proper headings (H1, H2) to structure your content")
                    elif content_type == "linkedin":
                        suggestions.append("Start with a strong hook and end with a call-to-action")

                elif check["name"] == "Quality Indicators":
                    suggestions.append("Review and remove any placeholder or repetitive content")

                elif check["name"] == "Completeness Check":
                    suggestions.append("Ensure your content has a clear introduction and conclusion")

        return suggestions

    def calculate_quality_score(
        self,
        content: str,
        content_type: str = "blog",
    ) -> dict[str, Any]:
        """
        Calculate a detailed quality score.
        
        Args:
            content: Content to score
            content_type: Type of content
            
        Returns:
            Dictionary with quality score breakdown
        """
        scores = {}

        # Length score (0-25)
        word_count = len(content.split())
        if content_type == "blog":
            if word_count >= 1500:
                scores["length"] = 25
            elif word_count >= 1000:
                scores["length"] = 20
            elif word_count >= 500:
                scores["length"] = 15
            else:
                scores["length"] = 10
        else:
            char_count = len(content)
            if 150 <= char_count <= 2500:
                scores["length"] = 25
            elif 100 <= char_count <= 3000:
                scores["length"] = 20
            else:
                scores["length"] = 10

        # Structure score (0-25)
        validation = self.validate_content(content, content_type)
        structure_passed = validation["checks"]["structure"]["passed"]
        scores["structure"] = 25 if structure_passed else 10

        # Originality score (0-25) - based on lexical diversity
        words = content.lower().split()
        unique_words = set(words)
        diversity = len(unique_words) / len(words) if words else 0
        scores["originality"] = min(25, int(diversity * 50))

        # Engagement score (0-25)
        engagement_indicators = [
            r'\?',  # Questions
            r'!',  # Exclamations
            r'\byou\b',  # Direct address
            r'\bwe\b',  # Inclusive language
        ]
        engagement_count = sum(
            1 for pattern in engagement_indicators
            if re.search(pattern, content, re.IGNORECASE)
        )
        scores["engagement"] = min(25, engagement_count * 7)

        total_score = sum(scores.values())

        return {
            "total_score": total_score,
            "max_score": 100,
            "percentage": round(total_score / 100 * 100, 1),
            "breakdown": scores,
            "grade": self._get_grade(total_score),
        }

    def _get_grade(self, score: int) -> str:
        """Get letter grade from score."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def check_brand_voice(
        self,
        content: str,
        brand_guidelines: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Check content against brand voice guidelines.
        
        Args:
            content: Content to check
            brand_guidelines: Brand voice guidelines
            
        Returns:
            Dictionary with brand voice analysis
        """
        issues = []
        matches = []

        # Check for required phrases
        required_phrases = brand_guidelines.get("required_phrases", [])
        for phrase in required_phrases:
            if phrase.lower() in content.lower():
                matches.append(f"Contains required phrase: '{phrase}'")
            else:
                issues.append(f"Missing required phrase: '{phrase}'")

        # Check for forbidden phrases
        forbidden_phrases = brand_guidelines.get("forbidden_phrases", [])
        for phrase in forbidden_phrases:
            if phrase.lower() in content.lower():
                issues.append(f"Contains forbidden phrase: '{phrase}'")

        # Check tone indicators
        tone = brand_guidelines.get("tone", "professional")
        tone_check = self._check_tone(content, tone)
        if not tone_check["matches"]:
            issues.append(f"Tone may not match '{tone}' guidelines")

        passed = len(issues) == 0

        return {
            "passed": passed,
            "matches": matches,
            "issues": issues,
            "tone_analysis": tone_check,
        }

    def _check_tone(self, content: str, expected_tone: str) -> dict[str, Any]:
        """Check if content matches expected tone."""
        tone_indicators = {
            "professional": {
                "positive": ["therefore", "consequently", "furthermore", "regarding"],
                "negative": ["gonna", "wanna", "kinda", "lol", "omg"],
            },
            "casual": {
                "positive": ["hey", "awesome", "cool", "great"],
                "negative": ["hereby", "pursuant", "aforementioned"],
            },
            "friendly": {
                "positive": ["you", "we", "together", "help", "support"],
                "negative": ["must", "required", "mandatory", "failure"],
            },
        }

        indicators = tone_indicators.get(expected_tone, tone_indicators["professional"])
        content_lower = content.lower()

        positive_matches = sum(
            1 for word in indicators["positive"]
            if word in content_lower
        )
        negative_matches = sum(
            1 for word in indicators["negative"]
            if word in content_lower
        )

        matches = positive_matches > negative_matches

        return {
            "expected_tone": expected_tone,
            "matches": matches,
            "positive_indicators": positive_matches,
            "negative_indicators": negative_matches,
        }