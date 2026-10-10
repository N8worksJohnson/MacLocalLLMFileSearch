"""Full indexing pipeline orchestrator — runs in a background thread."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from threading import Event, Thread
from typing import Callable

from llmfilesearch.constants import FILE_TYPE_MAP, METADATA_ONLY_EXTENSIONS
from llmfilesearch.core.embedder import build_embedding_text, embed_text
from llmfilesearch.core.extractor import extract_file
from llmfilesearch.core.scanner import FileJob, scan_directories
from llmfilesearch.core.summarizer import summarize_metadata, summarize_text
from llmfilesearch.db import filestate, vectorstore

# File types where the raw text is perfectly good as-is for embedding —
# no LLM summary needed.  The embedding model can understand code, config,
# and short text directly, which is 10-100x faster than calling the chat model.
_FAST_PATH_TYPES = {"code", "text"}
# Threshold: if the extracted text is shorter than this, just use it directly.
_FAST_PATH_MAX_CHARS = 3000
# For medium files we still call the LLM, but we cap the input to avoid
# multi-chunk hierarchical summarisation.  One call ≈ 3-8 s on a 3B model.
_SINGLE_CALL_MAX_CHARS = 12000

logger = logging.getLogger(__name__)


@dataclass
class IndexProgress:
    """Shared state for tracking indexing progress."""

    state: str = "idle"  # idle, scanning, indexing, stopping, complete, error
    files_discovered: int = 0
    files_to_process: int = 0
    files_processed: int = 0
    files_failed: int = 0
    files_deleted: int = 0
    current_file: str = ""
    elapsed_seconds: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "state": self.state,
            "files_discovered": self.files_discovered,
            "files_to_process": self.files_to_process,
            "files_processed": self.files_processed,
            "files_failed": self.files_failed,
            "files_deleted": self.files_deleted,
            "current_file": self.current_file,
            "elapsed_seconds": round(self.elapsed_seconds, 1),
            "error": self.error,
        }


class Indexer:
    """Manages the background indexing pipeline."""

    def __init__(self) -> None:
        self.progress = IndexProgress()
        self._cancel_event = Event()
        self._thread: Thread | None = None
        self._progress_callback: Callable[[IndexProgress], None] | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(
        self,
        directories: list[str],
        exclude_patterns: list[str] | None = None,
        full_rescan: bool = False,
        progress_callback: Callable[[IndexProgress], None] | None = None,
    ) -> None:
        """Start the indexing pipeline in a background thread."""
        if self.is_running:
            raise RuntimeError("Indexing is already in progress")

        self._cancel_event.clear()
        self.progress = IndexProgress(state="scanning")
        self._progress_callback = progress_callback

        if full_rescan:
            filestate.clear_all()
            vectorstore.reset_collection()

        self._thread = Thread(
            target=self._run,
            args=(directories, exclude_patterns),
            daemon=True,
            name="indexer",
        )
        self._thread.start()

    def stop(self) -> None:
        """Request the indexer to stop."""
        self._cancel_event.set()
        self.progress.state = "stopping"
        self._notify_progress()

    def _notify_progress(self) -> None:
        if self._progress_callback:
            try:
                self._progress_callback(self.progress)
            except Exception:
                pass

    def _run(self, directories: list[str], exclude_patterns: list[str] | None) -> None:
        """Main indexing loop (runs in background thread)."""
        start_time = time.monotonic()

        try:
            # Phase 1: Scan directories
            self.progress.state = "scanning"
            self._notify_progress()

            scan_result = scan_directories(
                directories=directories,
                exclude_patterns=exclude_patterns,
                cancel_event=self._cancel_event,
            )

            if self._cancel_event.is_set():
                self.progress.state = "idle"
                self._notify_progress()
                return

            self.progress.files_discovered = scan_result.total_discovered
            self.progress.files_to_process = len(scan_result.files_to_process)

            # Phase 2: Handle deletions
            if scan_result.files_deleted:
                vectorstore.delete_files_batch(scan_result.files_deleted)
                filestate.remove_files_batch(scan_result.files_deleted)
                self.progress.files_deleted = len(scan_result.files_deleted)
                logger.info("Removed %d deleted files from index", len(scan_result.files_deleted))

            # Phase 3: Process files
            self.progress.state = "indexing"
            self._notify_progress()

            for job in scan_result.files_to_process:
                if self._cancel_event.is_set():
                    break

                self.progress.current_file = job.path
                self.progress.elapsed_seconds = time.monotonic() - start_time
                self._notify_progress()

                try:
                    self._process_file(job)
                    self.progress.files_processed += 1
                except Exception as e:
                    logger.error("Failed to index %s: %s", job.path, e)
                    self.progress.files_failed += 1
                    filestate.mark_failed(job.path, job.size, job.mtime, str(e))

            # Done
            self.progress.state = "complete"
            self.progress.current_file = ""
            self.progress.elapsed_seconds = time.monotonic() - start_time
            self._notify_progress()

            logger.info(
                "Indexing complete: %d processed, %d failed, %d deleted (%.1fs)",
                self.progress.files_processed,
                self.progress.files_failed,
                self.progress.files_deleted,
                self.progress.elapsed_seconds,
            )

        except Exception as e:
            logger.exception("Indexer encountered an error: %s", e)
            self.progress.state = "error"
            self.progress.error = str(e)
            self._notify_progress()

    # ── Smart summarisation ───────────────────────────────────────────

    @staticmethod
    def _smart_summarize(extraction, file_name: str, file_type: str, extension: str) -> str:
        """Choose the fastest adequate summarisation strategy.

        Fast path  – use the raw extracted text directly (code, short text).
        Single LLM – one call for medium-length documents.
        Full LLM   – hierarchical chunked summarisation for long docs.
        Metadata   – media files with no text content.
        """
        # No text at all → metadata summary or fallback label
        if not extraction.has_text or not extraction.text.strip():
            if extraction.metadata:
                return summarize_metadata(extraction.metadata, file_name=file_name)
            return f"{file_type} file: {file_name}"

        text = extraction.text.strip()
        text_len = len(text)

        # Fast path: short files or code/text files under threshold
        if text_len <= _FAST_PATH_MAX_CHARS or (
            file_type in _FAST_PATH_TYPES and text_len <= _FAST_PATH_MAX_CHARS * 3
        ):
            # Truncate for the summary field (kept short for display)
            return text[:1500].strip()

        # Single LLM call: medium-length docs — send a truncated version
        if text_len <= _SINGLE_CALL_MAX_CHARS:
            return summarize_text(text, file_name=file_name)

        # Long docs: send just the beginning to keep it to one LLM call
        # (instead of hierarchical multi-chunk which is 3-5× slower)
        truncated = text[:_SINGLE_CALL_MAX_CHARS]
        return summarize_text(truncated, file_name=file_name)

    # ── File processing pipeline ───────────────────────────────────────

    def _process_file(self, job: FileJob) -> None:
        """Process a single file through the full pipeline."""
        t0 = time.monotonic()
        file_name = os.path.basename(job.path)
        file_type = FILE_TYPE_MAP.get(job.extension, "other")

        # Step 1: Extract content
        extraction = extract_file(job.path)
        t_extract = time.monotonic()

        if extraction.status == "failed":
            raise RuntimeError(f"Extraction failed: {extraction.error}")

        # Step 2: Summarize (smart — skips LLM when possible)
        summary = self._smart_summarize(extraction, file_name, file_type, job.extension)
        t_summarize = time.monotonic()

        # Step 3: Build embedding text and embed
        embedding_text = build_embedding_text(
            file_name=file_name,
            summary=summary,
            file_type=file_type,
            author=extraction.metadata.get("author", ""),
            title=extraction.metadata.get("title", ""),
        )
        embedding = embed_text(embedding_text)
        t_embed = time.monotonic()

        # Step 4: Build metadata for ChromaDB
        try:
            stat = os.stat(job.path)
            created_at = getattr(stat, "st_birthtime", stat.st_ctime)
        except OSError:
            created_at = job.mtime

        chroma_metadata = {
            "file_path": job.path,
            "file_name": file_name,
            "file_ext": job.extension,
            "file_type": file_type,
            "file_size": job.size,
            "modified_at": job.mtime,
            "created_at": created_at,
            "indexed_at": time.time(),
            "directory": os.path.dirname(job.path),
            "summary": summary[:500],  # cap summary length in metadata
            "has_text": extraction.has_text,
        }

        # Add optional metadata
        if extraction.metadata.get("author"):
            chroma_metadata["author"] = extraction.metadata["author"]
        if extraction.metadata.get("title"):
            chroma_metadata["title"] = extraction.metadata["title"]
        if extraction.metadata.get("page_count"):
            chroma_metadata["page_count"] = extraction.metadata["page_count"]

        # Step 5: Store in ChromaDB
        document_text = f"{file_name}: {summary[:2000]}"
        vectorstore.upsert_file(
            file_path=job.path,
            embedding=embedding,
            document_text=document_text,
            metadata=chroma_metadata,
        )

        # Step 6: Update file state
        filestate.mark_indexed(job.path, job.size, job.mtime)

        used_llm = (t_summarize - t_extract) > 0.5
        logger.info(
            "Indexed %s: extract=%.1fs summary=%.1fs embed=%.1fs total=%.1fs [%s]",
            file_name,
            t_extract - t0,
            t_summarize - t_extract,
            t_embed - t_summarize,
            t_embed - t0,
            "llm" if used_llm else "fast",
        )


# Global indexer instance
_indexer: Indexer | None = None


def get_indexer() -> Indexer:
    global _indexer
    if _indexer is None:
        _indexer = Indexer()
    return _indexer
