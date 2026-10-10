"""Extractor for plain text files: TXT, MD, CSV, JSON, code, etc."""

from __future__ import annotations

import logging
from pathlib import Path

from charset_normalizer import from_path

from llmfilesearch.extractors.base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


class TextExtractor(BaseExtractor):
    """Extract text from plain text and code files."""

    def extract(self, file_path: Path) -> ExtractionResult:
        try:
            # Try UTF-8 first (fast path)
            try:
                text = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                # Detect encoding
                result = from_path(file_path)
                best = result.best()
                if best is None:
                    return ExtractionResult(
                        status="failed",
                        error="Could not detect file encoding",
                    )
                text = str(best)

            text = self._truncate(text)

            metadata = {
                "line_count": text.count("\n") + 1,
            }

            # For code files, try to detect the language from the content
            ext = file_path.suffix.lower()
            if ext in (".json", ".jsonl"):
                metadata["format"] = "json"
            elif ext == ".csv":
                metadata["format"] = "csv"
            elif ext in (".yaml", ".yml"):
                metadata["format"] = "yaml"
            elif ext in (".xml", ".html", ".htm"):
                metadata["format"] = "markup"

            return ExtractionResult(text=text, metadata=metadata)

        except Exception as e:
            logger.warning("Failed to extract text from %s: %s", file_path, e)
            return ExtractionResult(status="failed", error=str(e))
