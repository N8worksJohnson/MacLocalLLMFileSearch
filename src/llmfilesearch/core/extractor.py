"""Extraction orchestrator — dispatches to the right extractor."""

from __future__ import annotations

import logging
from pathlib import Path

from llmfilesearch.extractors.base import ExtractionResult
from llmfilesearch.extractors.registry import get_extractor

logger = logging.getLogger(__name__)


def extract_file(file_path: str | Path) -> ExtractionResult:
    """Extract text content and metadata from a file.

    Looks up the appropriate extractor by extension and delegates to it.
    Returns a failed result if no extractor is available.
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    extractor = get_extractor(ext)
    if extractor is None:
        return ExtractionResult(
            status="failed",
            error=f"No extractor for extension: {ext}",
        )

    return extractor.extract(path)
