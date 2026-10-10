"""Directory walker with change detection for incremental scanning."""

from __future__ import annotations

import fnmatch
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Generator

from llmfilesearch.config import get_config
from llmfilesearch.constants import ALL_SUPPORTED_EXTENSIONS
from llmfilesearch.db import filestate

logger = logging.getLogger(__name__)


@dataclass
class FileJob:
    """Represents a file to be processed by the indexer."""

    path: str
    size: int
    mtime: float
    extension: str
    is_new: bool  # True if not previously indexed


@dataclass
class ScanResult:
    """Summary of a directory scan."""

    files_to_process: list[FileJob]
    files_deleted: list[str]  # paths of previously indexed files that no longer exist
    files_unchanged: int
    total_discovered: int
    scan_duration_seconds: float


def _is_excluded(path: str, name: str, exclude_patterns: list[str]) -> bool:
    """Check if a file or directory name matches any exclude pattern."""
    for pattern in exclude_patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
        if fnmatch.fnmatch(name.lower(), pattern.lower()):
            return True
    return False


def scan_directories(
    directories: list[str],
    exclude_patterns: list[str] | None = None,
    cancel_event: Event | None = None,
) -> ScanResult:
    """Scan directories for files to index.

    Walks the given directories, finds supported files, and compares
    against the file state DB to determine which files are new, changed,
    or deleted.

    Args:
        directories: List of directory paths to scan.
        exclude_patterns: Glob patterns for files/dirs to skip.
        cancel_event: Set this event to cancel the scan mid-run.

    Returns:
        ScanResult with files to process and files to delete.
    """
    config = get_config()
    if exclude_patterns is None:
        exclude_patterns = config.scan_exclude_patterns

    max_size = config.max_file_size_bytes
    start_time = time.monotonic()

    # Get all currently indexed paths
    indexed_paths = filestate.get_all_indexed_paths()
    seen_paths: set[str] = set()

    files_to_process: list[FileJob] = []
    files_unchanged = 0
    total_discovered = 0

    for directory in directories:
        if cancel_event and cancel_event.is_set():
            break

        dir_path = Path(directory)
        if not dir_path.is_dir():
            logger.warning("Scan directory does not exist: %s", directory)
            continue

        for root, dirs, files in os.walk(dir_path, followlinks=False):
            if cancel_event and cancel_event.is_set():
                break

            # Filter out excluded directories in-place
            dirs[:] = [
                d for d in dirs
                if not _is_excluded(os.path.join(root, d), d, exclude_patterns)
            ]

            for filename in files:
                if cancel_event and cancel_event.is_set():
                    break

                if _is_excluded(os.path.join(root, filename), filename, exclude_patterns):
                    continue

                file_path = os.path.join(root, filename)
                ext = os.path.splitext(filename)[1].lower()

                if ext not in ALL_SUPPORTED_EXTENSIONS:
                    continue

                try:
                    stat = os.stat(file_path)
                except OSError:
                    continue

                if stat.st_size > max_size:
                    continue

                if stat.st_size == 0:
                    continue

                total_discovered += 1
                seen_paths.add(file_path)

                # Check if file needs reindexing
                if filestate.is_file_changed(file_path, stat.st_size, stat.st_mtime):
                    is_new = file_path not in indexed_paths
                    files_to_process.append(FileJob(
                        path=file_path,
                        size=stat.st_size,
                        mtime=stat.st_mtime,
                        extension=ext,
                        is_new=is_new,
                    ))
                else:
                    files_unchanged += 1

    # Detect deleted files
    files_deleted = list(indexed_paths - seen_paths)

    scan_duration = time.monotonic() - start_time
    logger.info(
        "Scan complete: %d discovered, %d to process, %d unchanged, %d deleted (%.1fs)",
        total_discovered,
        len(files_to_process),
        files_unchanged,
        len(files_deleted),
        scan_duration,
    )

    return ScanResult(
        files_to_process=files_to_process,
        files_deleted=files_deleted,
        files_unchanged=files_unchanged,
        total_discovered=total_discovered,
        scan_duration_seconds=round(scan_duration, 2),
    )
