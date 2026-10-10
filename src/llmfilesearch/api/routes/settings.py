"""Settings CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from llmfilesearch.api.schemas import SettingsResponse, SettingsUpdateRequest
from llmfilesearch.db import settings_store

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
def get_settings() -> SettingsResponse:
    data = settings_store.get_all()
    return SettingsResponse(**{k: v for k, v in data.items() if k in SettingsResponse.model_fields})


@router.put("")
def update_settings(req: SettingsUpdateRequest) -> SettingsResponse:
    updates = req.model_dump(exclude_none=True)
    if updates:
        settings_store.update(updates)
    data = settings_store.get_all()
    return SettingsResponse(**{k: v for k, v in data.items() if k in SettingsResponse.model_fields})
