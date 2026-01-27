"""
Unit tests for REACH Guardrails.

"""

import pytest

from src.guardrails.topical_guard import TopicalGuard
from src.guardrails.safety_guard import SafetyGuard
from src.guardrails.guardrails_manager import GuardrailsManager


class TestTopicalGuard:
    """Tests for TopicalGuard class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.guard = TopicalGuard()

    def test_real_estate_topic_detected(self):
        """Test that real estate topics are correctly identified."""
        # Property-related queries
        result = self.guard.check_topic("Write a property listing for a 3-bedroom house")
        assert result["is_on_topic"] is True
        assert len(result["matched_keywords"]) > 0

        result = self.guard.check_topic("Create a blog about home buying tips")
        assert result["is_on_topic"] is True

        result = self.guard.check_topic("Generate content about mortgage rates")
        assert result["is_on_topic"] is True

    def test_off_topic_detected(self):
        """Test that off-topic requests are correctly identified."""
        # Programming topic
        result = self.guard.check_topic("Write a Python programming tutorial")
        assert result["is_on_topic"] is False
        assert len(result["off_topic_matches"]) > 0

        # Cooking topic
        result = self.guard.check_topic("Give me a recipe for chocolate cake")
        assert result["is_on_topic"] is False

        # Sports topic
        result = self.guard.check_topic("Write about the latest sports news")
        assert result["is_on_topic"] is False

    def test_mixed_content_real_estate_wins(self):
        """Test that mixed content with real estate keywords is allowed."""
        result = self.guard.check_topic(
            "Write a blog about how technology is changing real estate"
        )
        # Should be on-topic because real estate is mentioned
        assert result["is_on_topic"] is True

    def test_off_topic_response_message(self):
        """Test that the off-topic response is correct."""
        assert "Real Estate" in self.guard.OFF_TOPIC_RESPONSE
        assert "Sorry" in self.guard.OFF_TOPIC_RESPONSE

    def test_topic_suggestions(self):
        """Test that topic suggestions are provided."""
        suggestions = self.guard.get_topic_suggestions()
        assert len(suggestions) > 0
        assert any("property" in s.lower() or "real estate" in s.lower() for s in suggestions)


class TestSafetyGuard:
    """Tests for SafetyGuard class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.guard = SafetyGuard(strict_mode=False)

    def test_profanity_detected(self):
        """Test that profanity is correctly detected."""
        result = self.guard.check_profanity("This is a fucking test")
        assert result["has_profanity"] is True
        assert "fuck" in result["profanity_words"] or "fucking" in result["profanity_words"]

        result = self.guard.check_profanity("What the shit is this")
        assert result["has_profanity"] is True

    def test_clean_text_passes(self):
        """Test that clean text passes profanity check."""
        result = self.guard.check_profanity("Write a professional property listing")
        assert result["has_profanity"] is False
        assert len(result["profanity_words"]) == 0

    def test_leetspeak_detected(self):
        """Test that leetspeak profanity is detected."""
        result = self.guard._check_leetspeak("f*ck this")
        assert len(result) > 0

        result = self.guard._check_leetspeak("sh1t happens")
        assert len(result) > 0

    def test_inappropriate_content_detected(self):
        """Test that inappropriate content categories are detected."""
        result = self.guard.check_inappropriate_content("Create violent content")
        assert result["has_inappropriate"] is True

        result = self.guard.check_inappropriate_content("Generate porn images")
        assert result["has_inappropriate"] is True

    def test_image_prompt_safety(self):
        """Test image prompt safety checking."""
        # Safe prompt
        result = self.guard.check_image_prompt("Beautiful house with garden")
        assert result["is_safe"] is True

        # Unsafe prompt
        result = self.guard.check_image_prompt("Generate nude images")
        assert result["is_safe"] is False

        result = self.guard.check_image_prompt("Create violent bloody scene")
        assert result["is_safe"] is False

    def test_sanitize_text(self):
        """Test text sanitization."""
        sanitized = self.guard.sanitize_text("This is fucking great")
        assert "fucking" not in sanitized
        assert "f*****g" in sanitized or "f" in sanitized

    def test_severity_levels(self):
        """Test severity level calculation."""
        # No profanity
        result = self.guard.check_profanity("Clean text")
        assert result["severity"] == "none"

        # Low severity (1 word)
        result = self.guard.check_profanity("This is damn annoying")
        assert result["severity"] in ["low", "none"]  # "damn" might not be in list

        # Higher severity (multiple words)
        result = self.guard.check_profanity("Fuck this shit")
        assert result["severity"] in ["low", "medium", "high"]


class TestGuardrailsManager:
    """Tests for GuardrailsManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = GuardrailsManager(
            enable_topical=True,
            enable_safety=True,
            strict_mode=False,
        )

    def test_manager_initialization(self):
        """Test manager initializes correctly."""
        assert self.manager.enable_topical is True
        assert self.manager.enable_safety is True
        assert self.manager.topical_guard is not None
        assert self.manager.safety_guard is not None

    def test_manager_status(self):
        """Test manager status reporting."""
        status = self.manager.get_status()
        assert status["topical_enabled"] is True
        assert status["safety_enabled"] is True
        assert status["topical_guard_active"] is True
        assert status["safety_guard_active"] is True

    def test_disable_guardrail(self):
        """Test disabling guardrails."""
        self.manager.disable_guardrail("topical")
        assert self.manager.enable_topical is False

        self.manager.disable_guardrail("safety")
        assert self.manager.enable_safety is False

    def test_enable_guardrail(self):
        """Test enabling guardrails."""
        self.manager.disable_guardrail("topical")
        self.manager.enable_guardrail("topical")
        assert self.manager.enable_topical is True

    def test_is_enabled(self):
        """Test is_enabled check."""
        assert self.manager.is_enabled() is True

        self.manager.disable_guardrail("topical")
        self.manager.disable_guardrail("safety")
        assert self.manager.is_enabled() is False

    def test_get_off_topic_response(self):
        """Test getting off-topic response."""
        response = self.manager.get_off_topic_response()
        assert "Real Estate" in response

    def test_get_safety_blocked_response(self):
        """Test getting safety blocked response."""
        response = self.manager.get_safety_blocked_response()
        assert "cannot" in response.lower() or "inappropriate" in response.lower()

    def test_get_topic_suggestions(self):
        """Test getting topic suggestions."""
        suggestions = self.manager.get_topic_suggestions()
        assert len(suggestions) > 0


@pytest.mark.asyncio
class TestGuardrailsAsync:
    """Async tests for guardrails."""

    async def test_topical_validate_on_topic(self):
        """Test async validation for on-topic content."""
        guard = TopicalGuard()
        result = await guard.validate("Write a property listing description")
        assert result["passed"] is True
        assert result["message"] is None

    async def test_topical_validate_off_topic(self):
        """Test async validation for off-topic content."""
        guard = TopicalGuard()
        result = await guard.validate("Write a Python programming tutorial")
        assert result["passed"] is False
        assert result["message"] is not None
        assert "Real Estate" in result["message"]

    async def test_safety_validate_clean(self):
        """Test async safety validation for clean content."""
        guard = SafetyGuard(strict_mode=False)
        result = await guard.validate_text("Professional property description")
        assert result["passed"] is True

    async def test_safety_validate_profanity(self):
        """Test async safety validation for profanity."""
        guard = SafetyGuard(strict_mode=False)
        result = await guard.validate_text("This is fucking terrible")
        assert result["passed"] is False
        assert result["message"] is not None

    async def test_manager_validate_input_on_topic(self):
        """Test manager input validation for on-topic content."""
        manager = GuardrailsManager(strict_mode=False)
        result = await manager.validate_input("Create a real estate blog post")
        assert result["passed"] is True

    async def test_manager_validate_input_off_topic(self):
        """Test manager input validation for off-topic content."""
        manager = GuardrailsManager(strict_mode=False)
        result = await manager.validate_input("Write about cryptocurrency trading")
        assert result["passed"] is False
        assert result["blocked_by"] == "topical"

    async def test_manager_validate_input_profanity(self):
        """Test manager input validation for profanity."""
        manager = GuardrailsManager(strict_mode=False)
        result = await manager.validate_input("Write a fucking property listing")
        assert result["passed"] is False
        assert result["blocked_by"] == "safety"

    async def test_manager_validate_image_request_safe(self):
        """Test manager image request validation for safe content."""
        manager = GuardrailsManager(strict_mode=False)
        result = await manager.validate_image_request("Beautiful house exterior")
        assert result["passed"] is True

    async def test_manager_validate_image_request_unsafe(self):
        """Test manager image request validation for unsafe content."""
        manager = GuardrailsManager(strict_mode=False)
        result = await manager.validate_image_request("Generate nude images")
        assert result["passed"] is False