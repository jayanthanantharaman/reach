"""
Safety Guardrail for REACH.


This module implements safety guardrails to block profanity
and inappropriate content using semantic analysis.
"""

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SafetyGuard:
    """
    Safety Guardrail that blocks profanity and inappropriate content.
    
    Uses both keyword matching and semantic analysis to detect
    and block harmful, offensive, or inappropriate content.
    """

    # Profanity and offensive words (basic list - can be extended)
    PROFANITY_WORDS = [
        # Common profanity (censored for code readability)
        "fuck", "fucking", "fucked", "fucker", "fck",
        "shit", "shitty", "bullshit",
        "asshole", "arse",  # Note: "ass" removed due to false positives (class, glass, grass, etc.)
        "bitch", "bitchy",
        "bastard",
        "dickhead",
        "piss", "pissed off",
        "whore", "slut",
        "cunt",
        # Slurs and hate speech indicators
        "racist", "racism",
        "sexist", "sexism",
        "homophobic", "homophobia",
        "nazi", "fascist",
        # Violence indicators (only explicit violence)
        "murder", "terrorist", "terrorism",
        "gun violence",
        "self-harm",
    ]

    # Words that are safe even though they contain profanity substrings
    # These are legitimate words that should NOT trigger the filter
    SAFE_WORDS = [
        # Words containing "ass"
        "class", "classes", "classic", "classical", "classify", "classification",
        "glass", "glasses", "glassware", "fiberglass",
        "grass", "grassy", "grassland",
        "pass", "passed", "passing", "passage", "passenger", "passport",
        "mass", "massive", "massage",
        "bass", "bassist",
        "brass", "brassy",
        "assess", "assessment", "assessor",
        "assist", "assistant", "assistance",
        "associate", "associated", "association",
        "assume", "assumed", "assumption",
        "assure", "assured", "assurance",
        "asset", "assets",
        "assign", "assigned", "assignment",
        "assemble", "assembled", "assembly",
        "assert", "assertion", "assertive",
        "cassette", "casserole",
        "embassy", "embarrass", "embarrassed", "embarrassing",
        "harass", "harassment",
        "compass", "compassion", "compassionate",
        "trespass", "trespassing",
        "surpass", "surpassed",
        "bypass", "bypassed",
        "overpass", "underpass",
        "sassafras", "sassy",
        # Words containing "hell"
        "hello", "shell", "shells", "shellfish", "seashell",
        "dwell", "dwelling", "farewell",
        "michelle", "rochelle", "campbell",
        "hellenistic", "hellenic",
        # Words containing "damn"
        "amsterdam", "goddamn",
        # Words containing "dick"
        "dickens", "edickt", "predict", "prediction", "verdict",
        # Words containing "cock"
        "peacock", "hancock", "cockpit", "cocktail",
        # Words containing "piss"
        "mississippi",
        # Words containing "crap"
        "scrap", "scrape", "scraps",
    ]

    # Inappropriate content categories
    INAPPROPRIATE_CATEGORIES = [
        # Adult content
        "pornography", "porn", "xxx",
        "nude", "nudity", "naked",
        "sexually explicit", "erotic",
        
        # Violence
        "gore", "gory", "gruesome",
        "torture", "torturing",
        
        # Illegal activities
        "cocaine", "heroin", "meth",
        "fraud", "scam", "phishing",
        "hacking", "malware",
        
        # Discrimination
        "hate speech", "hateful",
        "derogatory",
    ]

    # Image-specific inappropriate content
    IMAGE_INAPPROPRIATE = [
        "nude", "naked", "explicit",
        "gore", "gory", "bloody",
        "violent", "violence",
        "weapon", "gun", "knife",
        "drug", "drugs",
        "offensive", "inappropriate",
        "adult", "xxx", "porn",
        "disturbing", "graphic",
    ]

    # Response for blocked content
    BLOCKED_RESPONSE = (
        "I cannot help create content with profanity, offensive language, "
        "or inappropriate material. Please rephrase your request using "
        "professional and appropriate language."
    )

    BLOCKED_IMAGE_RESPONSE = (
        "I cannot generate images containing inappropriate, offensive, "
        "violent, or explicit content. Please describe a professional "
        "and appropriate image for your real estate needs."
    )

    def __init__(self, llm_client: Optional[Any] = None, strict_mode: bool = True):
        """
        Initialize the Safety Guard.
        
        Args:
            llm_client: Optional LLM client for semantic analysis
            strict_mode: If True, use stricter content filtering
        """
        self.llm_client = llm_client
        self.strict_mode = strict_mode
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for content matching."""
        # Profanity pattern
        escaped_profanity = [re.escape(word) for word in self.PROFANITY_WORDS]
        self.profanity_pattern = re.compile(
            r'\b(' + '|'.join(escaped_profanity) + r')\b',
            re.IGNORECASE
        )

        # Inappropriate content pattern
        escaped_inappropriate = [re.escape(cat) for cat in self.INAPPROPRIATE_CATEGORIES]
        self.inappropriate_pattern = re.compile(
            r'\b(' + '|'.join(escaped_inappropriate) + r')\b',
            re.IGNORECASE
        )

        # Image inappropriate pattern
        escaped_image = [re.escape(word) for word in self.IMAGE_INAPPROPRIATE]
        self.image_inappropriate_pattern = re.compile(
            r'\b(' + '|'.join(escaped_image) + r')\b',
            re.IGNORECASE
        )

        # Leetspeak and obfuscation patterns
        self.leetspeak_patterns = [
            (r'f[u\*@0]ck', 'fuck'),
            (r'sh[i\*1]t', 'shit'),
            (r'b[i\*1]tch', 'bitch'),
            (r'a[s\$]s', 'ass'),
            (r'd[i\*1]ck', 'dick'),
            (r'c[u\*]nt', 'cunt'),
        ]

    def _check_leetspeak(self, text: str) -> list[str]:
        """
        Check for leetspeak/obfuscated profanity.
        
        Args:
            text: Text to check
            
        Returns:
            List of detected obfuscated words
        """
        detected = []
        text_lower = text.lower()

        for pattern, word in self.leetspeak_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                detected.append(word)

        return detected

    def check_profanity(self, text: str) -> dict[str, Any]:
        """
        Check text for profanity and offensive content.
        
        Args:
            text: Text to check
            
        Returns:
            Dictionary with:
                - has_profanity: Boolean indicating if profanity found
                - profanity_words: List of detected profanity
                - severity: Severity level (low, medium, high)
        """
        text_lower = text.lower()

        # Direct profanity matches
        profanity_matches = self.profanity_pattern.findall(text_lower)

        # Leetspeak matches
        leetspeak_matches = self._check_leetspeak(text)

        # Combine all matches
        all_matches = list(set(profanity_matches + leetspeak_matches))

        # Determine severity
        if len(all_matches) == 0:
            severity = "none"
        elif len(all_matches) <= 1:
            severity = "low"
        elif len(all_matches) <= 3:
            severity = "medium"
        else:
            severity = "high"

        return {
            "has_profanity": len(all_matches) > 0,
            "profanity_words": all_matches,
            "severity": severity,
        }

    def check_inappropriate_content(self, text: str) -> dict[str, Any]:
        """
        Check text for inappropriate content categories.
        
        Args:
            text: Text to check
            
        Returns:
            Dictionary with:
                - has_inappropriate: Boolean indicating if inappropriate content found
                - categories: List of detected inappropriate categories
                - severity: Severity level
        """
        text_lower = text.lower()

        # Find inappropriate content matches
        inappropriate_matches = self.inappropriate_pattern.findall(text_lower)
        unique_matches = list(set(inappropriate_matches))

        # Determine severity based on category type
        high_severity_words = ["porn", "nude", "gore", "terrorist", "suicide", "self-harm"]
        has_high_severity = any(word in text_lower for word in high_severity_words)

        if len(unique_matches) == 0:
            severity = "none"
        elif has_high_severity:
            severity = "high"
        elif len(unique_matches) <= 2:
            severity = "medium"
        else:
            severity = "high"

        return {
            "has_inappropriate": len(unique_matches) > 0,
            "categories": unique_matches,
            "severity": severity,
        }

    def check_image_prompt(self, prompt: str) -> dict[str, Any]:
        """
        Check image generation prompt for inappropriate content.
        
        Args:
            prompt: Image generation prompt
            
        Returns:
            Dictionary with safety check results
        """
        prompt_lower = prompt.lower()

        # Check for inappropriate image content
        image_matches = self.image_inappropriate_pattern.findall(prompt_lower)
        unique_matches = list(set(image_matches))

        # Also check profanity
        profanity_result = self.check_profanity(prompt)

        # Combine results
        all_issues = unique_matches + profanity_result.get("profanity_words", [])

        return {
            "is_safe": len(all_issues) == 0,
            "issues": list(set(all_issues)),
            "profanity": profanity_result,
            "inappropriate_content": unique_matches,
        }

    async def semantic_safety_check(self, text: str) -> dict[str, Any]:
        """
        Use LLM for semantic safety analysis.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with semantic safety results
        """
        if not self.llm_client:
            return {
                "is_safe": True,
                "confidence": 0.5,
                "reason": "No LLM client for semantic analysis",
            }

        prompt = f"""Analyze the following text for safety issues.

Check for:
1. Profanity or offensive language (even if disguised or misspelled)
2. Hate speech or discrimination
3. Violence or threats
4. Adult/explicit content
5. Illegal activities
6. Harmful or dangerous content

Text to analyze: "{text}"

Respond with ONLY one of these:
- "SAFE" if the text is appropriate and professional
- "UNSAFE" if the text contains any of the above issues

Response:"""

        try:
            response = await self.llm_client.generate(prompt, temperature=0.1, max_tokens=20)

            if hasattr(response, 'content'):
                result = response.content.strip().upper()
            else:
                result = str(response).strip().upper()

            is_safe = "SAFE" in result and "UNSAFE" not in result

            return {
                "is_safe": is_safe,
                "confidence": 0.9,
                "reason": "Semantic analysis completed",
            }

        except Exception as e:
            logger.error(f"Semantic safety check failed: {str(e)}")
            return {
                "is_safe": True,
                "confidence": 0.5,
                "reason": f"Semantic analysis failed: {str(e)}",
            }

    async def validate_text(self, text: str) -> dict[str, Any]:
        """
        Validate text content for safety.
        
        Args:
            text: Text to validate
            
        Returns:
            Dictionary with:
                - passed: Boolean indicating if validation passed
                - message: Response message if blocked
                - details: Detailed check results
        """
        # Check profanity
        profanity_result = self.check_profanity(text)

        # Check inappropriate content
        inappropriate_result = self.check_inappropriate_content(text)

        # Combine results
        has_issues = (
            profanity_result["has_profanity"] or
            inappropriate_result["has_inappropriate"]
        )

        # If no keyword issues but strict mode, do semantic check
        if not has_issues and self.strict_mode and self.llm_client:
            semantic_result = await self.semantic_safety_check(text)
            if not semantic_result["is_safe"]:
                has_issues = True

        if has_issues:
            logger.warning(f"Blocked unsafe content: profanity={profanity_result['profanity_words']}, inappropriate={inappropriate_result['categories']}")
            return {
                "passed": False,
                "message": self.BLOCKED_RESPONSE,
                "details": {
                    "profanity": profanity_result,
                    "inappropriate": inappropriate_result,
                },
            }

        return {
            "passed": True,
            "message": None,
            "details": {
                "profanity": profanity_result,
                "inappropriate": inappropriate_result,
            },
        }

    async def validate_image_prompt(self, prompt: str) -> dict[str, Any]:
        """
        Validate image generation prompt for safety.
        
        Args:
            prompt: Image generation prompt
            
        Returns:
            Dictionary with validation results
        """
        # Check image-specific safety
        image_result = self.check_image_prompt(prompt)

        # If no keyword issues but strict mode, do semantic check
        if image_result["is_safe"] and self.strict_mode and self.llm_client:
            semantic_result = await self.semantic_safety_check(prompt)
            if not semantic_result["is_safe"]:
                image_result["is_safe"] = False

        if not image_result["is_safe"]:
            logger.warning(f"Blocked unsafe image prompt: {image_result['issues']}")
            return {
                "passed": False,
                "message": self.BLOCKED_IMAGE_RESPONSE,
                "details": image_result,
            }

        return {
            "passed": True,
            "message": None,
            "details": image_result,
        }

    async def validate(
        self,
        content: str,
        content_type: str = "text",
    ) -> dict[str, Any]:
        """
        Validate content for safety based on type.
        
        Args:
            content: Content to validate
            content_type: Type of content ("text" or "image")
            
        Returns:
            Dictionary with validation results
        """
        if content_type == "image":
            return await self.validate_image_prompt(content)
        else:
            return await self.validate_text(content)

    def sanitize_text(self, text: str) -> str:
        """
        Sanitize text by replacing profanity with asterisks.
        
        Args:
            text: Text to sanitize
            
        Returns:
            Sanitized text
        """
        def replace_with_asterisks(match):
            word = match.group(0)
            if len(word) <= 2:
                return '*' * len(word)
            return word[0] + '*' * (len(word) - 2) + word[-1]

        return self.profanity_pattern.sub(replace_with_asterisks, text)