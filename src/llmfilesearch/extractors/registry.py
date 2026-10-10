"""Extractor registry — maps file extensions to extractor instances."""

from __future__ import annotations

from llmfilesearch.extractors.base import BaseExtractor
from llmfilesearch.extractors.docx_extractor import DocxExtractor
from llmfilesearch.extractors.media_extractor import MediaExtractor
from llmfilesearch.extractors.pdf_extractor import PdfExtractor
from llmfilesearch.extractors.pptx_extractor import PptxExtractor
from llmfilesearch.extractors.text_extractor import TextExtractor
from llmfilesearch.extractors.xlsx_extractor import XlsxExtractor

# Singleton instances
_text = TextExtractor()
_pdf = PdfExtractor()
_docx = DocxExtractor()
_xlsx = XlsxExtractor()
_pptx = PptxExtractor()
_media = MediaExtractor()

# Extension → extractor mapping
_REGISTRY: dict[str, BaseExtractor] = {}

# PDF
for ext in (".pdf",):
    _REGISTRY[ext] = _pdf

# DOCX
for ext in (".docx",):
    _REGISTRY[ext] = _docx

# XLSX
for ext in (".xlsx",):
    _REGISTRY[ext] = _xlsx

# PPTX
for ext in (".pptx",):
    _REGISTRY[ext] = _pptx

# Text / code / data files
_TEXT_EXTENSIONS = (
    ".txt", ".md", ".markdown", ".rst", ".log", ".ini", ".cfg", ".toml",
    ".yaml", ".yml", ".xml", ".html", ".htm", ".json", ".jsonl",
    ".csv", ".tsv",
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".cc",
    ".h", ".hpp", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".kts",
    ".scala", ".cs", ".vb", ".r", ".m", ".mm", ".lua", ".pl", ".pm",
    ".sh", ".bash", ".zsh", ".fish", ".sql", ".graphql", ".proto",
    ".zig", ".nim", ".dart", ".ex", ".exs", ".clj", ".cljs", ".hs",
    ".erl", ".elm", ".vue", ".svelte",
    ".css", ".scss", ".sass", ".less", ".styl",
    ".makefile", ".cmake", ".gradle", ".sbt",
    ".eml",
)
for ext in _TEXT_EXTENSIONS:
    _REGISTRY[ext] = _text

# Media files
_MEDIA_EXTENSIONS = (
    # Images
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp",
    ".heic", ".heif", ".svg", ".ico", ".raw", ".cr2", ".nef", ".arw",
    # Video
    ".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm", ".m4v",
    ".mpg", ".mpeg",
    # Audio
    ".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a", ".opus",
    ".aiff",
)
for ext in _MEDIA_EXTENSIONS:
    _REGISTRY[ext] = _media


def get_extractor(extension: str) -> BaseExtractor | None:
    """Look up the extractor for a file extension (lowercase, with dot)."""
    return _REGISTRY.get(extension.lower())


def is_supported(extension: str) -> bool:
    """Check if we have an extractor for this extension."""
    return extension.lower() in _REGISTRY
