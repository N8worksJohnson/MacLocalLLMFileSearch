"""Conversational file search with LLM-powered responses."""

from __future__ import annotations

import logging
import uuid
from typing import Generator

from llmfilesearch.config import get_config
from llmfilesearch.constants import CHAT_SYSTEM_PROMPT
from llmfilesearch.core.models import load_chat_model
from llmfilesearch.core.searcher import search

logger = logging.getLogger(__name__)


class Conversation:
    """Manages a single chat conversation with search context."""

    def __init__(self, conversation_id: str | None = None) -> None:
        self.id = conversation_id or str(uuid.uuid4())
        self.history: list[dict] = []  # {"role": "user"|"assistant", "content": "..."}

    def add_user_message(self, content: str) -> None:
        self.history.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str) -> None:
        self.history.append({"role": "assistant", "content": content})

    def get_trimmed_history(self, max_turns: int) -> list[dict]:
        """Return the last N turns of conversation."""
        # Each turn = 1 user + 1 assistant message = 2 entries
        max_entries = max_turns * 2
        if len(self.history) > max_entries:
            return self.history[-max_entries:]
        return list(self.history)


# Store active conversations
_conversations: dict[str, Conversation] = {}


def get_or_create_conversation(conversation_id: str | None = None) -> Conversation:
    """Get an existing conversation or create a new one."""
    if conversation_id and conversation_id in _conversations:
        return _conversations[conversation_id]
    conv = Conversation(conversation_id)
    _conversations[conv.id] = conv
    return conv


def delete_conversation(conversation_id: str) -> None:
    _conversations.pop(conversation_id, None)


def chat_search(
    message: str,
    conversation_id: str | None = None,
) -> Generator[dict, None, None]:
    """Process a chat message: search, then stream an LLM response.

    Yields dicts with:
        {"type": "results", "data": [search results]}
        {"type": "token", "data": "text chunk"}
        {"type": "done", "data": {"conversation_id": "..."}}
    """
    config = get_config()
    conv = get_or_create_conversation(conversation_id)
    conv.add_user_message(message)

    # Step 1: Search for relevant files
    results = search(query=message, n_results=config.chat_top_k)
    yield {"type": "results", "data": results}

    # Step 2: Build context from search results
    context_parts = []
    for i, result in enumerate(results, 1):
        context_parts.append(
            f"[{i}] {result['file_path']}\n"
            f"Type: {result['metadata'].get('file_type', 'unknown')}\n"
            f"Summary: {result.get('summary', 'No summary')}\n"
            f"Relevance: {result['score']:.0%}"
        )

    search_context = "\n\n".join(context_parts) if context_parts else "No relevant files found."

    # Step 3: Build messages for LLM
    messages = [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT},
        {
            "role": "system",
            "content": f"Search results for the user's query:\n\n{search_context}",
        },
    ]

    # Add conversation history (trimmed)
    history = conv.get_trimmed_history(config.chat_max_history_turns)
    messages.extend(history)

    # Step 4: Stream LLM response
    model = load_chat_model()
    response_text = ""

    stream = model.create_chat_completion(
        messages=messages,
        max_tokens=1024,
        temperature=0.3,
        stream=True,
    )

    for chunk in stream:
        delta = chunk["choices"][0].get("delta", {})
        token = delta.get("content", "")
        if token:
            response_text += token
            yield {"type": "token", "data": token}

    # Save assistant response to history
    conv.add_assistant_message(response_text)

    yield {
        "type": "done",
        "data": {"conversation_id": conv.id},
    }
