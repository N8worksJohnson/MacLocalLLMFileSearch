"""Application entry point: starts FastAPI server + pywebview window."""

from __future__ import annotations

import logging
import sys
import threading

import uvicorn

from llmfilesearch.config import get_config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _start_server(config) -> None:
    """Run the uvicorn server in a background thread."""
    uvicorn.run(
        "llmfilesearch.api.app:create_app",
        factory=True,
        host=config.host,
        port=config.port,
        log_level="warning",
    )


def main() -> None:
    """Main entry point."""
    config = get_config()

    # Check for --server-only flag (useful for development)
    if "--server-only" in sys.argv:
        logger.info("Starting in server-only mode on %s:%d", config.host, config.port)
        uvicorn.run(
            "llmfilesearch.api.app:create_app",
            factory=True,
            host=config.host,
            port=config.port,
            reload="--reload" in sys.argv,
            log_level="info",
        )
        return

    # Start the FastAPI server in a background thread
    server_thread = threading.Thread(
        target=_start_server,
        args=(config,),
        daemon=True,
        name="uvicorn",
    )
    server_thread.start()

    # Wait for server to be ready
    from llmfilesearch.desktop.window import wait_for_server

    logger.info("Waiting for server to start...")
    if not wait_for_server(config.host, config.port):
        logger.error("Server failed to start within timeout")
        sys.exit(1)

    logger.info("Server ready at http://%s:%d", config.host, config.port)

    # Open the desktop window — this blocks until the window is closed
    from llmfilesearch.desktop.window import create_window, start_window

    create_window()
    start_window(debug="--debug" in sys.argv)

    logger.info("Window closed, shutting down")


if __name__ == "__main__":
    main()
