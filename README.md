# MacLocalLLMFileSearch

A local, privacy-first file search tool powered by LLMs. Scans your filesystem, understands file contents using AI running entirely on your machine, and lets you find any file by describing what's in it.

**Your files never leave your computer.**

## What it does

1. **Scans** your chosen directories and extracts content from documents, code, images, audio, and video
2. **Understands** each file using a local LLM (summarization + embedding)
3. **Searches** semantically — describe what you're looking for in plain English
4. **Chats** — ask follow-up questions about your files in a conversational interface

Instead of remembering filenames or folder structures, just ask:
- *"Find that spreadsheet with Q3 revenue projections"*
- *"Where's the photo I took in Hawaii last year?"*
- *"Which Python file handles the database migrations?"*

## Tech Stack

- **LLM Backend:** [llama-cpp-python](https://github.com/abetlen/llama-cpp-python) with GGUF models
- **Embedding Model:** Nomic Embed Text v1.5 (768-dim, ~262MB)
- **Chat Model:** Qwen 2.5 family (0.5B / 1.5B / 3B, selected based on hardware)
- **Vector Database:** [ChromaDB](https://www.trychroma.com/) (local, persistent)
- **File State:** SQLite with WAL mode
- **API:** FastAPI with SSE streaming and WebSocket progress
- **Frontend:** Svelte 5 + Vite (compiled to static files)
- **Desktop:** PyWebView (native OS window)
- **GPU Acceleration:** Apple Metal (macOS), CUDA (NVIDIA)

## Supported File Types

| Category | Extensions |
|----------|-----------|
| Documents | `.pdf`, `.docx`, `.pptx` |
| Spreadsheets | `.xlsx`, `.csv`, `.tsv` |
| Text | `.txt`, `.md`, `.json`, `.yaml`, `.xml`, `.html`, `.ini`, `.toml`, `.log` |
| Code | `.py`, `.js`, `.ts`, `.java`, `.c`, `.cpp`, `.go`, `.rs`, `.rb`, `.swift`, and 40+ more |
| Images | `.jpg`, `.png`, `.heic`, `.tiff`, `.webp`, `.svg`, and more (metadata: EXIF, GPS, camera) |
| Video | `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`, and more (metadata: duration, dimensions) |
| Audio | `.mp3`, `.wav`, `.flac`, `.aac`, `.ogg`, and more (metadata: artist, album, duration) |
| Email | `.eml` |

## Requirements

- **macOS** with Apple Silicon (M1/M2/M3/M4) recommended
- **Python 3.11+**
- **Node.js 18+** (for building the frontend)
- **8GB+ RAM** (16GB+ recommended for better models)

## Installation

```bash
# Clone the repo
git clone https://github.com/N8worksJohnson/MacLocalLLMFileSearch.git
cd MacLocalLLMFileSearch

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install llama-cpp-python with Metal support (macOS Apple Silicon)
CMAKE_ARGS="-DGGML_BLAS=OFF -DGGML_ACCELERATE=OFF -DGGML_METAL=ON -DCMAKE_CXX_STANDARD=17" \
  pip install --no-cache-dir llama-cpp-python

# Install the project
pip install -e ".[dev]"

# Build the frontend
cd frontend && npm install && npm run build && cd ..
```

### CUDA (NVIDIA GPU) Installation

```bash
CMAKE_ARGS="-DGGML_CUDA=ON" pip install --no-cache-dir llama-cpp-python
pip install -e ".[dev]"
```

### CPU-only Installation

```bash
pip install --no-cache-dir llama-cpp-python
pip install -e ".[dev]"
```

## Usage

### Desktop App (PyWebView window)

```bash
python -m llmfilesearch.main
```

### Server Mode (browser at localhost:8741)

```bash
python -m llmfilesearch.main --server-only
```

Then open http://127.0.0.1:8741 in your browser.

### First Run

1. The **Setup Wizard** will detect your hardware and recommend a model profile
2. Download the embedding model (~262MB) and a chat model (400MB-2GB)
3. Go to **Settings**, add directories to scan
4. Click **Start Scan** — files are indexed incrementally (only new/changed files)
5. Go to **Search** and start asking questions

## How It Works

### Indexing Pipeline

For each file discovered during a scan:

1. **Extract** — Pull text content (documents, code) or metadata (images, video, audio)
2. **Summarize** — Short files use extracted text directly (fast path). Longer documents get a single LLM summary call
3. **Embed** — Generate a 768-dimensional vector using the embedding model
4. **Store** — Upsert the embedding + metadata into ChromaDB, update file state in SQLite

Subsequent scans are **incremental** — only files with changed size or modification time are reprocessed.

### Search

1. Your query is embedded using the same embedding model
2. ChromaDB finds the most similar file embeddings (cosine similarity)
3. Results are returned with file paths, summaries, and relevance scores

### Chat

1. Your message is used as a search query to find relevant files
2. The top results are injected as context into the chat prompt
3. The chat LLM streams a response that references your actual files

## Project Structure

```
src/llmfilesearch/
  api/           # FastAPI routes, schemas, WebSocket
  core/          # Indexer, scanner, embedder, summarizer, chat, search
  db/            # ChromaDB wrapper, SQLite file state, settings store
  desktop/       # PyWebView window management
  extractors/    # File content extraction (PDF, DOCX, media, etc.)
  config.py      # App configuration and paths
  constants.py   # File types, model registry, prompts
  main.py        # Entry point

frontend/
  src/
    components/  # ChatPanel, FileResult
    pages/       # Search, Settings, Setup wizard
    lib/         # API client, Svelte stores
```

## Configuration

Data is stored in the platform-appropriate location:
- **macOS:** `~/Library/Application Support/LLMFileSearch/`
- **Linux:** `~/.local/share/LLMFileSearch/`
- **Windows:** `%LOCALAPPDATA%/LLMFileSearch/`

This includes downloaded models, ChromaDB data, SQLite databases, and settings.

## Development

```bash
# Run server with auto-reload
python -m llmfilesearch.main --server-only --reload

# Run frontend dev server (hot reload)
cd frontend && npm run dev

# The Vite dev server proxies API calls to localhost:8741
```

## License

MIT License. See [LICENSE](LICENSE) for details.
