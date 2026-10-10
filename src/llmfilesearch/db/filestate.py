"""SQLite-based file state tracking for incremental scanning."""

from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from llmfilesearch.config import get_db_dir

logger = logging.getLogger(__name__)

_DB_FILENAME = "filestate.db"


@dataclass
class FileState:
    """Stored state for a single file."""

    file_path: str
    file_size: int
    mtime: float
    status: str  # "indexed", "failed", "pending"
    error_message: str | None
    indexed_at: float | None


def _get_db_path() -> Path:
    return get_db_dir() / _DB_FILENAME


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_get_db_path()))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS file_state (
                file_path TEXT PRIMARY KEY,
                file_size INTEGER NOT NULL,
                mtime REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                error_message TEXT,
                indexed_at REAL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_state_status
            ON file_state(status)
        """)
        conn.commit()
    finally:
        conn.close()


def get_file_state(file_path: str) -> FileState | None:
    """Get the stored state for a file."""
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM file_state WHERE file_path = ?",
            (file_path,),
        ).fetchone()
        if row is None:
            return None
        return FileState(
            file_path=row["file_path"],
            file_size=row["file_size"],
            mtime=row["mtime"],
            status=row["status"],
            error_message=row["error_message"],
            indexed_at=row["indexed_at"],
        )
    finally:
        conn.close()


def get_all_indexed_paths() -> set[str]:
    """Return a set of all file paths that are currently indexed."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT file_path FROM file_state WHERE status = 'indexed'"
        ).fetchall()
        return {row["file_path"] for row in rows}
    finally:
        conn.close()


def is_file_changed(file_path: str, size: int, mtime: float) -> bool:
    """Check if a file has changed since it was last indexed.

    Returns True if the file is new, or its size/mtime differ from stored state.
    """
    state = get_file_state(file_path)
    if state is None:
        return True
    if state.status == "failed":
        return True
    return state.file_size != size or abs(state.mtime - mtime) > 0.001


def mark_indexed(file_path: str, size: int, mtime: float) -> None:
    """Mark a file as successfully indexed."""
    conn = _get_connection()
    try:
        conn.execute(
            """
            INSERT INTO file_state (file_path, file_size, mtime, status, error_message, indexed_at)
            VALUES (?, ?, ?, 'indexed', NULL, ?)
            ON CONFLICT(file_path) DO UPDATE SET
                file_size = excluded.file_size,
                mtime = excluded.mtime,
                status = 'indexed',
                error_message = NULL,
                indexed_at = excluded.indexed_at
            """,
            (file_path, size, mtime, time.time()),
        )
        conn.commit()
    finally:
        conn.close()


def mark_failed(file_path: str, size: int, mtime: float, error: str) -> None:
    """Mark a file as failed to index."""
    conn = _get_connection()
    try:
        conn.execute(
            """
            INSERT INTO file_state (file_path, file_size, mtime, status, error_message, indexed_at)
            VALUES (?, ?, ?, 'failed', ?, NULL)
            ON CONFLICT(file_path) DO UPDATE SET
                file_size = excluded.file_size,
                mtime = excluded.mtime,
                status = 'failed',
                error_message = excluded.error_message
            """,
            (file_path, size, mtime, error),
        )
        conn.commit()
    finally:
        conn.close()


def remove_file(file_path: str) -> None:
    """Remove a file's state record."""
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM file_state WHERE file_path = ?", (file_path,))
        conn.commit()
    finally:
        conn.close()


def remove_files_batch(file_paths: list[str]) -> None:
    """Remove multiple file state records."""
    if not file_paths:
        return
    conn = _get_connection()
    try:
        conn.executemany(
            "DELETE FROM file_state WHERE file_path = ?",
            [(p,) for p in file_paths],
        )
        conn.commit()
    finally:
        conn.close()


def get_stats() -> dict:
    """Get file state statistics."""
    conn = _get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM file_state").fetchone()[0]
        indexed = conn.execute(
            "SELECT COUNT(*) FROM file_state WHERE status = 'indexed'"
        ).fetchone()[0]
        failed = conn.execute(
            "SELECT COUNT(*) FROM file_state WHERE status = 'failed'"
        ).fetchone()[0]
        return {
            "total": total,
            "indexed": indexed,
            "failed": failed,
        }
    finally:
        conn.close()


def clear_all() -> None:
    """Delete all file state records. Destructive!"""
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM file_state")
        conn.commit()
    finally:
        conn.close()
