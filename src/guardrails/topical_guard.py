"""
Topical Guardrail for REACH.


This module implements topical guardrails to restrict the agents
to work only on Real Estate topics using semantic analysis.
"""

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


class TopicalGuard:
    """
    Topical Guardrail that restricts content to Real Estate topics.
    
    Uses semantic analysis to determine if user input is related
    to real estate and blocks off-topic requests.
    """

    # Real estate related keywords and phrases
    REAL_ESTATE_KEYWORDS = [
        # Property types
        "property", "properties", "house", "houses", "home", "homes",
        "apartment", "apartments", "condo", "condominium", "condos",
        "townhouse", "townhome", "villa", "mansion", "estate",
        "duplex", "triplex", "multi-family", "single-family",
        "commercial property", "residential", "industrial",
        "retail space", "office space", "warehouse",
        "land", "lot", "acreage", "plot",
        
        # Real estate actions
        "buy", "buying", "purchase", "purchasing",
        "sell", "selling", "sale", "for sale",
        "rent", "renting", "rental", "lease", "leasing",
        "invest", "investing", "investment",
        "mortgage", "financing", "loan", "down payment",
        "closing", "escrow", "title",
        
        # Real estate professionals
        "realtor", "real estate agent", "broker", "property manager",
        "landlord", "tenant", "buyer", "seller",
        "appraiser", "inspector", "home inspector",
        
        # Real estate concepts
        "real estate", "realty", "housing market",
        "property value", "home value", "appraisal",
        "listing", "mls", "open house",
        "square feet", "sq ft", "sqft", "bedroom", "bathroom",
        "kitchen", "living room", "garage", "backyard",
        "neighborhood", "location", "zoning",
        "hoa", "homeowners association",
        "property tax", "capital gains",
        "appreciation", "depreciation",
        "equity", "refinance", "refinancing",
        "foreclosure", "short sale",
        "first-time buyer", "home buyer",
        "curb appeal", "staging", "renovation",
        "fixer-upper", "move-in ready",
        
        # Marketing for real estate
        "property marketing", "real estate marketing",
        "listing description", "property description",
        "real estate blog", "property blog",
        "real estate content", "property content",
        "real estate social media", "property social",
        "real estate linkedin", "realtor linkedin",
        "property listing", "home listing",
    ]

    # Off-topic indicators (topics to block)
    OFF_TOPIC_INDICATORS = [
        # Technology (non-real estate)
        "programming", "coding", "software development",
        "machine learning", "artificial intelligence",
        "cryptocurrency", "bitcoin", "blockchain",
        "video games", "gaming",
        
        # Entertainment
        "movies", "music", "celebrities", "sports",
        "recipes", "cooking", "food blog",
        
        # Politics
        "politics", "election", "political party",
        "government policy",
        
        # Health (non-real estate)
        "medical advice", "health tips", "diet",
        "exercise routine", "fitness",
        
        # Other industries
        "fashion", "beauty", "makeup",
        "travel destinations", "vacation",
        "automotive", "cars", "vehicles",
    ]

    # Response for off-topic requests
    OFF_TOPIC_RESPONSE = (
        "Sorry! I cannot help you with that topic. "
        "My expertise is in Real Estate. "
        "I can help you with property listings, real estate marketing, "
        "home buying/selling content, property descriptions, "
        "and real estate social media posts."
    )

    def __init__(self, llm_client: Optional[Any] = None):
        """
        Initialize the Topical Guard.
        
        Args:
            llm_client: Optional LLM client for semantic analysis
        """
        self.llm_client = llm_client
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for keyword matching."""
        # Create pattern for real estate keywords
        escaped_keywords = [re.escape(kw) for kw in self.REAL_ESTATE_KEYWORDS]
        self.real_estate_pattern = re.compile(
            r'\b(' + '|'.join(escaped_keywords) + r')\b',
            re.IGNORECASE
        )

        # Create pattern for off-topic indicators
        escaped_off_topic = [re.escape(kw) for kw in self.OFF_TOPIC_INDICATORS]
        self.off_topic_pattern = re.compile(
            r'\b(' + '|'.join(escaped_off_topic) + r')\b',
            re.IGNORECASE
        )

    def check_topic(self, user_input: str) -> dict[str, Any]:
        """
        Check if the user input is related to real estate.
        
        Args:
            user_input: The user's input text
            
        Returns:
            Dictionary with:
                - is_on_topic: Boolean indicating if topic is allowed
                - confidence: Confidence score (0-1)
                - reason: Explanation of the decision
                - matched_keywords: List of matched real estate keywords
        """
        user_input_lower = user_input.lower()

        # Find real estate keyword matches
        real_estate_matches = self.real_estate_pattern.findall(user_input_lower)
        real_estate_score = len(set(real_estate_matches))

        # Find off-topic matches
        off_topic_matches = self.off_topic_pattern.findall(user_input_lower)
        off_topic_score = len(set(off_topic_matches))

        # Calculate confidence
        total_matches = real_estate_score + off_topic_score
        if total_matches == 0:
            # No clear indicators - use semantic analysis if available
            if self.llm_client:
                return self._semantic_topic_check(user_input)
            else:
                # Default to allowing ambiguous requests
                confidence = 0.5
                is_on_topic = True
                reason = "No clear topic indicators found, allowing by default"
        else:
            # Calculate based on keyword matches
            confidence = real_estate_score / total_matches if total_matches > 0 else 0.5
            is_on_topic = real_estate_score > off_topic_score or real_estate_score >= 1

            if is_on_topic:
                reason = f"Found {real_estate_score} real estate keyword(s)"
            else:
                reason = f"Found {off_topic_score} off-topic indicator(s) vs {real_estate_score} real estate keyword(s)"

        return {
            "is_on_topic": is_on_topic,
            "confidence": confidence,
            "reason": reason,
            "matched_keywords": list(set(real_estate_matches)),
            "off_topic_matches": list(set(off_topic_matches)),
        }

    async def _semantic_topic_check(self, user_input: str) -> dict[str, Any]:
        """
        Use LLM for semantic topic analysis.
        
        Args:
            user_input: The user's input text
            
        Returns:
            Dictionary with topic check results
        """
        if not self.llm_client:
            return {
                "is_on_topic": True,
                "confidence": 0.5,
                "reason": "No LLM client for semantic analysis",
                "matched_keywords": [],
                "off_topic_matches": [],
            }

        prompt = f"""Analyze if the following user request is related to Real Estate.

Real Estate topics include:
- Property buying, selling, renting, or investing
- Real estate marketing and content creation
- Property descriptions and listings
- Home improvement for selling
- Real estate market analysis
- Mortgage and financing
- Property management
- Real estate social media and blog content

User Request: "{user_input}"

Respond with ONLY one of these:
- "ON_TOPIC" if the request is related to real estate
- "OFF_TOPIC" if the request is NOT related to real estate

Response:"""

        try:
            response = await self.llm_client.generate(prompt, temperature=0.1, max_tokens=20)

            if hasattr(response, 'content'):
                result = response.content.strip().upper()
            else:
                result = str(response).strip().upper()

            is_on_topic = "ON_TOPIC" in result

            return {
                "is_on_topic": is_on_topic,
                "confidence": 0.85 if is_on_topic else 0.85,
                "reason": "Semantic analysis determined topic relevance",
                "matched_keywords": [],
                "off_topic_matches": [],
            }

        except Exception as e:
            logger.error(f"Semantic topic check failed: {str(e)}")
            # Default to allowing on error
            return {
                "is_on_topic": True,
                "confidence": 0.5,
                "reason": f"Semantic analysis failed: {str(e)}",
                "matched_keywords": [],
                "off_topic_matches": [],
            }

    async def validate(self, user_input: str) -> dict[str, Any]:
        """
        Validate user input against topical guardrails.
        
        Args:
            user_input: The user's input text
            
        Returns:
            Dictionary with:
                - passed: Boolean indicating if validation passed
                - message: Response message (off-topic message if blocked)
                - details: Detailed check results
        """
        # First do keyword-based check
        check_result = self.check_topic(user_input)

        # If ambiguous and LLM available, do semantic check
        if check_result["confidence"] < 0.6 and self.llm_client:
            check_result = await self._semantic_topic_check(user_input)

        if check_result["is_on_topic"]:
            return {
                "passed": True,
                "message": None,
                "details": check_result,
            }
        else:
            logger.info(f"Blocked off-topic request: {user_input[:100]}...")
            return {
                "passed": False,
                "message": self.OFF_TOPIC_RESPONSE,
                "details": check_result,
            }

    def get_topic_suggestions(self) -> list[str]:
        """
        Get suggestions for on-topic requests.
        
        Returns:
            List of example real estate topics
        """
        return [
            "Write a property listing description for a 3-bedroom house",
            "Create a LinkedIn post about home buying tips",
            "Research current real estate market trends",
            "Generate a blog post about first-time home buyers",
            "Create marketing content for a luxury condo",
            "Write about mortgage rates and financing options",
            "Create social media content for a real estate agent",
            "Generate an image for a property listing",
        ]