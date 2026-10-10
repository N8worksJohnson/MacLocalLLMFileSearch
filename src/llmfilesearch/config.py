"""Application configuration and path management."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

from platformdirs import user_data_dir


APP_NAME = "LLMFileSearch"
APP_AUTHOR = "LLMFileSearch"


def get_data_dir() -> Path:
    """Return the platform-appropriate data directory, creating it if needed."""
    p = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_models_dir() -> Path:
    """Return the directory where downloaded GGUF models are stored."""
    p = get_data_dir() / "models"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_db_dir() -> Path:
    """Return the directory for ChromaDB and SQLite databases."""
    p = get_data_dir() / "db"
    p.mkdir(parents=True, exist_ok=True)
    return p


def is_frozen() -> bool:
    """Return True if running from a PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def get_bundle_dir() -> Path:
    """Return the PyInstaller bundle directory, or the project root in dev."""
    if is_frozen():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent.parent


@dataclass
class AppConfig:
    """Runtime application configuration."""

    # Server
    host: str = "127.0.0.1"
    port: int = 8741

    # Paths
    data_dir: Path = field(default_factory=get_data_dir)
    models_dir: Path = field(default_factory=get_models_dir)
    db_dir: Path = field(default_factory=get_db_dir)

    # Scanning defaults
    max_file_size_mb: int = 100
    batch_size: int = 50
    scan_exclude_patterns: list[str] = field(
        default_factory=lambda: [
            ".*",           # Hidden files/dirs
            "__pycache__",
            "node_modules",
            ".git",
            ".svn",
            "*.tmp",
            "*.lock",
            "Thumbs.db",
            ".DS_Store",
        ]
    )

    # LLM defaults
    summarizer_max_input_chars: int = 50_000
    summarizer_chunk_size: int = 4000
    summarizer_chunk_overlap: int = 200
    embedding_context_length: int = 8192
    chat_context_length: int = 32768
    chat_max_history_turns: int = 10

    # Search defaults
    search_top_k: int = 20
    chat_top_k: int = 8

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


# Global singleton
_config: AppConfig | None = None


def get_config() -> AppConfig:
    global _config
    if _config is None:
        _config = AppConfig()
    return _config
