"""Pydantic request/response models for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Search ────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    n_results: int = 20
    file_type: str | None = None
    directory: str | None = None
    modified_after: str | None = None
    modified_before: str | None = None


class FileResultSchema(BaseModel):
    id: str = ""
    file_path: str
    file_name: str
    summary: str = ""
    score: float = 0.0
    metadata: dict = {}


class SearchResponse(BaseModel):
    results: list[FileResultSchema]


# ── Chat ──────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


# ── Indexing ──────────────────────────────────────────────────────────

class IndexStartRequest(BaseModel):
    directories: list[str] | None = None  # None = use settings
    full_rescan: bool = False


class IndexStatusResponse(BaseModel):
    state: str
    files_discovered: int = 0
    files_to_process: int = 0
    files_processed: int = 0
    files_failed: int = 0
    files_deleted: int = 0
    current_file: str = ""
    elapsed_seconds: float = 0.0
    error: str | None = None


class IndexStatsResponse(BaseModel):
    total_files_indexed: int
    file_state_stats: dict = {}


# ── Files ─────────────────────────────────────────────────────────────

class FileOpenRequest(BaseModel):
    file_path: str


# ── Settings ──────────────────────────────────────────────────────────

class SettingsResponse(BaseModel):
    scan_directories: list[str] = []
    exclude_patterns: list[str] = []
    max_file_size_mb: int = 100
    auto_scan: bool = False
    scan_interval_hours: int = 24
    theme: str = "dark"
    embedding_model: str | None = None
    chat_model: str | None = None
    setup_complete: bool = False


class SettingsUpdateRequest(BaseModel):
    scan_directories: list[str] | None = None
    exclude_patterns: list[str] | None = None
    max_file_size_mb: int | None = None
    auto_scan: bool | None = None
    scan_interval_hours: int | None = None
    theme: str | None = None
    embedding_model: str | None = None
    chat_model: str | None = None
    setup_complete: bool | None = None


# ── Models ────────────────────────────────────────────────────────────

class ModelDownloadRequest(BaseModel):
    model_id: str
    model_type: str  # "embedding" or "chat"


class ModelDownloadStatus(BaseModel):
    filename: str = ""
    total_bytes: int = 0
    downloaded_bytes: int = 0
    percent: float = 0.0
    speed_bps: float = 0.0
    status: str = "idle"
    error: str | None = None


class ModelSelectRequest(BaseModel):
    model_type: str  # "embedding" or "chat"
    filename: str


# ── System ────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    models_loaded: dict[str, bool] = {}
    db_ready: bool = False


class SystemInfoResponse(BaseModel):
    platform: str
    arch: str
    total_ram_gb: float
    available_ram_gb: float
    has_metal: bool
    has_cuda: bool
    cpu_count: int
    recommended_profile: str
