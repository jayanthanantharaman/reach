"""
Content Optimization utilities for REACH.


This module provides tools for optimizing content for SEO,
readability, and engagement.
"""

import re
from collections import Counter
from typing import Any, Optional


class ContentOptimizer:
    """
    Content optimization utilities for SEO and readability.
    
    This class provides:
    - Keyword optimization analysis
    - Readability scoring
    - Content structure analysis
    - SEO recommendations
    """

    # Common stop words to exclude from keyword analysis
    STOP_WORDS = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
        "be", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "must", "shall", "can", "need",
        "this", "that", "these", "those", "i", "you", "he", "she", "it",
        "we", "they", "what", "which", "who", "whom", "when", "where", "why",
        "how", "all", "each", "every", "both", "few", "more", "most", "other",
        "some", "such", "no", "nor", "not", "only", "own", "same", "so",
        "than", "too", "very", "just", "also", "now", "here", "there",
    }

    def __init__(self):
        """Initialize the content optimizer."""
        pass

    def analyze_keywords(
        self,
        content: str,
        target_keywords: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Analyze keyword usage in content.
        
        Args:
            content: Content to analyze
            target_keywords: Optional list of target keywords
            
        Returns:
            Dictionary with keyword analysis results
        """
        # Clean and tokenize content
        words = self._tokenize(content)
        word_count = len(words)

        # Count word frequencies
        word_freq = Counter(words)

        # Get top keywords (excluding stop words)
        top_keywords = [
            (word, count)
            for word, count in word_freq.most_common(20)
            if word.lower() not in self.STOP_WORDS and len(word) > 2
        ][:10]

        # Analyze target keywords if provided
        target_analysis = []
        if target_keywords:
            content_lower = content.lower()
            for keyword in target_keywords:
                keyword_lower = keyword.lower()
                count = content_lower.count(keyword_lower)
                density = (count / word_count * 100) if word_count > 0 else 0

                # Check keyword placement
                in_first_100 = keyword_lower in content_lower[:500]
                in_headings = self._keyword_in_headings(content, keyword)

                target_analysis.append({
                    "keyword": keyword,
                    "count": count,
                    "density": round(density, 2),
                    "in_first_paragraph": in_first_100,
                    "in_headings": in_headings,
                    "status": self._get_keyword_status(density),
                })

        return {
            "word_count": word_count,
            "top_keywords": top_keywords,
            "target_keyword_analysis": target_analysis,
            "unique_words": len(set(words)),
            "lexical_diversity": round(len(set(words)) / word_count, 2) if word_count > 0 else 0,
        }

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into words."""
        # Remove special characters and split
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        return words

    def _keyword_in_headings(self, content: str, keyword: str) -> bool:
        """Check if keyword appears in headings."""
        # Find markdown headings
        headings = re.findall(r'^#{1,6}\s+(.+)$', content, re.MULTILINE)
        keyword_lower = keyword.lower()
        return any(keyword_lower in heading.lower() for heading in headings)

    def _get_keyword_status(self, density: float) -> str:
        """Get keyword density status."""
        if density < 0.5:
            return "low"
        elif density > 3.0:
            return "high"
        else:
            return "optimal"

    def analyze_readability(self, content: str) -> dict[str, Any]:
        """
        Analyze content readability.
        
        Args:
            content: Content to analyze
            
        Returns:
            Dictionary with readability metrics
        """
        # Split into sentences
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]

        # Split into words
        words = self._tokenize(content)

        # Calculate metrics
        word_count = len(words)
        sentence_count = len(sentences)
        avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0

        # Count syllables (simplified)
        syllable_count = sum(self._count_syllables(word) for word in words)
        avg_syllables = syllable_count / word_count if word_count > 0 else 0

        # Calculate Flesch Reading Ease (simplified)
        flesch_score = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables)
        flesch_score = max(0, min(100, flesch_score))

        # Determine reading level
        reading_level = self._get_reading_level(flesch_score)

        # Analyze paragraph structure
        paragraphs = content.split('\n\n')
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        return {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "paragraph_count": len(paragraphs),
            "avg_sentence_length": round(avg_sentence_length, 1),
            "avg_syllables_per_word": round(avg_syllables, 2),
            "flesch_reading_ease": round(flesch_score, 1),
            "reading_level": reading_level,
            "recommendations": self._get_readability_recommendations(
                avg_sentence_length, flesch_score, paragraphs
            ),
        }

    def _count_syllables(self, word: str) -> int:
        """Count syllables in a word (simplified)."""
        word = word.lower()
        count = 0
        vowels = "aeiouy"
        prev_vowel = False

        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_vowel:
                count += 1
            prev_vowel = is_vowel

        # Handle silent e
        if word.endswith('e'):
            count -= 1

        return max(1, count)

    def _get_reading_level(self, flesch_score: float) -> str:
        """Get reading level from Flesch score."""
        if flesch_score >= 90:
            return "Very Easy (5th grade)"
        elif flesch_score >= 80:
            return "Easy (6th grade)"
        elif flesch_score >= 70:
            return "Fairly Easy (7th grade)"
        elif flesch_score >= 60:
            return "Standard (8th-9th grade)"
        elif flesch_score >= 50:
            return "Fairly Difficult (10th-12th grade)"
        elif flesch_score >= 30:
            return "Difficult (College)"
        else:
            return "Very Difficult (College Graduate)"

    def _get_readability_recommendations(
        self,
        avg_sentence_length: float,
        flesch_score: float,
        paragraphs: list[str],
    ) -> list[str]:
        """Generate readability recommendations."""
        recommendations = []

        if avg_sentence_length > 25:
            recommendations.append(
                "Consider breaking up long sentences. Aim for 15-20 words per sentence."
            )

        if flesch_score < 50:
            recommendations.append(
                "Content may be difficult to read. Try using simpler words and shorter sentences."
            )

        long_paragraphs = [p for p in paragraphs if len(p.split()) > 100]
        if long_paragraphs:
            recommendations.append(
                f"Found {len(long_paragraphs)} long paragraph(s). Consider breaking them up for better readability."
            )

        return recommendations

    def analyze_structure(self, content: str) -> dict[str, Any]:
        """
        Analyze content structure.
        
        Args:
            content: Content to analyze
            
        Returns:
            Dictionary with structure analysis
        """
        # Find headings
        h1_matches = re.findall(r'^#\s+(.+)$', content, re.MULTILINE)
        h2_matches = re.findall(r'^##\s+(.+)$', content, re.MULTILINE)
        h3_matches = re.findall(r'^###\s+(.+)$', content, re.MULTILINE)

        # Find lists
        bullet_lists = re.findall(r'^[-*]\s+.+$', content, re.MULTILINE)
        numbered_lists = re.findall(r'^\d+\.\s+.+$', content, re.MULTILINE)

        # Find links
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)

        # Find images
        images = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', content)

        # Check for meta description
        has_meta = "meta description:" in content.lower() or "**meta" in content.lower()

        return {
            "headings": {
                "h1_count": len(h1_matches),
                "h2_count": len(h2_matches),
                "h3_count": len(h3_matches),
                "h1_titles": h1_matches,
                "h2_titles": h2_matches,
            },
            "lists": {
                "bullet_items": len(bullet_lists),
                "numbered_items": len(numbered_lists),
            },
            "links": {
                "count": len(links),
                "links": links[:10],  # First 10 links
            },
            "images": {
                "count": len(images),
                "images": images,
            },
            "has_meta_description": has_meta,
            "recommendations": self._get_structure_recommendations(
                h1_matches, h2_matches, bullet_lists, links
            ),
        }

    def _get_structure_recommendations(
        self,
        h1_matches: list,
        h2_matches: list,
        bullet_lists: list,
        links: list,
    ) -> list[str]:
        """Generate structure recommendations."""
        recommendations = []

        if len(h1_matches) == 0:
            recommendations.append("Add an H1 heading (title) to your content.")
        elif len(h1_matches) > 1:
            recommendations.append("Consider having only one H1 heading per page.")

        if len(h2_matches) < 2:
            recommendations.append(
                "Add more H2 subheadings to break up content and improve scannability."
            )

        if len(bullet_lists) == 0:
            recommendations.append(
                "Consider adding bullet points or lists to improve readability."
            )

        if len(links) == 0:
            recommendations.append(
                "Add internal or external links to provide additional value."
            )

        return recommendations

    def get_seo_score(
        self,
        content: str,
        target_keywords: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        Calculate overall SEO score.
        
        Args:
            content: Content to analyze
            target_keywords: Optional target keywords
            
        Returns:
            Dictionary with SEO score and breakdown
        """
        keyword_analysis = self.analyze_keywords(content, target_keywords)
        readability = self.analyze_readability(content)
        structure = self.analyze_structure(content)

        # Calculate component scores
        scores = {}

        # Word count score (0-20)
        word_count = keyword_analysis["word_count"]
        if word_count >= 1500:
            scores["word_count"] = 20
        elif word_count >= 1000:
            scores["word_count"] = 15
        elif word_count >= 500:
            scores["word_count"] = 10
        else:
            scores["word_count"] = 5

        # Keyword score (0-25)
        if target_keywords and keyword_analysis["target_keyword_analysis"]:
            optimal_keywords = sum(
                1 for k in keyword_analysis["target_keyword_analysis"]
                if k["status"] == "optimal"
            )
            scores["keywords"] = min(25, optimal_keywords * 8)
        else:
            scores["keywords"] = 10

        # Readability score (0-20)
        flesch = readability["flesch_reading_ease"]
        if 50 <= flesch <= 70:
            scores["readability"] = 20
        elif 40 <= flesch <= 80:
            scores["readability"] = 15
        else:
            scores["readability"] = 10

        # Structure score (0-20)
        h2_count = structure["headings"]["h2_count"]
        has_lists = structure["lists"]["bullet_items"] > 0
        has_links = structure["links"]["count"] > 0

        scores["structure"] = 0
        if h2_count >= 3:
            scores["structure"] += 8
        elif h2_count >= 1:
            scores["structure"] += 4
        if has_lists:
            scores["structure"] += 6
        if has_links:
            scores["structure"] += 6

        # Meta score (0-15)
        scores["meta"] = 15 if structure["has_meta_description"] else 5

        total_score = sum(scores.values())

        return {
            "total_score": total_score,
            "max_score": 100,
            "grade": self._get_seo_grade(total_score),
            "breakdown": scores,
            "recommendations": (
                keyword_analysis.get("recommendations", []) +
                readability.get("recommendations", []) +
                structure.get("recommendations", [])
            ),
        }

    def _get_seo_grade(self, score: int) -> str:
        """Get letter grade from SEO score."""
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