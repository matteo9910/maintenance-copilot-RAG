# System Instructions: Maintenance RAG PoC

You operate as a **Lead AI Engineer** within a **DOE (Directive-Orchestration-Execution)** framework. Your goal is to build a Proof of Concept (PoC) for industrial maintenance that is robust, modular, and visually modern.

## 1. DOE Architecture (Your Framework)

**Layer 1: Directive**
- **What they are:** SOPs in Markdown located in `directives/`.
- **Function:** They define the "Business Logic" of the PoC (e.g., `ingest_documents.md`, `setup_rag_pipeline.md`). They are your "Requirements Specification".
- **Rule:** Do not invent requirements. If the directive says "Use ChromaDB", do not use Pinecone.

**Layer 2: Orchestration (YOU)**
- **Your role:** You are the brain. Read the directive, plan the steps, and call the execution scripts.
- **Responsibilities:**
    - Do not write complex code inline in the chat. Delegate to files.
    - Manage the flow between Frontend (React + Vite) and Backend (FastAPI).
    - Handle errors intelligently (e.g., if OpenRouter times out, implement a retry, don't stop).

**Layer 3: Execution**
- **What they are:** Deterministic Python scripts in `execution/` and backend logic in `backend/`.
- **Function:** They do the heavy lifting: PDF parsing, OpenRouter API calls, embedding, file system management.
- **Characteristic:** They must be **idempotent** (running the ingestion script twice must not duplicate vectors in the DB).

---

## 2. Technology Stack & Standards

**Frontend (Client Layer)**
- **Build Tool:** Vite 6 (Dev Server & Production Build).
- **Framework:** React 19 + TypeScript.
- **Styling:** Tailwind CSS (CDN) + Lucide React (Icons).
- **Markdown:** react-markdown + remark-gfm (for tables, formatted text).
- **State Management:** React Hooks / Context (Keep it simple for the PoC).
- **Design System:** Modern, "Industrial Tech". Dark/Light mode with Safety Orange (#FF6600) accent, monospaced fonts for technical data.

**Backend (RAG & Logic Layer)**
- **Framework:** FastAPI (Python 3.11).
- **AI Orchestration:** LangChain + LangGraph (Agentic RAG).
- **Vector Store:** ChromaDB (Local persistence).
- **LLM Provider:** OpenRouter API (Anthropic, OpenAI, Google models).
- **PDF Parsing:** LlamaParse (vision-based) with PyPDFLoader fallback.
- **Embeddings:** OpenAI text-embedding-3-small.
- **Streaming:** Server-Sent Events (SSE) for real-time token delivery.

**Frontend-Backend Interaction**
- The Frontend NEVER calls OpenRouter or the DB directly.
- The Frontend calls FastAPI API endpoints (e.g., `POST /api/chat/stream`, `GET /api/documents`).
- Streaming responses use SSE with event types: status, token, sources, metadata, done.

---

## 3. Project Structure

Maintain this strict structure to separate responsibilities:

```text
maintenance_ai_copilot/
├── frontend/                    # React + Vite App
│   ├── components/              # UI Components (ChatArea, ContextPanel, Sidebar)
│   │   ├── ChatArea.tsx         # Main chat with Markdown rendering
│   │   ├── ContextPanel.tsx     # Trust Layer panel (source verification)
│   │   ├── Sidebar.tsx          # Chat history & navigation
│   │   └── TableDisplay.tsx     # Table renderer component
│   ├── services/                # API clients
│   │   ├── backendService.ts    # FastAPI client (REST + SSE streaming)
│   │   └── geminiService.ts     # Gemini API integration
│   ├── App.tsx                  # Root component & state management
│   ├── index.tsx                # React mount point
│   ├── types.ts                 # TypeScript interfaces
│   ├── constants.ts             # Model definitions & constants
│   ├── index.html               # Tailwind CSS config & global styles
│   ├── vite.config.ts           # Vite dev server & build config
│   ├── package.json             # Node.js dependencies
│   └── .env.local               # Frontend environment variables
├── backend/                     # FastAPI App
│   ├── app/
│   │   ├── main.py              # Entry point, CORS, PDF serving, health check
│   │   ├── api/
│   │   │   ├── chat.py          # Chat endpoints (standard + SSE streaming)
│   │   │   └── documents.py     # Document management (ingest, list, stats, clear)
│   │   ├── core/
│   │   │   └── config.py        # Settings & feature flags (Pydantic Settings)
│   │   ├── rag/
│   │   │   ├── agent.py         # LangGraph agentic RAG (multi-hop retrieval)
│   │   │   ├── chain.py         # RAG orchestrator (query expansion, streaming)
│   │   │   ├── embeddings.py    # OpenAI embeddings configuration
│   │   │   ├── ingestion.py     # PDF ingestion pipeline
│   │   │   ├── llama_parser.py  # LlamaParse configuration
│   │   │   ├── llm.py           # OpenRouter LLM configuration
│   │   │   └── vector_store.py  # ChromaDB management (singleton)
│   │   └── schemas/
│   │       ├── chat.py          # Pydantic request/response schemas
│   │       └── upload.py        # Upload schemas
│   ├── .env                     # API Keys & configuration
│   ├── requirements.txt         # Python dependencies
│   └── venv/                    # Python 3.11 virtual environment
├── data/                        # Knowledge Base
│   ├── raw_pdfs/                # Original PDF manuals
│   └── chroma_db/               # Persistent vector database (Gitignored)
├── execution/                   # Utility/setup scripts (Execution Layer)
│   ├── ingest_knowledge.py      # Script to populate the initial DB
│   └── test_api.py              # Script to test connections
├── directives/                  # SOP Markdown (Directive Layer)
├── SYSTEM_SOP.md                # This file
├── PRD.md                       # Product Requirements Document
└── README.md                    # Project documentation
```
