"""Base extractor and extraction result dataclass."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExtractionResult:
    """Result from extracting content from a file."""

    text: str = ""
    metadata: dict = field(default_factory=dict)
    status: str = "success"  # "success", "partial", "failed", "metadata_only"
    error: str | None = None

    @property
    def has_text(self) -> bool:
        return bool(self.text.strip())


class BaseExtractor(ABC):
    """Abstract base class for file content extractors."""

    # Max chars to extract (prevent memory issues on huge files)
    MAX_TEXT_LENGTH = 50_000

    @abstractmethod
    def extract(self, file_path: Path) -> ExtractionResult:
        """Extract text content and metadata from a file.

        Should never raise exceptions — return ExtractionResult with
        status="failed" and error message instead.
        """
        ...

    def _truncate(self, text: str) -> str:
        """Truncate text to MAX_TEXT_LENGTH."""
        if len(text) > self.MAX_TEXT_LENGTH:
            return text[: self.MAX_TEXT_LENGTH]
        return text
