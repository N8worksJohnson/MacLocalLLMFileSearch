"""Health and system info endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from llmfilesearch.api.schemas import HealthResponse, SystemInfoResponse
from llmfilesearch.constants import VERSION
from llmfilesearch.core.models import detect_hardware, models_are_loaded, recommend_profile

router = APIRouter(prefix="/api/status", tags=["status"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=VERSION,
        models_loaded=models_are_loaded(),
        db_ready=True,
    )


@router.get("/system", response_model=SystemInfoResponse)
def system_info() -> SystemInfoResponse:
    hw = detect_hardware()
    return SystemInfoResponse(
        platform=hw.platform,
        arch=hw.arch,
        total_ram_gb=hw.total_ram_gb,
        available_ram_gb=hw.available_ram_gb,
        has_metal=hw.has_metal,
        has_cuda=hw.has_cuda,
        cpu_count=hw.cpu_count,
        recommended_profile=recommend_profile(hw),
    )
