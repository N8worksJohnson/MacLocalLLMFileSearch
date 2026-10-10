"""Persistent settings storage using SQLite."""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from llmfilesearch.config import get_db_dir

logger = logging.getLogger(__name__)

_DB_FILENAME = "settings.db"

# Default settings
DEFAULTS: dict[str, Any] = {
    "scan_directories": [],
    "exclude_patterns": [
        ".*", "__pycache__", "node_modules", ".git", ".svn",
        "*.tmp", "*.lock", "Thumbs.db", ".DS_Store",
    ],
    "max_file_size_mb": 100,
    "auto_scan": False,
    "scan_interval_hours": 24,
    "theme": "dark",
    "embedding_model": None,  # filename of selected model
    "chat_model": None,       # filename of selected model
    "setup_complete": False,
}


def _get_db_path() -> Path:
    return get_db_dir() / _DB_FILENAME


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_get_db_path()))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the settings table if it doesn't exist."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def get(key: str) -> Any:
    """Get a setting value by key. Returns the default if not set."""
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return DEFAULTS.get(key)
        return json.loads(row["value"])
    finally:
        conn.close()


def set(key: str, value: Any) -> None:
    """Set a setting value."""
    conn = _get_connection()
    try:
        conn.execute(
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, json.dumps(value)),
        )
        conn.commit()
    finally:
        conn.close()


def get_all() -> dict[str, Any]:
    """Get all settings, merged with defaults."""
    result = dict(DEFAULTS)
    conn = _get_connection()
    try:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        for row in rows:
            result[row["key"]] = json.loads(row["value"])
    finally:
        conn.close()
    return result


def update(updates: dict[str, Any]) -> dict[str, Any]:
    """Update multiple settings at once. Returns the full settings dict."""
    conn = _get_connection()
    try:
        for key, value in updates.items():
            conn.execute(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, json.dumps(value)),
            )
        conn.commit()
    finally:
        conn.close()
    return get_all()


def delete(key: str) -> None:
    """Remove a setting (reverts to default)."""
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM settings WHERE key = ?", (key,))
        conn.commit()
    finally:
        conn.close()
