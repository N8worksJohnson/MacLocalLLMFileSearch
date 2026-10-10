"""PyWebView window creation and lifecycle management."""

from __future__ import annotations

import logging
import platform
import threading
import time

import webview

from llmfilesearch.config import get_config

logger = logging.getLogger(__name__)

_window: webview.Window | None = None


def create_window(
    title: str = "LLM File Search",
    width: int = 1200,
    height: int = 800,
) -> webview.Window:
    """Create the main application window pointing to the local server."""
    global _window
    config = get_config()
    url = f"http://{config.host}:{config.port}"

    _window = webview.create_window(
        title=title,
        url=url,
        width=width,
        height=height,
        min_size=(800, 600),
        resizable=True,
    )

    return _window


def start_window(debug: bool = False) -> None:
    """Start the pywebview event loop. Blocks until window is closed."""
    gui = None
    if platform.system() == "Darwin":
        gui = "cocoa"

    webview.start(debug=debug, gui=gui)


def wait_for_server(host: str, port: int, timeout: float = 30.0) -> bool:
    """Wait for the FastAPI server to be ready before opening the window."""
    import httpx

    url = f"http://{host}:{port}/api/status/health"
    start = time.monotonic()

    while time.monotonic() - start < timeout:
        try:
            resp = httpx.get(url, timeout=2.0)
            if resp.status_code == 200:
                return True
        except (httpx.ConnectError, httpx.TimeoutException):
            pass
        time.sleep(0.2)

    return False
