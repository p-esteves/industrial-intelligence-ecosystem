"""
Industrial Multi-Agent Ecosystem — Configuration Module.

Centralized settings management using Pydantic Settings.
Reads from .env file and environment variables with sensible defaults
for local-first (Ollama) or remote (Groq/Gemini/Claude) operation.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application-wide settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM Provider ────────────────────────────────────────────
    llm_provider: Literal["ollama", "gemini", "claude", "groq"] = "ollama"

    # ── Ollama ──────────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    # ── Google Gemini ───────────────────────────────────────────
    google_api_key: str = ""
    google_model: str = "gemini-2.0-flash"

    # ── Anthropic Claude ────────────────────────────────────────
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    # ── Groq ────────────────────────────────────────────────────
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # ── Embeddings ──────────────────────────────────────────────
    embedding_provider: Literal["local", "gemini"] = "local"
    embedding_model_name: str = "BAAI/bge-small-en-v1.5"

    # ── Paths ───────────────────────────────────────────────────
    data_dir: str = "./data"
    sample_dir: str = "./data/sample"
    faiss_index_dir: str = "./data/.faiss_index"

    # ── Anomaly Detection Thresholds ─────────────────────────────
    anomaly_zscore_threshold: float = 2.0
    anomaly_iqr_threshold: float = 1.5

    # ── Logging ─────────────────────────────────────────────────
    log_level: str = "INFO"

    # ── API Server ──────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:8501,http://localhost:8502"

    # ── Frontend / Backend integration ─────────────────────────
    backend_url: str = "http://localhost:8000"

    # ── Derived Properties ──────────────────────────────────────

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def docs_dir(self) -> str:
        """Path to the directory where PDF/text documents are stored."""
        return f"{self.data_dir}/docs"

    @property
    def sample_docs_dir(self) -> str:
        """Path to sample industrial documentation."""
        return f"{self.sample_dir}/docs"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached singleton of application settings.
    This ensures settings are loaded only once from disk.
    """
    return Settings()

