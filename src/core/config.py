"""
Configuration management for REACH.


This module handles all configuration settings including API keys,
model parameters, and application settings.
"""

import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application Settings
    app_name: str = Field(default="REACH", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # Google Gemini Settings
    google_api_key: str = Field(
        default="", description="Google API key for Gemini", alias="GOOGLE_API_KEY"
    )
    gemini_model: str = Field(
        default="gemini-1.5-pro", description="Gemini model to use"
    )
    gemini_temperature: float = Field(
        default=0.7, description="Temperature for Gemini responses"
    )
    gemini_max_tokens: int = Field(
        default=8192, description="Max tokens for Gemini responses"
    )

    # OpenAI Settings (for DALL-E)
    openai_api_key: str = Field(
        default="", description="OpenAI API key for DALL-E", alias="OPENAI_API_KEY"
    )
    dalle_model: str = Field(default="dall-e-3", description="DALL-E model to use")
    dalle_image_size: str = Field(
        default="1024x1024", description="Default image size for DALL-E"
    )
    dalle_quality: str = Field(
        default="standard", description="Image quality (standard or hd)"
    )

    # SERP API Settings
    serp_api_key: str = Field(
        default="", description="SERP API key for web research", alias="SERP_API_KEY"
    )
    serp_results_count: int = Field(
        default=10, description="Number of search results to fetch"
    )

    # Content Settings
    max_blog_length: int = Field(
        default=2000, description="Maximum blog post length in words"
    )
    max_linkedin_length: int = Field(
        default=3000, description="Maximum LinkedIn post length in characters"
    )
    default_language: str = Field(default="en", description="Default content language")

    # Rate Limiting
    rate_limit_requests: int = Field(
        default=60, description="Max requests per minute"
    )
    rate_limit_tokens: int = Field(
        default=100000, description="Max tokens per minute"
    )

    # Memory Settings
    conversation_memory_limit: int = Field(
        default=20, description="Number of conversation turns to remember"
    )
    session_timeout_minutes: int = Field(
        default=60, description="Session timeout in minutes"
    )

    # Quality Settings
    min_quality_score: float = Field(
        default=0.7, description="Minimum quality score for content"
    )
    enable_quality_validation: bool = Field(
        default=True, description="Enable content quality validation"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Returns:
        Settings: Application settings
    """
    return Settings()


# Eagerly expose a module-level settings instance for convenience imports.
settings = get_settings()


def validate_api_keys() -> dict[str, bool]:
    """
    Validate that required API keys are configured.
    
    Returns:
        dict: Dictionary with API key validation status
    """
    settings = get_settings()
    return {
        "google_api_key": bool(settings.google_api_key),
        "openai_api_key": bool(settings.openai_api_key),
        "serp_api_key": bool(settings.serp_api_key),
    }


def get_missing_api_keys() -> list[str]:
    """
    Get list of missing API keys.
    
    Returns:
        list: List of missing API key names
    """
    validation = validate_api_keys()
    return [key for key, is_valid in validation.items() if not is_valid]
