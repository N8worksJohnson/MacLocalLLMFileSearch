"""Vector search engine — queries ChromaDB for relevant files."""

from __future__ import annotations

import logging
from datetime import datetime

from llmfilesearch.config import get_config
from llmfilesearch.core.embedder import embed_text
from llmfilesearch.db import vectorstore

logger = logging.getLogger(__name__)


def search(
    query: str,
    n_results: int | None = None,
    file_type: str | None = None,
    directory: str | None = None,
    modified_after: str | None = None,
    modified_before: str | None = None,
) -> list[dict]:
    """Search for files matching a natural language query.

    Args:
        query: Natural language search query.
        n_results: Max results to return (default from config).
        file_type: Filter by file type category (e.g. "document", "code").
        directory: Filter to files within this directory (prefix match).
        modified_after: ISO date string — only files modified after this date.
        modified_before: ISO date string — only files modified before this date.

    Returns:
        List of result dicts sorted by relevance score (highest first).
    """
    config = get_config()
    if n_results is None:
        n_results = config.search_top_k

    # Embed the query
    query_embedding = embed_text(query)

    # Build ChromaDB where clause
    where_conditions: list[dict] = []

    if file_type:
        where_conditions.append({"file_type": {"$eq": file_type}})

    if directory:
        where_conditions.append({"directory": {"$eq": directory}})

    if modified_after:
        try:
            ts = datetime.fromisoformat(modified_after).timestamp()
            where_conditions.append({"modified_at": {"$gte": ts}})
        except ValueError:
            pass

    if modified_before:
        try:
            ts = datetime.fromisoformat(modified_before).timestamp()
            where_conditions.append({"modified_at": {"$lte": ts}})
        except ValueError:
            pass

    where: dict | None = None
    if len(where_conditions) == 1:
        where = where_conditions[0]
    elif len(where_conditions) > 1:
        where = {"$and": where_conditions}

    # Query ChromaDB
    results = vectorstore.search(
        query_embedding=query_embedding,
        n_results=n_results,
        where=where,
    )

    return results
