"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from llmfilesearch.config import get_bundle_dir
from llmfilesearch.constants import VERSION
from llmfilesearch.db import filestate, settings_store

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    filestate.init_db()
    settings_store.init_db()
    logger.info("Databases initialized")
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="LLMFileSearch",
        version=VERSION,
        docs_url="/api/docs",
        redoc_url=None,
        lifespan=lifespan,
    )

    # CORS — allow the frontend dev server and the pywebview window
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:8741", "http://localhost:8741", "http://127.0.0.1:5173", "http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routes
    from llmfilesearch.api.routes import files, index, models, search, settings, status
    from llmfilesearch.api import websocket

    app.include_router(status.router)
    app.include_router(search.router)
    app.include_router(index.router)
    app.include_router(files.router)
    app.include_router(settings.router)
    app.include_router(models.router)
    app.include_router(websocket.router)

    # Serve the built frontend as static files
    # In production (PyInstaller), frontend dist is in the bundle
    # In development, the Vite dev server is used instead
    static_dir = _find_static_dir()
    if static_dir and static_dir.is_dir():
        # Serve static assets
        app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")

        # Serve index.html for all non-API routes (SPA fallback)
        from fastapi.responses import FileResponse

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str) -> FileResponse:
            # Don't interfere with API routes
            if full_path.startswith("api/") or full_path.startswith("ws/"):
                from fastapi.responses import JSONResponse
                return JSONResponse({"error": "not found"}, status_code=404)

            file_path = (static_dir / full_path).resolve()
            if file_path.is_file() and file_path.is_relative_to(static_dir.resolve()):
                return FileResponse(str(file_path))
            return FileResponse(str(static_dir / "index.html"))

        logger.info("Serving frontend from %s", static_dir)
    else:
        logger.info("No frontend build found; API-only mode")

    return app


def _find_static_dir() -> Path | None:
    """Locate the frontend dist directory."""
    # Check bundled location (PyInstaller)
    bundle = get_bundle_dir()
    candidate = bundle / "frontend" / "dist"
    if candidate.is_dir():
        return candidate

    # Check development location
    candidate = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "dist"
    if candidate.is_dir():
        return candidate

    return None
