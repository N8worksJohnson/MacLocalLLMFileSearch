"""Indexing control endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from llmfilesearch.api.schemas import IndexStartRequest, IndexStatusResponse, IndexStatsResponse
from llmfilesearch.core.indexer import get_indexer
from llmfilesearch.db import filestate, settings_store, vectorstore

router = APIRouter(prefix="/api/index", tags=["index"])


@router.post("/start")
def start_indexing(req: IndexStartRequest) -> dict:
    indexer = get_indexer()

    if indexer.is_running:
        return {"status": "already_running"}

    directories = req.directories
    if not directories:
        directories = settings_store.get("scan_directories") or []

    if not directories:
        return {"status": "error", "message": "No directories configured. Add directories in settings."}

    exclude_patterns = settings_store.get("exclude_patterns")

    indexer.start(
        directories=directories,
        exclude_patterns=exclude_patterns,
        full_rescan=req.full_rescan,
    )

    return {"status": "started"}


@router.post("/stop")
def stop_indexing() -> dict:
    indexer = get_indexer()
    if not indexer.is_running:
        return {"status": "not_running"}

    indexer.stop()
    return {"status": "stopping"}


@router.get("/status", response_model=IndexStatusResponse)
def index_status() -> IndexStatusResponse:
    indexer = get_indexer()
    p = indexer.progress
    return IndexStatusResponse(**p.to_dict())


@router.get("/stats", response_model=IndexStatsResponse)
def index_stats() -> IndexStatsResponse:
    vs_stats = vectorstore.get_stats()
    fs_stats = filestate.get_stats()
    return IndexStatsResponse(
        total_files_indexed=vs_stats["total_files_indexed"],
        file_state_stats=fs_stats,
    )
