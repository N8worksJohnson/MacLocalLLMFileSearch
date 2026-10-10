"""File detail and OS operations (open, reveal)."""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from llmfilesearch.api.schemas import FileOpenRequest
from llmfilesearch.db import settings_store

router = APIRouter(prefix="/api/files", tags=["files"])


def _validate_file_path(file_path: str) -> bool:
    """Ensure the file path is within configured scan directories."""
    try:
        resolved = Path(file_path).resolve()
        scan_dirs = settings_store.get("scan_directories") or []
        for scan_dir in scan_dirs:
            if resolved.is_relative_to(Path(scan_dir).resolve()):
                return True
        return False
    except (ValueError, OSError):
        return False


@router.post("/open")
def open_file(req: FileOpenRequest) -> dict:
    """Open a file with the OS default application."""
    if not _validate_file_path(req.file_path):
        return JSONResponse(
            status_code=403,
            content={"error": "File path not within scan directories"},
        )

    if not os.path.isfile(req.file_path):
        raise HTTPException(status_code=404, detail="File not found")

    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.Popen(["open", req.file_path])
        elif system == "Windows":
            os.startfile(req.file_path)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", req.file_path])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "opened"}


@router.post("/reveal")
def reveal_file(req: FileOpenRequest) -> dict:
    """Reveal a file in Finder / Explorer."""
    if not _validate_file_path(req.file_path):
        return JSONResponse(
            status_code=403,
            content={"error": "File path not within scan directories"},
        )

    if not os.path.exists(req.file_path):
        raise HTTPException(status_code=404, detail="File not found")

    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.Popen(["open", "-R", req.file_path])
        elif system == "Windows":
            subprocess.Popen(["explorer", "/select,", req.file_path])
        else:
            # Linux: open the directory
            subprocess.Popen(["xdg-open", os.path.dirname(req.file_path)])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "revealed"}
