"""Embedding generation via llama-cpp-python."""

from __future__ import annotations

import logging

from llmfilesearch.core.models import load_embedding_model

logger = logging.getLogger(__name__)


def embed_text(text: str) -> list[float]:
    """Generate an embedding vector for a single text string.

    Returns a list of floats (dimension depends on the model, e.g. 768).
    """
    model = load_embedding_model()
    result = model.create_embedding(text)
    return result["data"][0]["embedding"]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts.

    Processes one at a time internally (llama-cpp-python batch embedding
    can be unreliable). Returns a list of embedding vectors.
    """
    model = load_embedding_model()
    embeddings = []
    for text in texts:
        result = model.create_embedding(text)
        embeddings.append(result["data"][0]["embedding"])
    return embeddings


def build_embedding_text(
    file_name: str,
    summary: str,
    file_type: str = "",
    author: str = "",
    title: str = "",
) -> str:
    """Construct the text that will be embedded for a file.

    Combines filename, summary, and key metadata into a single
    searchable string.
    """
    parts = [file_name]
    if title and title != file_name:
        parts.append(title)
    if summary:
        parts.append(summary)
    if file_type:
        parts.append(file_type)
    if author:
        parts.append(f"by {author}")
    return " | ".join(parts)
