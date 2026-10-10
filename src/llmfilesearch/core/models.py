"""LLM model loading, lifecycle management, and hardware detection."""

from __future__ import annotations

import hashlib
import logging
import os
import platform
import shutil
import struct
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Generator

import httpx
from llama_cpp import Llama

from llmfilesearch.config import get_config, get_models_dir
from llmfilesearch.constants import CHAT_MODELS, EMBEDDING_MODELS

logger = logging.getLogger(__name__)


@dataclass
class HardwareInfo:
    """Detected hardware capabilities."""

    total_ram_gb: float
    available_ram_gb: float
    platform: str  # "darwin", "win32", "linux"
    arch: str  # "arm64", "x86_64"
    has_metal: bool  # Apple Silicon GPU
    has_cuda: bool  # NVIDIA GPU
    cpu_count: int


def detect_hardware() -> HardwareInfo:
    """Detect system hardware for model recommendations."""
    import psutil

    mem = psutil.virtual_memory()

    sys_platform = platform.system().lower()
    if sys_platform == "darwin":
        plat = "darwin"
    elif sys_platform == "windows":
        plat = "win32"
    else:
        plat = "linux"

    arch = platform.machine().lower()
    has_metal = plat == "darwin" and arch == "arm64"

    # Basic CUDA check — look for nvidia-smi
    has_cuda = shutil.which("nvidia-smi") is not None

    return HardwareInfo(
        total_ram_gb=round(mem.total / (1024**3), 1),
        available_ram_gb=round(mem.available / (1024**3), 1),
        platform=plat,
        arch=arch,
        has_metal=has_metal,
        has_cuda=has_cuda,
        cpu_count=os.cpu_count() or 1,
    )


def recommend_profile(hw: HardwareInfo) -> str:
    """Recommend a model profile based on hardware."""
    if hw.total_ram_gb >= 32:
        return "quality"
    elif hw.total_ram_gb >= 16:
        return "standard"
    return "light"


def get_available_models() -> dict:
    """Return all available models grouped by type."""
    return {
        "embedding": EMBEDDING_MODELS,
        "chat": CHAT_MODELS,
    }


def get_model_path(filename: str) -> Path | None:
    """Return the path to a downloaded model, or None if not found."""
    path = get_models_dir() / filename
    if path.is_file():
        return path
    return None


def list_downloaded_models() -> list[dict]:
    """List all GGUF files in the models directory."""
    models_dir = get_models_dir()
    downloaded = []
    for f in models_dir.glob("*.gguf"):
        downloaded.append({
            "filename": f.name,
            "size_bytes": f.stat().st_size,
            "path": str(f),
        })
    return downloaded


# ── Model download ────────────────────────────────────────────────────


@dataclass
class DownloadProgress:
    """Progress info for a model download."""

    filename: str
    total_bytes: int
    downloaded_bytes: int
    speed_bps: float = 0.0
    status: str = "downloading"  # downloading, verifying, complete, failed
    error: str | None = None

    @property
    def percent(self) -> float:
        if self.total_bytes == 0:
            return 0.0
        return min(100.0, (self.downloaded_bytes / self.total_bytes) * 100)


def download_model(
    url: str,
    filename: str,
    expected_size: int = 0,
    expected_sha256: str = "",
) -> Generator[DownloadProgress, None, Path]:
    """Download a GGUF model with progress reporting and resume support.

    Yields DownloadProgress updates. The final return value is the file path.
    Usage:
        gen = download_model(url, filename)
        try:
            while True:
                progress = next(gen)
                # update UI with progress
        except StopIteration as e:
            file_path = e.value
    """
    dest = get_models_dir() / filename
    partial = dest.with_suffix(dest.suffix + ".partial")

    # Resume support: check for partial download
    resume_from = 0
    if partial.is_file():
        resume_from = partial.stat().st_size
        logger.info("Resuming download of %s from byte %d", filename, resume_from)

    headers = {}
    if resume_from > 0:
        headers["Range"] = f"bytes={resume_from}-"

    progress = DownloadProgress(
        filename=filename,
        total_bytes=expected_size or 0,
        downloaded_bytes=resume_from,
    )

    try:
        with httpx.stream("GET", url, headers=headers, follow_redirects=True, timeout=30.0) as resp:
            resp.raise_for_status()

            # Update total size from Content-Length or Content-Range
            if "content-range" in resp.headers:
                # Format: bytes 1000-9999/10000
                total_str = resp.headers["content-range"].split("/")[-1]
                progress.total_bytes = int(total_str)
            elif "content-length" in resp.headers:
                content_len = int(resp.headers["content-length"])
                progress.total_bytes = resume_from + content_len

            mode = "ab" if resume_from > 0 else "wb"
            with open(partial, mode) as f:
                import time

                last_time = time.monotonic()
                last_bytes = progress.downloaded_bytes

                for chunk in resp.iter_bytes(chunk_size=1024 * 256):  # 256KB chunks
                    f.write(chunk)
                    progress.downloaded_bytes += len(chunk)

                    # Calculate speed every 0.5s
                    now = time.monotonic()
                    elapsed = now - last_time
                    if elapsed >= 0.5:
                        delta_bytes = progress.downloaded_bytes - last_bytes
                        progress.speed_bps = delta_bytes / elapsed
                        last_time = now
                        last_bytes = progress.downloaded_bytes

                    yield progress

        # Verify SHA-256 if provided
        if expected_sha256:
            progress.status = "verifying"
            yield progress

            sha = hashlib.sha256()
            with open(partial, "rb") as f:
                while True:
                    chunk = f.read(1024 * 1024)
                    if not chunk:
                        break
                    sha.update(chunk)

            if sha.hexdigest() != expected_sha256:
                progress.status = "failed"
                progress.error = "SHA-256 checksum mismatch"
                yield progress
                partial.unlink(missing_ok=True)
                raise ValueError(f"Checksum mismatch for {filename}")

        # Move partial to final destination
        partial.rename(dest)
        progress.status = "complete"
        yield progress
        return dest

    except httpx.HTTPError as e:
        progress.status = "failed"
        progress.error = str(e)
        yield progress
        raise


# ── Model loading ─────────────────────────────────────────────────────

_embedding_model: Llama | None = None
_chat_model: Llama | None = None
_embedding_model_path: str | None = None
_chat_model_path: str | None = None
_embedding_lock = threading.Lock()
_chat_lock = threading.Lock()


def _determine_gpu_layers(hw: HardwareInfo | None = None) -> int:
    """Determine how many layers to offload to GPU."""
    if hw is None:
        try:
            hw = detect_hardware()
        except Exception:
            return 0

    if hw.has_metal:
        return -1  # Offload all layers to Metal
    if hw.has_cuda:
        return -1  # Offload all layers to CUDA
    return 0  # CPU only


def load_embedding_model(model_path: str | Path | None = None) -> Llama:
    """Load the embedding model. Uses cached instance if already loaded."""
    global _embedding_model, _embedding_model_path

    path_str = str(model_path) if model_path else None

    # Fast path: already loaded
    if _embedding_model is not None and _embedding_model_path == path_str:
        return _embedding_model

    with _embedding_lock:
        # Check again under lock
        if _embedding_model is not None and _embedding_model_path == path_str:
            return _embedding_model

        if model_path is None:
            # Try to find a downloaded embedding model
            for model_info in EMBEDDING_MODELS:
                found = get_model_path(model_info["filename"])
                if found:
                    model_path = found
                    break

        if model_path is None:
            raise FileNotFoundError(
                "No embedding model found. Please download a model first."
            )

        config = get_config()
        n_gpu = _determine_gpu_layers()

        logger.info("Loading embedding model from %s (n_gpu_layers=%d)", model_path, n_gpu)
        _embedding_model = Llama(
            model_path=str(model_path),
            embedding=True,
            n_ctx=config.embedding_context_length,
            n_gpu_layers=n_gpu,
            verbose=False,
        )
        _embedding_model_path = str(model_path)
        logger.info("Embedding model loaded successfully")
        return _embedding_model


def load_chat_model(model_path: str | Path | None = None) -> Llama:
    """Load the chat/summarization model. Uses cached instance if already loaded."""
    global _chat_model, _chat_model_path

    path_str = str(model_path) if model_path else None

    # Fast path: already loaded
    if _chat_model is not None and _chat_model_path == path_str:
        return _chat_model

    with _chat_lock:
        # Check again under lock
        if _chat_model is not None and _chat_model_path == path_str:
            return _chat_model

        if model_path is None:
            # Try to find a downloaded chat model
            for model_info in CHAT_MODELS:
                found = get_model_path(model_info["filename"])
                if found:
                    model_path = found
                    break

        if model_path is None:
            raise FileNotFoundError(
                "No chat model found. Please download a model first."
            )

        config = get_config()
        n_gpu = _determine_gpu_layers()

        logger.info("Loading chat model from %s (n_gpu_layers=%d)", model_path, n_gpu)
        _chat_model = Llama(
            model_path=str(model_path),
            n_ctx=config.chat_context_length,
            n_gpu_layers=n_gpu,
            verbose=False,
        )
        _chat_model_path = str(model_path)
        logger.info("Chat model loaded successfully")
        return _chat_model


def unload_models() -> None:
    """Unload all models from memory."""
    global _embedding_model, _chat_model, _embedding_model_path, _chat_model_path
    _embedding_model = None
    _chat_model = None
    _embedding_model_path = None
    _chat_model_path = None
    logger.info("All models unloaded")


def models_are_loaded() -> dict[str, bool]:
    """Check which models are currently loaded."""
    return {
        "embedding": _embedding_model is not None,
        "chat": _chat_model is not None,
    }
