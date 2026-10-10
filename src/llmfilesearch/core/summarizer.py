"""LLM-based file content summarization."""

from __future__ import annotations

import logging

from llmfilesearch.constants import SUMMARIZE_METADATA_PROMPT, SUMMARIZE_SYSTEM_PROMPT
from llmfilesearch.core.models import load_chat_model

logger = logging.getLogger(__name__)


def summarize_text(text: str, file_name: str = "") -> str:
    """Summarize file text content using a single LLM call.

    The caller (indexer._smart_summarize) is responsible for truncating
    long texts before calling this, so we always make exactly one LLM call.
    """
    if not text.strip():
        return ""

    prompt_text = text
    if file_name:
        prompt_text = f"File: {file_name}\n\n{text}"

    return _llm_summarize(prompt_text)


def summarize_metadata(metadata: dict, file_name: str = "") -> str:
    """Generate a summary from file metadata only (for media files, etc.)."""
    parts = []
    if file_name:
        parts.append(f"File: {file_name}")

    for key, value in metadata.items():
        if value and key not in ("file_path", "file_name", "file_ext"):
            parts.append(f"{key}: {value}")

    if not parts:
        return ""

    prompt = "\n".join(parts)

    model = load_chat_model()
    response = model.create_chat_completion(
        messages=[
            {"role": "system", "content": SUMMARIZE_METADATA_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=200,
        temperature=0.1,
    )

    return response["choices"][0]["message"]["content"].strip()


def _llm_summarize(text: str) -> str:
    """Call the LLM to summarize a single piece of text."""
    model = load_chat_model()

    response = model.create_chat_completion(
        messages=[
            {"role": "system", "content": SUMMARIZE_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        max_tokens=300,
        temperature=0.1,
    )

    return response["choices"][0]["message"]["content"].strip()


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        # Try to break at a sentence or paragraph boundary
        if end < len(text):
            last_para = chunk.rfind("\n\n")
            last_sentence = chunk.rfind(". ")
            last_newline = chunk.rfind("\n")

            # Prefer paragraph break > sentence break > newline
            break_point = max(last_para, last_sentence, last_newline)
            if break_point > chunk_size * 0.5:
                chunk = chunk[: break_point + 1]
                end = start + break_point + 1

        chunks.append(chunk.strip())
        start = end - overlap

    return [c for c in chunks if c]
