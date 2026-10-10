"""ChromaDB wrapper for file embedding storage and search."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import chromadb
from chromadb.config import Settings

from llmfilesearch.config import get_db_dir

logger = logging.getLogger(__name__)

_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None

COLLECTION_NAME = "file_index"


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        db_path = get_db_dir() / "chromadb"
        db_path.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=str(db_path),
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def get_collection() -> chromadb.Collection:
    """Get or create the file_index collection."""
    global _collection
    if _collection is None:
        client = _get_client()
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def file_path_to_id(file_path: str) -> str:
    """Generate a deterministic document ID from a file path."""
    return hashlib.sha256(file_path.encode("utf-8")).hexdigest()


def upsert_file(
    file_path: str,
    embedding: list[float],
    document_text: str,
    metadata: dict[str, Any],
) -> None:
    """Insert or update a single file in the collection."""
    collection = get_collection()
    doc_id = file_path_to_id(file_path)
    collection.upsert(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[document_text],
        metadatas=[metadata],
    )


def upsert_files_batch(
    file_paths: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict[str, Any]],
) -> None:
    """Batch upsert multiple files."""
    collection = get_collection()
    ids = [file_path_to_id(p) for p in file_paths]
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )


def delete_file(file_path: str) -> None:
    """Remove a file from the collection."""
    collection = get_collection()
    doc_id = file_path_to_id(file_path)
    collection.delete(ids=[doc_id])


def delete_files_batch(file_paths: list[str]) -> None:
    """Remove multiple files from the collection."""
    if not file_paths:
        return
    collection = get_collection()
    ids = [file_path_to_id(p) for p in file_paths]
    collection.delete(ids=ids)


def search(
    query_embedding: list[float],
    n_results: int = 20,
    where: dict | None = None,
) -> list[dict]:
    """Search for similar files by embedding vector.

    Returns a list of result dicts with keys:
        file_path, file_name, summary, score, metadata
    """
    collection = get_collection()

    kwargs: dict[str, Any] = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)

    if not results["ids"] or not results["ids"][0]:
        return []

    output = []
    for i, doc_id in enumerate(results["ids"][0]):
        distance = results["distances"][0][i]
        # ChromaDB cosine distance: 0 = identical, 2 = opposite
        # Convert to similarity score: 1 - (distance / 2)
        score = 1.0 - (distance / 2.0)

        meta = results["metadatas"][0][i] if results["metadatas"] else {}
        document = results["documents"][0][i] if results["documents"] else ""

        output.append({
            "id": doc_id,
            "file_path": meta.get("file_path", ""),
            "file_name": meta.get("file_name", ""),
            "summary": meta.get("summary", ""),
            "document": document,
            "score": round(score, 4),
            "metadata": meta,
        })

    return output


def get_stats() -> dict:
    """Get collection statistics."""
    collection = get_collection()
    count = collection.count()
    return {
        "total_files_indexed": count,
        "collection_name": COLLECTION_NAME,
    }


def reset_collection() -> None:
    """Delete and recreate the collection. Destructive!"""
    global _collection
    client = _get_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    _collection = None
    get_collection()  # Recreate
