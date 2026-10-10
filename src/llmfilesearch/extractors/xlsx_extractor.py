"""Extractor for XLSX/XLS files using openpyxl."""

from __future__ import annotations

import logging
from pathlib import Path

from llmfilesearch.extractors.base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


class XlsxExtractor(BaseExtractor):
    """Extract text and metadata from Excel files."""

    def extract(self, file_path: Path) -> ExtractionResult:
        try:
            from openpyxl import load_workbook

            wb = load_workbook(str(file_path), read_only=True, data_only=True)
            try:
                metadata = {
                    "sheet_names": wb.sheetnames,
                    "sheet_count": len(wb.sheetnames),
                }

                props = wb.properties
                if props:
                    if props.title:
                        metadata["title"] = props.title
                    if props.creator:
                        metadata["author"] = props.creator
                    if props.created:
                        metadata["created"] = props.created.isoformat()

                # Extract content: header row + sample data from each sheet
                text_parts = []
                for sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                    text_parts.append(f"Sheet: {sheet_name}")

                    row_count = 0
                    for row in ws.iter_rows(values_only=True):
                        cells = [str(c) if c is not None else "" for c in row]
                        row_text = " | ".join(c for c in cells if c)
                        if row_text:
                            text_parts.append(row_text)
                        row_count += 1
                        # Limit rows per sheet to prevent huge extractions
                        if row_count >= 200:
                            text_parts.append(f"... ({sheet_name} truncated)")
                            break

                text = "\n".join(text_parts)
                text = self._truncate(text)

                if not text.strip():
                    return ExtractionResult(
                        metadata=metadata, status="metadata_only"
                    )

                return ExtractionResult(text=text, metadata=metadata)

            finally:
                wb.close()

        except Exception as e:
            logger.warning("Failed to extract XLSX %s: %s", file_path, e)
            return ExtractionResult(status="failed", error=str(e))
