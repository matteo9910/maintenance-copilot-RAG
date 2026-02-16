# Product Requirements Document (PRD)
**Project Name:** Maintenance AI Copilot (PoC)
**Version:** 4.0
**Status:** Full-Stack Implementation with Agentic RAG, Streaming & Visual Figures
**Date:** 2026-01-30
**Owner:** Senior AI Engineer (Big4 Team)

---

## 1. Executive Summary
The "Maintenance AI Copilot" is a web-based PoC application designed to help industrial maintenance technicians quickly resolve equipment faults.
The system uses a hybrid **RAG (Retrieval-Augmented Generation)** architecture: the frontend and vector database run locally (localhost) to ensure speed and control, while generative intelligence is provided through the **OpenRouter API**, allowing users to dynamically select the most suitable LLM model (Claude Sonnet 4.5, ChatGPT-4o, Gemini 3 Pro).
The project strictly follows the **DOE (Directive-Orchestration-Execution)** development framework to ensure reliability and maintainability.

### Version History

#### v4.0 - Inline Technical Figures & PDF Image Extraction (2026-02-16)
- **PDF Figure Extraction**: New `image_extractor.py` module uses PyMuPDF to extract complete figure regions from PDF pages using a caption-anchored, three-phase pipeline (image clustering, caption detection, content expansion).
- **Inline Technical Figures**: AI responses display relevant technical figures (diagrams, schematics, dimension drawings) inline with source attribution and page reference.
- **Vector Graphics Capture**: Region-based rendering (`get_pixmap(clip=rect)`) captures all content including vector drawings, annotations, labels, and dimension lines -- not just embedded bitmap images.
- **Image Deduplication**: Multi-level deduplication prevents duplicate figures in responses (page-level dedup, URL-path dedup, max 4 figures per response).
- **Image Serving API**: New `GET /api/images/{pdf_stem}/{filename}` endpoint serves extracted figure images with proper MIME types.
- **Manifest System**: JSON manifests track page-to-image mappings for each PDF, enabling fast lookup during RAG response enrichment.

#### v3.0 - Full-Stack Polish & Markdown Rendering (2026-01-30)
- **Markdown Rendering**: AI responses now render full Markdown including formatted tables, headers, lists, bold, and code blocks via `react-markdown` + `remark-gfm`.
- **Dark/Light Mode**: Complete theme toggle with industrial-themed styling.
- **Real-time Streaming**: SSE-based token streaming with live processing status updates.

#### v2.0 - Advanced RAG Architecture (2026-01-27)
The system evolved from a **Naive RAG** to an **Agentic RAG** with the following improvements:
1. **LlamaParse Integration**: Advanced PDF parsing with vision models for accurate extraction of complex tables.
2. **LangGraph Agentic RAG**: Multi-hop retrieval system that automatically follows cross-references in documents.

---

## 2. Problem Statement & Goals
**The Problem:**
Technicians spend up to 40% of intervention time searching for information in large, disorganized, often paper-based PDF manuals. Tribal knowledge ("how did Mario fix it last year?") is lost.

**PoC Objectives:**
1. **Reduce MTTR:** Provide step-by-step solutions in < 15 seconds.
2. **Trust & Verification:** Every response must explicitly cite its source (PDF and Page).
3. **Model Benchmark:** Allow the client to compare LLM performance in real-time (Cost vs Quality).
4. **Multimodality:** Support visual input (fault photos) for diagnosis.

---

## 3. User Personas
* **Marco (Maintenance Technician):** Primary user. Works on the shop floor, uses rugged tablet/laptop. Needs direct answers, not theory. Uploads photos of error codes.
* **Giulia (Plant Manager):** Secondary user/Stakeholder. Evaluates system reliability. Wants to see that the AI doesn't "hallucinate" but relies on official manuals.

---

## 4. Technical Architecture (DOE Framework)

The system follows the 3-layer architecture defined in `SYSTEM_SOP.md`:

### 4.1. Directive Layer (Business Logic)
* Defined in Markdown files in the `/directives` folder.
* Governs chunking strategies, data retention policies, and system prompt templates.

### 4.2. Orchestration Layer (Backend - FastAPI)
* **Role:** Manages API flow, user sessions, and routing to OpenRouter.
* **Components:**
    * `POST /api/chat`: Main endpoint. Receives text/images and `model_id`.
    * `POST /api/chat/stream`: SSE streaming endpoint for real-time token delivery.
    * `POST /api/documents/ingest`: Triggers the indexing pipeline.
    * `GET /api/documents`: Lists indexed documents.
    * `GET /api/health`: System health check with vector store stats.
    * **Agentic Router:** Selects retrieval mode (agentic multi-hop vs. legacy single-pass) based on configuration.

### 4.3. Execution Layer (Tools & Scripts)
* **Role:** Deterministic operations on files and databases.
* **Stack:** Python Scripts.
* **Vector Store:** **ChromaDB** (Persisted to local disk at `./data/chroma_db`).
* **Ingestion Engine:** Optimized scripts for PDF parsing (including tables) and embedding generation.

### 4.4. RAG Module Architecture (v2.0+)

The RAG module (`backend/app/rag/`) consists of the following components:

| Module | Description |
|--------|-------------|
| `llama_parser.py` | PDF parsing with LlamaParse (vision models) |
| `ingestion.py` | Ingestion pipeline with PyPDFLoader fallback |
| `image_extractor.py` | PDF figure extraction (region-based rendering with PyMuPDF) |
| `embeddings.py` | OpenAI Embeddings configuration |
| `vector_store.py` | ChromaDB management (singleton pattern) |
| `agent.py` | LangGraph agent for multi-hop retrieval |
| `chain.py` | RAG orchestrator (agentic/legacy routing, query expansion, streaming) |
| `llm.py` | LLM configuration via OpenRouter |

---

## 5. Functional Requirements (FR)

### FR-01: Knowledge Ingestion & Management
* **Description:** The system must process a local folder of PDFs (`./data/raw_pdfs`).
* **Requirement:** Documents must be chunked (1000 chars, 200 overlap) and tagged with metadata extracted from the filename (e.g., `Manuale_Pressa_T800.pdf` -> `machine: pressa_t800`).
* **Output:** Persistent ChromaDB database.
* **API:** `POST /api/documents/ingest` with optional `clear_existing` flag.

### FR-02: Advanced Model Selection
* **Description:** The user must be able to choose which LLM to use for each query.
* **UI:** Dropdown in the chat header populated with available models.
* **Available Models (via OpenRouter):**
    * `anthropic/claude-sonnet-4.5` — Claude Sonnet 4.5 (Anthropic)
    * `openai/chatgpt-4o-latest` — ChatGPT-4o Latest (OpenAI)
    * `google/gemini-3-pro-preview` — Gemini 3 Pro Preview (Google)
* **Default Model:** `anthropic/claude-sonnet-4.5`
* **Backend:** The system passes the correct `model_id` to the OpenRouter call.

### FR-03: Multimodal Input (Vision RAG)
* **Description:** The user can upload an image (.jpg, .png) in the chat.
* **Flow:** The image is converted to base64 and sent to the LLM along with the system prompt. The system can analyze the image (e.g., read an error code or identify a broken component).
* **UI:** Paperclip icon button with image preview before sending.

### FR-04: Evidence & Citations (Trust Layer)
* **Description:** Generated responses must include precise references.
* **UI:** Citation buttons appear below each AI response showing source document names. A collapsible "Trust Layer" panel on the right shows:
    * Source document name, page number, chapter, and section.
    * Extended content excerpt (up to 1500 characters) from the original document.
    * PDF download link for the source file.
    * "Source Verified" confidence indicator.
* **Behavior:** Clicking a citation opens the Trust Layer panel with full context.

### FR-05: Context-Aware Chat
* **Description:** The system must maintain memory of the current conversation (multi-turn conversation).
* **Limits:** Memory is limited to the active session (reset on refresh for the PoC).
* **Sessions:** The sidebar shows chat history with session titles and creation dates.

### FR-06: Advanced PDF Parsing (LlamaParse) - v2.0
* **Description:** The system uses LlamaParse for PDF parsing, leveraging vision models to understand the structural layout of documents.
* **Problem Solved:** Traditional loaders (PyPDFLoader) "flatten" tables, causing incorrect associations between merged cells and rows. LlamaParse preserves table structure by converting them to structured Markdown.
* **Configuration:**
    * `USE_LLAMA_PARSE`: Flag to enable/disable (default: True)
    * `LLAMA_PARSE_RESULT_TYPE`: Output format ("markdown" for structured tables)
* **Fallback:** If LlamaParse fails or is unavailable, the system automatically falls back to PyPDFLoader.

### FR-07: Agentic RAG with Multi-hop Retrieval (LangGraph) - v2.0
* **Description:** The system uses a LangGraph agent that can perform multiple searches to answer complex questions requiring cross-referencing between document sections.
* **Problem Solved:** Linear RAG (naive) performs a single similarity search. If the document says "See Page 131" but page 131 doesn't contain the keywords from the original query, the information is not retrieved. The agent recognizes these references and performs additional searches.
* **Agentic Flow:**
    1. The agent receives the user's question
    2. Uses the `search_maintenance_docs` tool to search the knowledge base
    3. Analyzes results and identifies references to other pages/tables/notes
    4. Performs additional searches to retrieve referenced content
    5. Integrates all information and generates the final response
* **Configuration:**
    * `USE_AGENTIC_RAG`: Flag to enable/disable (default: True)
    * `MAX_AGENT_ITERATIONS`: Maximum hop limit (default: 5)
* **Loop Detection:** The system detects and prevents infinite loops by tracking already-executed queries.
* **Metadata Response:** The response includes metadata about the RAG process:
    * `mode`: "agentic" or "legacy"
    * `iterations`: Number of retrieval iterations
    * `queries_executed`: List of executed queries

### FR-08: Query Expansion - v2.0
* **Description:** Before searching the vector store, the system expands the user's query by generating 2-3 alternative search queries using the LLM.
* **Purpose:** Improves retrieval recall by searching for synonyms, related concepts, and different phrasings.
* **Limit:** Up to 3 expansion queries plus the original query.
* **Deduplication:** Results are deduplicated across all queries to avoid redundant context.

### FR-09: Real-time Streaming with Status Updates - v3.0
* **Description:** AI responses are streamed token-by-token via Server-Sent Events (SSE) for minimal perceived latency.
* **Endpoint:** `POST /api/chat/stream`
* **SSE Event Types:**
    * `status` — Processing stage updates (analyzing, expanding queries, searching, generating)
    * `token` — Individual generated tokens
    * `sources` — Source documents at end of generation
    * `metadata` — RAG metadata (mode, iterations, queries)
    * `done` — Stream completion signal
* **UI Feedback:** Real-time status messages with animated icons show the current processing stage (e.g., "Searching knowledge base... (2/3)").

### FR-10: Markdown Rendering with Formatted Tables - v3.0
* **Description:** AI responses are rendered as rich HTML using `react-markdown` with `remark-gfm` plugin.
* **Supported Elements:** Tables (with borders, header styling, hover effects), headings, bold/italic, ordered/unordered lists, inline/block code.
* **Table Styling:** Visible borders, colored header background, cell padding, horizontal scroll for wide tables.
* **Dark Mode Support:** All Markdown elements adapt to the current theme.

### FR-11: Dark/Light Mode Toggle - v3.0
* **Description:** Users can toggle between dark and light themes.
* **Dark Theme:** Industrial dark mode with deep backgrounds (#0B0C10, #1F2833) and Safety Orange accent (#FF6600).
* **Light Theme:** Clean white/gray backgrounds with the same accent color.
* **Persistence:** Theme preference maintained during the session.

### FR-12: PDF Figure Extraction & Inline Display - v4.0
* **Description:** The system extracts complete figure regions from PDF manuals and displays them inline in AI responses when relevant.
* **Extraction Pipeline (three-phase):**
    1. **Image Clustering:** PyMuPDF detects embedded image bounding boxes, filters decorative elements (< 50pt), and groups nearby images into figure clusters using rectangle merging (50pt threshold).
    2. **Caption Detection:** For each cluster, searches for figure caption text (`Fig.X-Y`, `Figure N`) within 500pt below the image region.
    3. **Content Expansion:** Expands the region horizontally to include all text annotations, labels, and notes within the figure's vertical range, then merges overlapping expanded regions.
* **Rendering:** The complete figure region is rendered at 200 DPI using `page.get_pixmap(clip=rect)`, capturing vector graphics, dimension lines, and annotations exactly as they appear in the PDF.
* **Manifest System:** A JSON manifest maps page numbers to extracted image filenames for each PDF, enabling fast lookup during response enrichment.
* **Frontend Display:**
    * Figures appear inline below AI responses with source attribution (`PDF name - Page N | Figure N`).
    * "Full size" button opens the figure in a new browser tab at full resolution.
    * Multi-level deduplication prevents duplicate figures: (source, page) pair dedup, URL-path dedup, and max 4 figures per response.
* **API Endpoint:** `GET /api/images/{pdf_stem}/{filename}` serves extracted images with correct MIME types.
* **Configuration:**
    * `RENDER_DPI`: 200 (rendering quality)
    * `MERGE_DISTANCE_PT`: 50 (image grouping threshold)
    * `CAPTION_SEARCH_DISTANCE_PT`: 500 (max distance to caption below image)
    * `FIGURE_PADDING_PT`: 10 (padding around rendered regions)

---

## 6. Frontend & UX Requirements

**Stack:** React 19 + TypeScript + Vite 6 (Dev Server & Build Tool), Tailwind CSS (CDN), Lucide React (Icons), react-markdown + remark-gfm (Markdown rendering).

### UI Structure
1. **Sidebar (Left - Collapsible):**
    * Brand: "MC Maintenance Copilot".
    * "New Chat" button to create sessions.
    * Search bar for filtering chat history.
    * Chat history list with titles and dates.
    * User footer section.
2. **Top Navigation Bar:**
    * Model Selector dropdown (left).
    * Dark/Light mode toggle button (right).
3. **Main Chat (Center):**
    * Welcome screen with empty state.
    * Token-streamed messages with differentiated User/AI styling.
    * Full Markdown rendering (tables, headers, lists, bold, code blocks).
    * Inline technical figures with source/page attribution and "Full size" viewer.
    * Citation buttons below AI responses.
    * "View Trust Layer" link for source verification.
    * Real-time processing status with animated icons.
4. **Input Zone (Bottom):**
    * Auto-resizing textarea.
    * Image upload button (paperclip icon) with preview.
    * Send button with loading state.
5. **Trust Layer Panel (Right - Collapsible):**
    * Source document details (name, page, chapter, section).
    * Extended content excerpt (up to 1500 characters).
    * PDF download link.
    * "Source Verified" confidence badge.

**Visual Style:**
* **Theme:** Industrial with Dark/Light mode support.
* **Dark Mode:** Deep backgrounds (#0B0C10, #1F2833), muted text (#C5C6C7).
* **Accent:** Safety Orange (#FF6600) for interactive elements and highlights.
* **Typography:** `Inter` for UI, `JetBrains Mono` for code and technical data.
* **Icons:** Lucide React icon library.
* **Scrollbars:** Custom styled (6px, rounded, accent on hover).

---

## 7. API Interface (v3.0)

The Frontend communicates with the Backend FastAPI through the following routes:

| Method | Endpoint | Payload | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | - | Root status check |
| `GET` | `/api/health` | - | Detailed system health with vector store stats |
| `GET` | `/api/models` | - | List available LLM models with default |
| `POST` | `/api/chat` | `{ query, model?, history[], image? }` | Send message and retrieve response |
| `POST` | `/api/chat/stream` | `{ query, model?, history[], image? }` | SSE streaming response with real-time tokens |
| `GET` | `/api/chat/models` | - | List models (chat router) |
| `GET` | `/api/documents` | - | List indexed documents with metadata |
| `POST` | `/api/documents/ingest` | `{ clear_existing? }` | Trigger PDF re-indexing pipeline |
| `GET` | `/api/documents/stats` | - | Collection statistics (count, status) |
| `DELETE` | `/api/documents/clear` | - | Clear entire knowledge base |
| `GET` | `/api/pdfs/{filename}` | - | Serve PDF file for download |
| `GET` | `/api/images/{pdf_stem}/{filename}` | - | Serve extracted figure images |

### Chat Request Schema
```json
{
  "query": "string (required, min_length=1)",
  "model": "string | null (e.g., 'anthropic/claude-sonnet-4.5')",
  "history": [
    { "role": "user | model", "content": "string" }
  ],
  "image": "string | null (base64 encoded)"
}
```

### Chat Response Schema
```json
{
  "answer": "string",
  "sources": [
    {
      "content": "string (up to 1500 chars)",
      "source": "filename.pdf",
      "page": 123,
      "chapter": "string | null",
      "section": "string | null",
      "images": ["/api/images/filename/page_123_fig_1.png"]
    }
  ],
  "conversation_id": "uuid",
  "model_used": "anthropic/claude-sonnet-4.5",
  "rag_metadata": {
    "mode": "agentic | legacy",
    "iterations": 2,
    "queries_executed": ["query1", "query2"]
  }
}
```

### SSE Stream Events
```
event: status\ndata: {"step": "searching", "message": "Searching knowledge base...", "index": 1, "total": 3}
event: token\ndata: {"token": "The"}
event: sources\ndata: [{"content": "...", "source": "file.pdf", "page": 42}]
event: metadata\ndata: {"mode": "agentic", "iterations": 2, "queries_executed": [...]}
event: done\ndata: {}
```

---

## 8. Non-Functional Requirements (NFR)

* **NFR-01 (Performance):** Vector retrieval time < 500ms. Total response time (Time to First Token) < 3s (dependent on external API, but the backend must not add latency). SSE streaming ensures perceived latency is minimal.
* **NFR-02 (Data Privacy):** PDF documents and Embeddings remain strictly local. Only the relevant chunks for the question and the user query are sent to OpenRouter.
* **NFR-03 (Reliability):** API error handling. If OpenRouter fails, display a user-friendly error message (not a Python stack trace). Fallback from LlamaParse to PyPDFLoader if parsing fails.
* **NFR-04 (Corporate Network):** HTTP clients configured with `verify=False` for corporate SSL certificate environments.

---

## 9. Implementation Roadmap

**Phase 1: Setup & Backend Core (Days 1-3)** — COMPLETED
* Project repository initialization (React + FastAPI).
* DOE environment setup (`directives/`, `execution/`).
* Ingestion script development (`execution/ingest.py`) and ChromaDB setup.
* OpenRouter API testing via Python script.

**Phase 2: API Development (Days 4-5)** — COMPLETED
* FastAPI endpoint development.
* LangChain logic implementation (Retrieval Chain).
* Testing with Postman.

**Phase 3: Frontend Construction (Days 6-8)** — COMPLETED
* UI component development (Chat Bubble, Layout, Sidebar).
* API client integration with backend service.
* State management (Messages, Loading, Sessions).

**Phase 4: Refinement (Days 9-10)** — COMPLETED
* System prompt engineering (AI personality tuning).
* UI polish (Dark/Light mode, icons, loading animations).
* Demo preparation.

**Phase 5: Advanced RAG Architecture (Days 11-12)** — COMPLETED
* LlamaParse integration for PDF parsing with vision models.
* LangGraph implementation for Agentic RAG with multi-hop retrieval.
* Loop detection and iteration limit management.
* API response update with RAG metadata.
* End-to-end testing of the agentic system.

**Phase 6: Streaming & UI Polish (Days 13-14)** — COMPLETED
* SSE streaming endpoint implementation (`POST /api/chat/stream`).
* Real-time processing status messages during RAG pipeline.
* Token-by-token response streaming in frontend.
* Trust Layer panel with extended source content.
* Markdown rendering with `react-markdown` + `remark-gfm` for formatted tables.
* Dark/Light mode toggle with industrial theme.
* Chat session management with sidebar history.

**Phase 7: PDF Figure Extraction & Inline Display (Days 15-16)** — COMPLETED
* PyMuPDF-based figure extraction with caption-anchored region detection.
* Three-phase pipeline: image clustering, caption search (500pt range), content expansion with post-merge.
* High-DPI rendering (200 DPI) capturing vector graphics, annotations, and dimension drawings.
* JSON manifest system for page-to-image mapping.
* Image serving API endpoint (`GET /api/images/{pdf_stem}/{filename}`).
* Inline technical figures in chat responses with source attribution.
* Multi-level frontend deduplication (page-level, URL-path, max 4 limit).
* Full-size image viewing in new browser tab.

---

## 10. Configuration Reference (v3.0)

### Environment Variables — Backend (.env)
```bash
# OpenRouter API
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# OpenAI API (Embeddings)
OPENAI_API_KEY=sk-proj-...

# LlamaCloud API (LlamaParse)
LLAMA_CLOUD_API_KEY=llx-...

# Default Model
DEFAULT_MODEL=anthropic/claude-sonnet-4.5

# ChromaDB
CHROMA_PERSIST_DIRECTORY=../data/chroma_db
CHROMA_COLLECTION_NAME=maintenance_docs

# Embedding Model
EMBEDDING_MODEL=text-embedding-3-small

# Feature Flags
USE_LLAMA_PARSE=true
USE_AGENTIC_RAG=true
MAX_AGENT_ITERATIONS=5

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true
FRONTEND_URL=http://localhost:3000
```

### Environment Variables — Frontend (.env.local)
```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

### Backend Dependencies
```
# FastAPI & Server
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
python-multipart>=0.0.6

# AI & RAG
langchain>=0.3.0
langchain-community>=0.3.0
langchain-openai>=0.2.0
langchain-chroma>=0.2.0
chromadb>=0.4.22
openai>=1.10.0

# PDF Processing
pypdf>=3.17.0
pdfplumber>=0.10.3
llama-parse>=0.4.0
llama-index>=0.10.0
PyMuPDF>=1.24.0

# Agentic RAG (LangGraph)
langgraph>=0.2.0
langchain-core>=0.3.0

# Utilities
python-dotenv>=1.0.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
httpx>=0.26.0
tenacity>=8.2.0
```

### Frontend Dependencies
```
react ^19.2.3
react-dom ^19.2.3
react-markdown ^10.1.0
remark-gfm ^4.0.1
lucide-react ^0.562.0
@google/genai ^1.38.0
```

---

## 11. Project Structure

```
maintenance_ai_copilot/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entry point & PDF serving
│   │   ├── api/
│   │   │   ├── chat.py             # Chat endpoints (standard + SSE streaming)
│   │   │   └── documents.py        # Document management (ingest, list, stats, clear)
│   │   ├── core/
│   │   │   └── config.py           # Settings & feature flags
│   │   ├── rag/
│   │   │   ├── agent.py            # LangGraph agentic RAG (multi-hop retrieval)
│   │   │   ├── chain.py            # RAG orchestrator (query expansion, streaming)
│   │   │   ├── embeddings.py       # OpenAI embeddings configuration
│   │   │   ├── image_extractor.py  # PDF figure extraction (PyMuPDF region rendering)
│   │   │   ├── ingestion.py        # PDF ingestion pipeline
│   │   │   ├── llama_parser.py     # LlamaParse configuration
│   │   │   ├── llm.py              # OpenRouter LLM configuration
│   │   │   └── vector_store.py     # ChromaDB management (singleton)
│   │   └── schemas/
│   │       ├── chat.py             # Pydantic request/response schemas
│   │       └── upload.py           # Upload schemas
│   ├── .env                        # API keys & configuration
│   ├── requirements.txt            # Python dependencies
│   └── venv/                       # Python 3.11 virtual environment
├── frontend/
│   ├── components/
│   │   ├── ChatArea.tsx            # Main chat with Markdown rendering
│   │   ├── ContextPanel.tsx        # Trust Layer panel
│   │   ├── Sidebar.tsx             # Chat history & navigation
│   │   └── TableDisplay.tsx        # Table renderer component
│   ├── services/
│   │   ├── backendService.ts       # FastAPI client (REST + SSE streaming)
│   │   └── geminiService.ts        # Gemini API integration
│   ├── App.tsx                     # Root component & state management
│   ├── index.tsx                   # React mount point
│   ├── types.ts                    # TypeScript interfaces
│   ├── constants.ts                # Model definitions & constants
│   ├── index.html                  # Tailwind CSS config & global styles
│   ├── vite.config.ts              # Vite dev server & build config
│   ├── tsconfig.json               # TypeScript configuration
│   ├── package.json                # Node.js dependencies
│   └── .env.local                  # Frontend environment variables
├── data/
│   ├── raw_pdfs/                   # Source PDF manuals
│   ├── images/                     # Extracted figure regions (gitignored, generated)
│   └── chroma_db/                  # ChromaDB persistent storage (gitignored)
├── execution/
│   ├── ingest_knowledge.py         # Knowledge base ingestion script
│   └── test_api.py                 # API connection testing script
├── directives/                     # SOP Markdown files (Directive layer)
├── SYSTEM_SOP.md                   # System operating procedures
├── PRD.md                          # This document
└── README.md                       # Project documentation
```
