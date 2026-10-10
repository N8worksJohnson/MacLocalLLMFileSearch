"""Search and chat endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse

from llmfilesearch.api.schemas import ChatRequest, SearchRequest, SearchResponse
from llmfilesearch.core import chat as chat_module
from llmfilesearch.core import searcher

router = APIRouter(prefix="/api", tags=["search"])


@router.post("/search", response_model=SearchResponse)
def search_files(req: SearchRequest) -> SearchResponse:
    try:
        results = searcher.search(
            query=req.query,
            n_results=req.n_results,
            file_type=req.file_type,
            directory=req.directory,
            modified_after=req.modified_after,
            modified_before=req.modified_before,
        )
        return SearchResponse(results=results)
    except FileNotFoundError:
        return JSONResponse(
            status_code=503,
            content={"error": "No embedding model available. Please download a model in Settings."},
        )


@router.post("/chat")
def chat(req: ChatRequest) -> StreamingResponse:
    """Streaming chat search — returns Server-Sent Events."""

    try:
        def event_stream():
            for event in chat_module.chat_search(
                message=req.message,
                conversation_id=req.conversation_id,
            ):
                yield f"data: {json.dumps(event)}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except FileNotFoundError:
        return JSONResponse(
            status_code=503,
            content={"error": "No embedding model available. Please download a model in Settings."},
        )


@router.delete("/chat/{conversation_id}")
def delete_conversation(conversation_id: str) -> dict:
    chat_module.delete_conversation(conversation_id)
    return {"status": "deleted"}
