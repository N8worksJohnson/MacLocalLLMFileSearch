"""Extractor for PDF files using pymupdf."""

from __future__ import annotations

import logging
from pathlib import Path

from llmfilesearch.extractors.base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


class PdfExtractor(BaseExtractor):
    """Extract text and metadata from PDF files."""

    def extract(self, file_path: Path) -> ExtractionResult:
        try:
            import fitz  # pymupdf

            doc = fitz.open(str(file_path))
            try:
                # Extract metadata
                meta = doc.metadata or {}
                metadata = {}
                if meta.get("title"):
                    metadata["title"] = meta["title"]
                if meta.get("author"):
                    metadata["author"] = meta["author"]
                if meta.get("subject"):
                    metadata["subject"] = meta["subject"]
                if meta.get("creationDate"):
                    metadata["creation_date"] = meta["creationDate"]
                metadata["page_count"] = len(doc)

                # Extract text from all pages
                text_parts = []
                for page in doc:
                    page_text = page.get_text()
                    if page_text:
                        text_parts.append(page_text)

                text = "\n\n".join(text_parts)
                text = self._truncate(text)

                if not text.strip():
                    return ExtractionResult(
                        text="",
                        metadata=metadata,
                        status="metadata_only",
                    )

                return ExtractionResult(text=text, metadata=metadata)

            finally:
                doc.close()

        except Exception as e:
            logger.warning("Failed to extract PDF %s: %s", file_path, e)
            return ExtractionResult(status="failed", error=str(e))
