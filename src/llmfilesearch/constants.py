"""Application constants — file type mappings, version info, model registry."""

from __future__ import annotations

VERSION = "0.1.0"
APP_DISPLAY_NAME = "LLM File Search"

# ── File type categories ──────────────────────────────────────────────

FILE_TYPE_MAP: dict[str, str] = {}

_CATEGORIES: dict[str, list[str]] = {
    "document": [".pdf", ".docx"],
    "spreadsheet": [".xlsx", ".csv", ".tsv"],
    "presentation": [".pptx"],
    "text": [".txt", ".md", ".markdown", ".rst", ".log", ".ini", ".cfg", ".toml", ".yaml", ".yml", ".xml", ".html", ".htm", ".json", ".jsonl"],
    "code": [
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".cc", ".h", ".hpp",
        ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".kts", ".scala", ".cs", ".vb",
        ".r", ".m", ".mm", ".lua", ".pl", ".pm", ".sh", ".bash", ".zsh", ".fish",
        ".sql", ".graphql", ".proto", ".zig", ".nim", ".dart", ".ex", ".exs",
        ".clj", ".cljs", ".hs", ".erl", ".elm", ".vue", ".svelte",
        ".css", ".scss", ".sass", ".less", ".styl",
        ".makefile", ".cmake", ".gradle", ".sbt",
    ],
    "image": [
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp",
        ".heic", ".heif", ".svg", ".ico", ".raw", ".cr2", ".nef", ".arw",
    ],
    "video": [".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg"],
    "audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a", ".opus", ".aiff"],
    "archive": [".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar"],
    "email": [".eml"],
}

for category, extensions in _CATEGORIES.items():
    for ext in extensions:
        FILE_TYPE_MAP[ext] = category

# Extensions that contain readable text content (we'll try to extract text)
TEXT_EXTRACTABLE_EXTENSIONS: set[str] = set()
for cat in ("document", "spreadsheet", "presentation", "text", "code", "email"):
    for ext in _CATEGORIES[cat]:
        TEXT_EXTRACTABLE_EXTENSIONS.add(ext)

# Extensions where we only read metadata (no text content)
METADATA_ONLY_EXTENSIONS: set[str] = set()
for cat in ("image", "video", "audio", "archive"):
    for ext in _CATEGORIES[cat]:
        METADATA_ONLY_EXTENSIONS.add(ext)

ALL_SUPPORTED_EXTENSIONS: set[str] = TEXT_EXTRACTABLE_EXTENSIONS | METADATA_ONLY_EXTENSIONS

# ── Model registry ────────────────────────────────────────────────────

EMBEDDING_MODELS: list[dict] = [
    {
        "id": "nomic-embed-text-v1.5-Q8_0",
        "name": "Nomic Embed Text v1.5",
        "filename": "nomic-embed-text-v1.5.Q8_0.gguf",
        "url": "https://huggingface.co/nomic-ai/nomic-embed-text-v1.5-GGUF/resolve/main/nomic-embed-text-v1.5.Q8_0.gguf",
        "size_bytes": 274_726_144,
        "sha256": "",  # Fill after first verified download
        "dimensions": 768,
        "context_length": 8192,
        "description": "High-quality text embeddings. Recommended for all hardware profiles.",
    },
]

CHAT_MODELS: list[dict] = [
    {
        "id": "qwen2.5-0.5b-instruct-Q4_K_M",
        "name": "Qwen 2.5 0.5B (Light)",
        "filename": "qwen2.5-0.5b-instruct-q4_k_m.gguf",
        "url": "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf",
        "size_bytes": 397_820_928,
        "sha256": "",
        "context_length": 32768,
        "min_ram_gb": 4,
        "profile": "light",
        "description": "Fast and compact. Best for machines with 8GB RAM.",
    },
    {
        "id": "qwen2.5-1.5b-instruct-Q4_K_M",
        "name": "Qwen 2.5 1.5B (Standard)",
        "filename": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "url": "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "size_bytes": 1_049_804_800,
        "sha256": "",
        "context_length": 32768,
        "min_ram_gb": 8,
        "profile": "standard",
        "description": "Good balance of quality and speed. Recommended for 16GB RAM.",
    },
    {
        "id": "qwen2.5-3b-instruct-Q4_K_M",
        "name": "Qwen 2.5 3B (Quality)",
        "filename": "qwen2.5-3b-instruct-q4_k_m.gguf",
        "url": "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf",
        "size_bytes": 2_048_000_000,
        "sha256": "",
        "context_length": 32768,
        "min_ram_gb": 16,
        "profile": "quality",
        "description": "Highest quality summaries and chat. Best for 32GB+ RAM.",
    },
]

# ── Summarizer prompts ────────────────────────────────────────────────

SUMMARIZE_SYSTEM_PROMPT = (
    "You are a file content summarizer. Given the contents of a file, "
    "produce a concise 1-3 sentence summary. Focus on what the file is about, "
    "its key topics, and any notable details like names, dates, or numbers. "
    "If the text appears to be code, describe what the code does. "
    "Be factual and specific. Do not say 'this file contains'."
)

SUMMARIZE_METADATA_PROMPT = (
    "Summarize this file based only on its metadata. "
    "Include the file type, any dates, dimensions, camera/device info, "
    "and location if available. Be concise (1-2 sentences)."
)

CHAT_SYSTEM_PROMPT = (
    "You are a helpful file search assistant. The user is looking for files "
    "on their computer. You have access to search results from their indexed files. "
    "Answer their question using the search results below. "
    "Always cite file paths when referencing specific files. "
    "If no results seem relevant, say so and suggest a different search query. "
    "Be concise and direct."
)
