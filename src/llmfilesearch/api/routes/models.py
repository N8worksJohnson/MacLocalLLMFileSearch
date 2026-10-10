"""Model management endpoints: list, download, select."""

from __future__ import annotations

import logging
import threading

from fastapi import APIRouter, HTTPException

from llmfilesearch.api.schemas import (
    ModelDownloadRequest,
    ModelDownloadStatus,
    ModelSelectRequest,
)
from llmfilesearch.constants import CHAT_MODELS, EMBEDDING_MODELS
from llmfilesearch.core.models import (
    download_model,
    get_available_models,
    get_model_path,
    list_downloaded_models,
    load_chat_model,
    load_embedding_model,
)
from llmfilesearch.db import settings_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/models", tags=["models"])

# Track active downloads
_download_status: dict[str, ModelDownloadStatus] = {}
_download_lock = threading.Lock()


@router.get("/available")
def available_models() -> dict:
    """List all available models and which are downloaded."""
    models = get_available_models()
    downloaded = {m["filename"] for m in list_downloaded_models()}

    for model_list in models.values():
        for model in model_list:
            model["downloaded"] = model["filename"] in downloaded

    return models


@router.get("/downloaded")
def downloaded_models() -> list[dict]:
    """List all downloaded model files."""
    return list_downloaded_models()


@router.get("/current")
def current_models() -> dict:
    """Get the currently selected models from settings."""
    return {
        "embedding": settings_store.get("embedding_model"),
        "chat": settings_store.get("chat_model"),
    }


@router.post("/download")
def start_download(req: ModelDownloadRequest) -> dict:
    """Start downloading a model in the background."""
    # Find the model info
    all_models = EMBEDDING_MODELS if req.model_type == "embedding" else CHAT_MODELS
    model_info = None
    for m in all_models:
        if m["id"] == req.model_id:
            model_info = m
            break

    if model_info is None:
        raise HTTPException(status_code=404, detail=f"Model not found: {req.model_id}")

    # Check if already downloading
    with _download_lock:
        if req.model_id in _download_status and _download_status[req.model_id].status == "downloading":
            return {"status": "already_downloading", "model_id": req.model_id}

        _download_status[req.model_id] = ModelDownloadStatus(
            filename=model_info["filename"],
            total_bytes=model_info.get("size_bytes", 0),
            status="downloading",
        )

    def _download_thread():
        try:
            gen = download_model(
                url=model_info["url"],
                filename=model_info["filename"],
                expected_size=model_info.get("size_bytes", 0),
                expected_sha256=model_info.get("sha256", ""),
            )
            for progress in gen:
                with _download_lock:
                    _download_status[req.model_id] = ModelDownloadStatus(
                        filename=progress.filename,
                        total_bytes=progress.total_bytes,
                        downloaded_bytes=progress.downloaded_bytes,
                        percent=progress.percent,
                        speed_bps=progress.speed_bps,
                        status=progress.status,
                        error=progress.error,
                    )
        except Exception as e:
            logger.error("Download failed for %s: %s", req.model_id, e)
            with _download_lock:
                _download_status[req.model_id] = ModelDownloadStatus(
                    filename=model_info["filename"],
                    status="failed",
                    error=str(e),
                )

    thread = threading.Thread(target=_download_thread, daemon=True)
    thread.start()

    return {"status": "started", "model_id": req.model_id}


@router.get("/download/status")
def download_status() -> dict[str, ModelDownloadStatus]:
    """Get download progress for all active/recent downloads."""
    with _download_lock:
        return dict(_download_status)


@router.post("/select")
def select_model(req: ModelSelectRequest) -> dict:
    """Select a downloaded model for use."""
    path = get_model_path(req.filename)
    if path is None:
        raise HTTPException(status_code=404, detail=f"Model file not found: {req.filename}")

    if req.model_type == "embedding":
        settings_store.set("embedding_model", req.filename)
        load_embedding_model(path)
    elif req.model_type == "chat":
        settings_store.set("chat_model", req.filename)
        load_chat_model(path)
    else:
        raise HTTPException(status_code=400, detail=f"Invalid model_type: {req.model_type}")

    return {"status": "selected", "model_type": req.model_type, "filename": req.filename}
