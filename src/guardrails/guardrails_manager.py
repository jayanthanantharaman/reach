"""
Guardrails Manager for REACH.


This module provides a unified interface for managing all guardrails
including topical and safety guardrails using NeMo Guardrails framework.
"""

import logging
from typing import Any, Optional

from .topical_guard import TopicalGuard
from .safety_guard import SafetyGuard

logger = logging.getLogger(__name__)


class GuardrailsManager:
    """
    Unified manager for all REACH guardrails.
    
    Combines topical guardrails (Real Estate only) and safety guardrails
    (profanity blocking) into a single interface.
    """

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        enable_topical: bool = True,
        enable_safety: bool = True,
        strict_mode: bool = True,
    ):
        """
        Initialize the Guardrails Manager.
        
        Args:
            llm_client: Optional LLM client for semantic analysis
            enable_topical: Enable topical guardrails (Real Estate only)
            enable_safety: Enable safety guardrails (profanity blocking)
            strict_mode: Use strict mode for safety checks
        """
        self.llm_client = llm_client
        self.enable_topical = enable_topical
        self.enable_safety = enable_safety

        # Initialize guards
        self.topical_guard = TopicalGuard(llm_client=llm_client) if enable_topical else None
        self.safety_guard = SafetyGuard(llm_client=llm_client, strict_mode=strict_mode) if enable_safety else None

        logger.info(
            f"GuardrailsManager initialized: topical={enable_topical}, safety={enable_safety}"
        )

    async def validate_input(
        self,
        user_input: str,
        content_type: str = "text",
        skip_topical: bool = False,
    ) -> dict[str, Any]:
        """
        Validate user input against all enabled guardrails.
        
        Args:
            user_input: The user's input text
            content_type: Type of content ("text" or "image")
            skip_topical: If True, skip topical validation (only run safety)
            
        Returns:
            Dictionary with:
                - passed: Boolean indicating if all validations passed
                - message: Response message if blocked
                - blocked_by: Which guardrail blocked the request
                - details: Detailed results from each guardrail
        """
        results = {
            "passed": True,
            "message": None,
            "blocked_by": None,
            "details": {},
        }

        # Check safety first (profanity/inappropriate content)
        if self.enable_safety and self.safety_guard:
            safety_result = await self.safety_guard.validate(user_input, content_type)
            results["details"]["safety"] = safety_result

            if not safety_result["passed"]:
                results["passed"] = False
                results["message"] = safety_result["message"]
                results["blocked_by"] = "safety"
                logger.info(f"Input blocked by safety guardrail: {user_input[:50]}...")
                return results

        # Check topical relevance (Real Estate only) - can be skipped
        if not skip_topical and self.enable_topical and self.topical_guard:
            topical_result = await self.topical_guard.validate(user_input)
            results["details"]["topical"] = topical_result

            if not topical_result["passed"]:
                results["passed"] = False
                results["message"] = topical_result["message"]
                results["blocked_by"] = "topical"
                logger.info(f"Input blocked by topical guardrail: {user_input[:50]}...")
                return results

        return results

    async def validate_safety_only(
        self,
        user_input: str,
        content_type: str = "text",
    ) -> dict[str, Any]:
        """
        Validate user input against safety guardrails only (no topical check).
        
        This is useful for content types like Instagram where we want to allow
        creative freedom while still blocking inappropriate content.
        
        Args:
            user_input: The user's input text
            content_type: Type of content ("text" or "image")
            
        Returns:
            Dictionary with:
                - passed: Boolean indicating if safety validation passed
                - message: Response message if blocked
                - blocked_by: Which guardrail blocked the request
                - details: Detailed results from safety guardrail
        """
        return await self.validate_input(user_input, content_type, skip_topical=True)

    async def validate_output(
        self,
        output: str,
        content_type: str = "text",
    ) -> dict[str, Any]:
        """
        Validate generated output against safety guardrails.
        
        Args:
            output: The generated output text
            content_type: Type of content
            
        Returns:
            Dictionary with validation results
        """
        results = {
            "passed": True,
            "message": None,
            "blocked_by": None,
            "details": {},
        }

        # Only check safety for outputs (topical is for inputs)
        if self.enable_safety and self.safety_guard:
            safety_result = await self.safety_guard.validate(output, content_type)
            results["details"]["safety"] = safety_result

            if not safety_result["passed"]:
                results["passed"] = False
                results["message"] = "Generated content contains inappropriate material and has been blocked."
                results["blocked_by"] = "safety"
                logger.warning(f"Output blocked by safety guardrail")
                return results

        return results

    async def validate_image_request(self, prompt: str) -> dict[str, Any]:
        """
        Validate image generation request.
        
        Args:
            prompt: Image generation prompt
            
        Returns:
            Dictionary with validation results
        """
        # First validate as regular input
        input_result = await self.validate_input(prompt, content_type="image")

        if not input_result["passed"]:
            return input_result

        # Additional image-specific safety check
        if self.enable_safety and self.safety_guard:
            image_result = await self.safety_guard.validate_image_prompt(prompt)
            input_result["details"]["image_safety"] = image_result

            if not image_result["passed"]:
                input_result["passed"] = False
                input_result["message"] = image_result["message"]
                input_result["blocked_by"] = "image_safety"

        return input_result

    def get_off_topic_response(self) -> str:
        """Get the standard off-topic response message."""
        if self.topical_guard:
            return self.topical_guard.OFF_TOPIC_RESPONSE
        return "Sorry! I cannot help you with that topic. My expertise is in Real Estate."

    def get_safety_blocked_response(self) -> str:
        """Get the standard safety blocked response message."""
        if self.safety_guard:
            return self.safety_guard.BLOCKED_RESPONSE
        return "I cannot help create content with inappropriate material."

    def get_topic_suggestions(self) -> list[str]:
        """Get suggestions for on-topic requests."""
        if self.topical_guard:
            return self.topical_guard.get_topic_suggestions()
        return []

    def is_enabled(self) -> bool:
        """Check if any guardrails are enabled."""
        return self.enable_topical or self.enable_safety

    def get_status(self) -> dict[str, Any]:
        """Get the current status of all guardrails."""
        return {
            "topical_enabled": self.enable_topical,
            "safety_enabled": self.enable_safety,
            "llm_client_available": self.llm_client is not None,
            "topical_guard_active": self.topical_guard is not None,
            "safety_guard_active": self.safety_guard is not None,
        }

    def set_llm_client(self, llm_client: Any) -> None:
        """
        Set or update the LLM client for semantic analysis.
        
        Args:
            llm_client: LLM client instance
        """
        self.llm_client = llm_client

        if self.topical_guard:
            self.topical_guard.llm_client = llm_client

        if self.safety_guard:
            self.safety_guard.llm_client = llm_client

        logger.info("LLM client updated for guardrails")

    def enable_guardrail(self, guardrail_type: str) -> None:
        """
        Enable a specific guardrail.
        
        Args:
            guardrail_type: "topical" or "safety"
        """
        if guardrail_type == "topical":
            self.enable_topical = True
            if not self.topical_guard:
                self.topical_guard = TopicalGuard(llm_client=self.llm_client)
        elif guardrail_type == "safety":
            self.enable_safety = True
            if not self.safety_guard:
                self.safety_guard = SafetyGuard(llm_client=self.llm_client)

        logger.info(f"Enabled {guardrail_type} guardrail")

    def disable_guardrail(self, guardrail_type: str) -> None:
        """
        Disable a specific guardrail.
        
        Args:
            guardrail_type: "topical" or "safety"
        """
        if guardrail_type == "topical":
            self.enable_topical = False
        elif guardrail_type == "safety":
            self.enable_safety = False

        logger.info(f"Disabled {guardrail_type} guardrail")


# NeMo Guardrails integration helper
class NeMoGuardrailsConfig:
    """
    Helper class for NeMo Guardrails configuration.
    
    Provides methods to generate NeMo-compatible configuration
    for the REACH guardrails.
    """

    @staticmethod
    def get_config_yaml() -> str:
        """
        Get the NeMo Guardrails YAML configuration.
        
        Returns:
            YAML configuration string
        """
        return """
# REACH NeMo Guardrails Configuration
# 

models:
  - type: main
    engine: google
    model: gemini-1.5-pro

rails:
  input:
    flows:
      - check_topical_relevance
      - check_safety
  output:
    flows:
      - check_output_safety

prompts:
  - task: check_topical_relevance
    content: |
      Determine if the user's request is related to Real Estate.
      Real Estate topics include: property buying/selling/renting, 
      real estate marketing, property descriptions, mortgage/financing,
      property management, and real estate content creation.
      
      User request: {{ user_input }}
      
      Respond with "on_topic" or "off_topic".

  - task: check_safety
    content: |
      Check if the following text contains profanity, offensive language,
      hate speech, violence, adult content, or other inappropriate material.
      
      Text: {{ user_input }}
      
      Respond with "safe" or "unsafe".
"""

    @staticmethod
    def get_colang_rules() -> str:
        """
        Get the NeMo Guardrails CoLang rules.
        
        Returns:
            CoLang rules string
        """
        return """
# REACH NeMo Guardrails CoLang Rules
# 

# Topical Guardrail - Real Estate Only
define flow check_topical_relevance
  user "{*}"
  $is_real_estate = execute check_real_estate_topic(user_input=$user_message)
  if not $is_real_estate
    bot "Sorry! I cannot help you with that topic. My expertise is in Real Estate. I can help you with property listings, real estate marketing, home buying/selling content, property descriptions, and real estate social media posts."
    stop
  end

# Safety Guardrail - Block Profanity
define flow check_safety
  user "{*}"
  $is_safe = execute check_content_safety(user_input=$user_message)
  if not $is_safe
    bot "I cannot help create content with profanity, offensive language, or inappropriate material. Please rephrase your request using professional and appropriate language."
    stop
  end

# Output Safety Check
define flow check_output_safety
  bot "{*}"
  $output_safe = execute check_content_safety(user_input=$bot_message)
  if not $output_safe
    bot "I apologize, but I cannot provide that response. Let me help you with appropriate real estate content instead."
    stop
  end

# Real Estate Topic Keywords
define flow greet_real_estate
  user "hello" or "hi" or "hey"
  bot "Hello! I'm your Real Estate content assistant. I can help you with property listings, real estate marketing, blog posts, LinkedIn content, and images for your real estate business. What would you like to create today?"
end

# Property Listing Request
define flow property_listing
  user "{*} property listing {*}" or "{*} listing description {*}" or "{*} describe property {*}"
  bot "I'd be happy to help create a property listing description. Please provide details about the property (bedrooms, bathrooms, features, location, etc.)."
end

# Real Estate Blog Request
define flow real_estate_blog
  user "{*} real estate blog {*}" or "{*} property blog {*}" or "{*} housing market {*}"
  bot "I can help you write an engaging real estate blog post. What topic would you like to cover? Some popular options include market trends, home buying tips, or neighborhood guides."
end

# Block Off-Topic Requests
define flow block_off_topic
  user "{*} recipe {*}" or "{*} cooking {*}" or "{*} movie {*}" or "{*} sports {*}"
  bot "Sorry! I cannot help you with that topic. My expertise is in Real Estate. I can help you with property listings, real estate marketing, home buying/selling content, property descriptions, and real estate social media posts."
  stop
end

# Block Profanity
define flow block_profanity
  user "{*} fuck {*}" or "{*} shit {*}" or "{*} damn {*}" or "{*} ass {*}"
  bot "I cannot help create content with profanity or offensive language. Please rephrase your request using professional and appropriate language."
  stop
end

# Block Inappropriate Image Requests
define flow block_inappropriate_images
  user "{*} nude {*}" or "{*} violent {*}" or "{*} explicit {*}" or "{*} gore {*}"
  bot "I cannot generate images containing inappropriate, offensive, violent, or explicit content. Please describe a professional and appropriate image for your real estate needs."
  stop
end
"""

    @staticmethod
    def save_config_files(config_dir: str = "rails_config") -> None:
        """
        Save NeMo Guardrails configuration files.
        
        Args:
            config_dir: Directory to save configuration files
        """
        import os

        os.makedirs(config_dir, exist_ok=True)

        # Save YAML config
        with open(os.path.join(config_dir, "config.yaml"), "w") as f:
            f.write(NeMoGuardrailsConfig.get_config_yaml())

        # Save CoLang rules
        with open(os.path.join(config_dir, "rails.co"), "w") as f:
            f.write(NeMoGuardrailsConfig.get_colang_rules())

        logger.info(f"NeMo Guardrails config files saved to {config_dir}")