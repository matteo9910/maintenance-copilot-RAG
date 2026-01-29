# Maintenance AI Copilot

An intelligent web application that helps industrial maintenance technicians rapidly diagnose and resolve equipment faults by querying technical documentation using **Agentic RAG (Retrieval-Augmented Generation)**.

The system parses maintenance manuals into a vector database and uses a **multi-hop retrieval agent** (powered by LangGraph) to automatically follow cross-references across pages, tables, and sections -- delivering complete, source-cited answers in seconds.

---

## Table of Contents

- [Key Features](#key-features)
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Knowledge Base Ingestion](#knowledge-base-ingestion)
- [API Reference](#api-reference)
- [RAG System Architecture](#rag-system-architecture)
- [Frontend Components](#frontend-components)
- [Development](#development)

---

## Key Features

### Agentic Multi-Hop Retrieval
- **LangGraph-based agent** performs iterative searches across the knowledge base
- Automatically follows document references ("See Table 5-10", "Refer to Page 131")
- Loop detection prevents infinite retrieval cycles
- Configurable iteration limit (default: 5 hops) for safety

### Real-Time Streaming Responses
- Server-Sent Events (SSE) deliver tokens as they are generated
- Live status updates show each retrieval step ("Search 1: lubrication schedule", "Search 2: grease specifications")
- Sub-second Time To First Token (TTFT)

### Trust & Verification Layer
- Every answer cites its source documents (filename, page, section)
- Dedicated Context Panel displays full source excerpts (1000-1500 chars)
- Users can open the original PDF directly from the interface
- Chunk position tracking (e.g., "Segment 3 of 12")

### Multi-Model Support
- Switch between LLMs per query via OpenRouter:
  - Anthropic Claude Sonnet 4
  - OpenAI GPT-4o / GPT-5
  - Google Gemini 3 Pro
- Compare model quality and speed in real-time

### Vision-Based PDF Parsing
- LlamaParse extracts tables with cell-level accuracy
- Preserves complex table structures as markdown
- Automatic fallback to PyPDFLoader if LlamaParse is unavailable

### Multimodal Input
- Upload images of equipment faults or error codes
- LLM analyzes images in context of the maintenance documentation

---

## Architecture Overview

```
+-------------------+        HTTP/SSE         +--------------------+
|                   | <---------------------> |                    |
|  React Frontend   |                         |  FastAPI Backend   |
|  (Vite + TS)      |                         |  (Python)          |
|  Port 3000        |                         |  Port 8000         |
|                   |                         |                    |
+-------------------+                         +--------+-----------+
                                                       |
                                              +--------+-----------+
                                              |                    |
                                              |   RAG Engine       |
                                              |   (LangChain +     |
                                              |    LangGraph)      |
                                              |                    |
                                              +----+----------+----+
                                                   |          |
                                          +--------+--+  +----+----------+
                                          |           |  |               |
                                          | ChromaDB  |  | OpenRouter    |
                                          | (Vectors) |  | (LLM API)    |
                                          |           |  |               |
                                          +-----------+  +---------------+
                                               |
                                          +-----------+
                                          | OpenAI    |
                                          | Embeddings|
                                          +-----------+
```

**Data flow:**
1. User submits a question (+ optional image) from the frontend
2. Backend receives the request and activates the RAG agent
3. The agent searches ChromaDB iteratively, following cross-references
4. Retrieved context is sent to the LLM via OpenRouter for answer generation
5. Tokens are streamed back to the frontend in real-time with source citations

---

## Tech Stack

### Backend
| Component | Technology |
|-----------|-----------|
| Web Framework | FastAPI |
| ASGI Server | Uvicorn |
| RAG Framework | LangChain 0.3+ |
| Agentic RAG | LangGraph 0.2+ |
| Vector Database | ChromaDB (persistent, SQLite-backed) |
| Embeddings | OpenAI `text-embedding-3-small` (1536 dims) |
| LLM Provider | OpenRouter API (multi-model) |
| PDF Parsing | LlamaParse (vision) + PyPDF (fallback) |
| Configuration | Pydantic Settings |

### Frontend
| Component | Technology |
|-----------|-----------|
| Framework | React 19 |
| Language | TypeScript 5.8 |
| Build Tool | Vite 6 |
| Styling | Tailwind CSS |
| Icons | Lucide React |

---

## Project Structure

```
maintenance_ai_copilot/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI entry point, routes, health checks
│   │   ├── core/
│   │   │   └── config.py          # Environment-based settings (Pydantic)
│   │   ├── api/
│   │   │   ├── chat.py            # Chat endpoints (POST /api/chat, /api/chat/stream)
│   │   │   └── documents.py       # Document management (ingest, list, clear)
│   │   ├── rag/
│   │   │   ├── agent.py           # LangGraph agentic multi-hop retrieval
│   │   │   ├── chain.py           # RAG orchestration (agentic + legacy modes)
│   │   │   ├── vector_store.py    # ChromaDB client (singleton pattern)
│   │   │   ├── embeddings.py      # OpenAI embeddings configuration
│   │   │   ├── llm.py             # OpenRouter LLM wrapper + model registry
│   │   │   ├── ingestion.py       # PDF chunking & metadata extraction
│   │   │   └── llama_parser.py    # LlamaParse integration for tables
│   │   └── schemas/
│   │       ├── chat.py            # Request/response Pydantic models
│   │       └── upload.py          # Upload schemas
│   └── requirements.txt
├── frontend/
│   ├── App.tsx                    # Main app component, state management
│   ├── components/
│   │   ├── ChatArea.tsx           # Chat interface with streaming
│   │   ├── Sidebar.tsx            # Chat history & navigation
│   │   ├── ContextPanel.tsx       # Trust layer / source viewer
│   │   └── TableDisplay.tsx       # Markdown table rendering
│   ├── services/
│   │   ├── backendService.ts      # API client (REST + SSE streaming)
│   │   └── geminiService.ts       # Google Gemini integration
│   ├── types.ts                   # TypeScript interfaces
│   ├── constants.ts               # Model definitions
│   ├── vite.config.ts             # Vite build configuration
│   └── package.json
├── data/
│   ├── raw_pdfs/                  # Source PDF manuals
│   └── chroma_db/                 # Vector database (gitignored)
├── execution/
│   ├── ingest_knowledge.py        # Standalone ingestion script
│   └── test_api.py                # API connectivity test
├── directives/                    # SOP documents (DOE framework)
├── PRD.md                         # Product Requirements Document
├── SYSTEM_SOP.md                  # System architecture & DOE framework
└── .gitignore
```

---

## Prerequisites

- **Python** 3.9+
- **Node.js** 16+
- **npm** 8+
- **API Keys:**
  - [OpenRouter](https://openrouter.ai/) -- LLM access (Claude, GPT-4o, Gemini)
  - [OpenAI](https://platform.openai.com/) -- Embeddings (`text-embedding-3-small`)
  - [LlamaCloud](https://cloud.llamaindex.ai/) -- Advanced PDF parsing (optional)

---

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd maintenance_ai_copilot
```

### 2. Backend setup

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Frontend setup

```bash
cd frontend
npm install
```

---

## Configuration

Create a `.env` file in the `backend/` directory:

```env
# LLM Provider (required)
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Embeddings (required)
OPENAI_API_KEY=sk-proj-your-key-here

# Advanced PDF Parsing (optional - falls back to PyPDF if not set)
LLAMA_CLOUD_API_KEY=llx-your-key-here

# Default LLM model
DEFAULT_MODEL=anthropic/claude-sonnet-4

# Feature flags
USE_LLAMA_PARSE=true
USE_AGENTIC_RAG=true
MAX_AGENT_ITERATIONS=5

# Paths
CHROMA_PERSIST_DIRECTORY=../data/chroma_db
RAW_PDFS_DIRECTORY=../data/raw_pdfs

# Server
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true
FRONTEND_URL=http://localhost:3000
```

---

## Running the Application

### Start the backend

```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
Starting Maintenance RAG API...
Vector Store: 950 documents indexed
Uvicorn running on http://0.0.0.0:8000
```

### Start the frontend

```bash
cd frontend
npm run dev
```

The app will be available at **http://localhost:3000**.

### Verify the system

```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "components": {
    "api": "ok",
    "vector_store": { "status": "ok", "documents_indexed": 950 },
    "llm_provider": "openrouter"
  },
  "available_models": ["anthropic/claude-sonnet-4", "openai/gpt-4o", ...]
}
```

---

## Knowledge Base Ingestion

Place PDF manuals in `data/raw_pdfs/`, then run:

```bash
cd execution
python ingest_knowledge.py
```

**What happens:**
1. PDFs are loaded with LlamaParse (vision-based, preserves tables) or PyPDF (fallback)
2. Documents are split into chunks (1000 chars, 200 char overlap)
3. Each chunk receives metadata: source, page, chapter, section, chunk index
4. Chunks are embedded with OpenAI `text-embedding-3-small`
5. Vectors are stored in ChromaDB at `data/chroma_db/`

The script is idempotent -- running it again will not duplicate documents.

You can also trigger ingestion via the API:

```bash
curl -X POST http://localhost:8000/api/documents/ingest
```

---

## API Reference

### Health & Status

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | System health with component status |
| `GET` | `/api/models` | Available LLM models with default |

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Synchronous chat (used for image queries) |
| `POST` | `/api/chat/stream` | Streaming chat with SSE (primary endpoint) |
| `GET` | `/api/chat/models` | Available models |

**Chat Request:**
```json
{
  "query": "What maintenance is needed at 300 operating hours?",
  "model": "anthropic/claude-sonnet-4",
  "history": [
    { "role": "user", "content": "previous question" },
    { "role": "assistant", "content": "previous answer" }
  ],
  "image": "base64-encoded-image (optional)"
}
```

**Streaming Events (SSE):**
```
event: status
data: {"step": "analyzing", "message": "Analyzing your question..."}

event: status
data: {"step": "searching", "message": "Search 1: 300 hours maintenance schedule", "index": 1}

event: status
data: {"step": "searching", "message": "Search 2: lubrication specifications", "index": 2}

event: token
data: Based on the maintenance manual...

event: sources
data: [{"content": "...", "source": "manual.pdf", "page": 45, ...}]

event: metadata
data: {"mode": "agentic_streaming", "iterations": 3, "queries_executed": [...]}

event: done
data: [DONE]
```

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/documents` | List indexed documents with chunk count |
| `POST` | `/api/documents/ingest` | Trigger PDF ingestion pipeline |
| `DELETE` | `/api/documents/clear` | Clear entire knowledge base |
| `GET` | `/api/documents/stats` | Vector store statistics |
| `GET` | `/api/pdfs/{filename}` | Serve original PDF files |

---

## RAG System Architecture

The system supports two retrieval modes, selectable via the `USE_AGENTIC_RAG` config flag:

### Agentic RAG (Default)

Uses a **LangGraph state machine** to perform multi-hop retrieval:

```
User Question
     |
     v
[Agent Node] -- decides what to search
     |
     v
[Search Tool] -- queries ChromaDB (top-k similarity)
     |
     v
[State Update] -- accumulates documents, tracks queries
     |
     v
[Agent Node] -- analyzes results, detects references
     |            ("See Table 5-10", "Refer to Page 131")
     |
     +-- if references found --> [Search Tool] (next hop)
     |
     +-- if complete or max iterations --> [Generate Answer]
```

**Key behaviors:**
- The agent prompt instructs it to **never tell the user** "see page X for details" -- instead, it searches for that page and includes the information
- Loop detection: if the same query has been executed before, the agent skips it
- Maximum 5 iterations by default (`MAX_AGENT_ITERATIONS`)
- All retrieved documents are accumulated across hops for comprehensive context

### Legacy RAG (Fallback)

Single-pass retrieval with **query expansion**:
1. The LLM generates 2-3 semantic variants of the user's question
2. Each variant is used to search ChromaDB independently
3. Results are deduplicated and merged
4. Top documents are sent to the LLM for answer generation

---

## Frontend Components

### ChatArea
The main conversation interface supporting:
- Real-time token streaming with processing status indicators
- Markdown rendering (bold, italic, lists, code blocks, tables)
- Image upload for visual fault diagnosis
- Model selection dropdown
- Auto-scrolling and auto-resizing input area

### ContextPanel (Trust Layer)
A right-side panel that displays source documents for verification:
- Document filename with file icon
- Page number and chapter/section location
- Expandable full-content preview (1000-1500 chars)
- Direct link to open the original PDF
- Chunk position indicator (e.g., "Segment 3 of 12")

### Sidebar
Navigation panel with:
- Chat session history
- New chat creation
- Collapsible on mobile (overlay mode)

### Theme
- Dark mode optimized for industrial environments
- Light mode toggle available
- Industrial design language with accent colors

---

## Development

### Backend development

```bash
cd backend
python -m uvicorn app.main:app --reload
```

The `--reload` flag enables hot-reloading on code changes.

### Frontend development

```bash
cd frontend
npm run dev
```

Vite provides HMR (Hot Module Replacement) for instant updates.

### Production build

```bash
cd frontend
npm run build    # outputs to dist/
npm run preview  # preview the production build
```

### Environment variables reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENROUTER_API_KEY` | Yes | -- | OpenRouter API key for LLM access |
| `OPENAI_API_KEY` | Yes | -- | OpenAI API key for embeddings |
| `LLAMA_CLOUD_API_KEY` | No | -- | LlamaCloud key for advanced PDF parsing |
| `DEFAULT_MODEL` | No | `anthropic/claude-sonnet-4.5` | Default LLM model |
| `USE_AGENTIC_RAG` | No | `true` | Enable multi-hop agentic retrieval |
| `USE_LLAMA_PARSE` | No | `true` | Enable vision-based PDF parsing |
| `MAX_AGENT_ITERATIONS` | No | `5` | Max retrieval hops per query |
| `CHROMA_PERSIST_DIRECTORY` | No | `../data/chroma_db` | Vector DB path |
| `RAW_PDFS_DIRECTORY` | No | `../data/raw_pdfs` | Source PDFs path |
| `API_HOST` | No | `0.0.0.0` | Backend host |
| `API_PORT` | No | `8000` | Backend port |
| `FRONTEND_URL` | No | `http://localhost:3000` | Frontend URL for CORS |
| `DEBUG` | No | `true` | Enable debug mode |

---

## License

This project is a Proof of Concept developed for internal evaluation purposes.
