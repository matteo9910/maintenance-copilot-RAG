# Product Requirements Document (PRD)
**Project Name:** Maintenance AI Copilot (PoC)
**Version:** 2.0
**Status:** Advanced RAG Implementation Complete
**Date:** 2026-01-27
**Owner:** Senior AI Engineer (Big4 Team)

---

## 1. Executive Summary
Il "Maintenance AI Copilot" è un'applicazione web PoC progettata per supportare i tecnici di manutenzione industriale nella risoluzione rapida dei guasti.
Il sistema utilizza un'architettura **RAG (Retrieval-Augmented Generation)** ibrida: il frontend e il database vettoriale risiedono in locale (Local Host) per garantire velocità e controllo, mentre l'intelligenza generativa è fornita tramite **OpenRouter API**, permettendo all'utente di selezionare dinamicamente il modello LLM più adatto (GPT-4o, Claude 3.5, Gemini 1.5).
Il progetto adotta rigorosamente il framework di sviluppo **DOE (Directive-Orchestration-Execution)** per garantire affidabilità e manutenibilità.

### v2.0 - Advanced RAG Architecture (2026-01-27)
Il sistema è stato evoluto da un **Naive RAG** a un **Agentic RAG** con le seguenti migliorie:

1. **LlamaParse Integration**: Parsing PDF avanzato con modelli di visione per estrazione accurata di tabelle complesse
2. **LangGraph Agentic RAG**: Sistema di retrieval multi-hop che segue automaticamente riferimenti incrociati nei documenti

---

## 2. Problem Statement & Goals
**Il Problema:**
I tecnici spendono fino al 40% del tempo di intervento cercando informazioni in manuali PDF voluminosi, disorganizzati e spesso cartacei. La conoscenza tribale ("come ha risolto Mario l'anno scorso?") viene persa.

**Gli Obiettivi del PoC:**
1.  **Riduzione MTTR:** Fornire soluzioni passo-passo in < 15 secondi.
2.  **Trust & Verification:** Ogni risposta deve citare esplicitamente la fonte (PDF e Pagina).
3.  **Model Benchmark:** Permettere al cliente di confrontare in tempo reale le performance di diversi LLM (Cost vs Quality).
4.  **Multimodalità:** Supportare l'input visivo (foto del guasto) per la diagnosi.

---

## 3. User Personas
* **Marco (Maintenance Technician):** Utente primario. Opera in reparto, usa tablet/laptop rugged. Ha bisogno di risposte dirette, non teoria. Carica foto dei codici errore.
* **Giulia (Plant Manager):** Utente secondario/Stakeholder. Valuta l'affidabilità del sistema. Vuole vedere che l'AI non "allucina" ma si basa sui manuali ufficiali.

---

## 4. Technical Architecture (DOE Framework)

Il sistema segue l'architettura a 3 livelli definita nel `SYSTEM_SOP.md`:

### 4.1. Directive Layer (Logica di Business)
* Definita in file Markdown nella cartella `/directives`.
* Regola le strategie di chunking, le policy di retention dei dati e i template dei prompt di sistema.

### 4.2. Orchestration Layer (Backend - FastAPI)
* **Ruolo:** Gestisce il flusso API, la sessione utente e il routing verso OpenRouter.
* **Componenti:**
    * `POST /api/chat`: Endpoint principale. Riceve testo/immagini e `model_id`.
    * `POST /api/ingest`: Triggera la pipeline di indicizzazione.
    * **Router Logico:** Seleziona quali documenti recuperare dal Vector Store in base ai metadati (es. `machine_id`).

### 4.3. Execution Layer (Tools & Scripts)
* **Ruolo:** Operazioni deterministiche sui file e database.
* **Stack:** Python Scripts.
* **Vector Store:** **ChromaDB** (Persistenza su disco locale in `./data/chroma_db`).
* **Ingestion Engine:** Script ottimizzati per parsing PDF (inclusi tabelle) e generazione embeddings.

### 4.4. RAG Module Architecture (v2.0)

Il modulo RAG (`backend/app/rag/`) è composto dai seguenti componenti:

| Modulo | Descrizione |
|--------|-------------|
| `llama_parser.py` | Parsing PDF con LlamaParse (vision models) |
| `ingestion.py` | Pipeline di ingestion con fallback PyPDFLoader |
| `embeddings.py` | Configurazione OpenAI Embeddings |
| `vector_store.py` | Gestione ChromaDB (singleton pattern) |
| `agent.py` | LangGraph agent per multi-hop retrieval |
| `chain.py` | Orchestratore RAG (agentic/legacy routing) |
| `llm.py` | Configurazione LLM via OpenRouter |

---

## 5. Functional Requirements (FR)

### FR-01: Knowledge Ingestion & Management
* **Descrizione:** Il sistema deve processare una cartella locale di PDF (`./data/raw_pdfs`).
* **Requisito:** I documenti devono essere "Chunkati" e taggati con metadati estratti dal nome file (es. `Manuale_Pressa_T800.pdf` -> `machine: pressa_t800`).
* **Output:** Database ChromaDB persistente.

### FR-02: Advanced Model Selection
* **Descrizione:** L'utente deve poter scegliere quale LLM utilizzare per ogni singola query.
* **UI:** Dropdown nel frontend popolato dinamicamente (o staticamente per il PoC) con opzioni:
    * `openai/gpt-4o`
    * `anthropic/claude-3.5-sonnet`
    * `google/gemini-1.5-pro`
* **Backend:** Il sistema passa il `model_id` corretto alla chiamata OpenRouter.

### FR-03: Multimodal Input (Vision RAG)
* **Descrizione:** L'utente può caricare un'immagine (.jpg, .png) nella chat.
* **Flusso:** L'immagine viene convertita in base64 e inviata all'LLM insieme al prompt di sistema. Il sistema deve essere in grado di analizzare l'immagine (es. leggere un codice errore o identificare un componente rotto).

### FR-04: Evidence & Citations
* **Descrizione:** Le risposte generate devono includere riferimenti precisi.
* **UI:** Accanto alla risposta, o in un pannello laterale, devono apparire i link "Fonte: [NomeDoc - Pagina X]".
* **Behavior:** Cliccando sulla fonte, (opzionale per V1) si espande il testo originale recuperato (il "Chunk").

### FR-05: Context-Aware Chat
* **Descrizione:** Il sistema deve mantenere la memoria della conversazione corrente (Multi-turn conversation).
* **Limiti:** La memoria è limitata alla sessione attiva (reset al refresh per il PoC).

### FR-06: Advanced PDF Parsing (LlamaParse) - v2.0
* **Descrizione:** Il sistema utilizza LlamaParse per il parsing dei PDF, sfruttando modelli di visione per comprendere il layout strutturale dei documenti.
* **Problema Risolto:** I loader tradizionali (PyPDFLoader) "appiattiscono" le tabelle, causando associazioni errate tra celle unite e righe. LlamaParse preserva la struttura delle tabelle convertendole in Markdown strutturato.
* **Configurazione:**
    * `USE_LLAMA_PARSE`: Flag per abilitare/disabilitare (default: True)
    * `LLAMA_PARSE_RESULT_TYPE`: Formato output ("markdown" per tabelle strutturate)
* **Fallback:** Se LlamaParse fallisce o non è disponibile, il sistema utilizza automaticamente PyPDFLoader.

### FR-07: Agentic RAG with Multi-hop Retrieval (LangGraph) - v2.0
* **Descrizione:** Il sistema utilizza un agente LangGraph che può eseguire multiple ricerche per rispondere a domande complesse che richiedono cross-referencing tra sezioni del documento.
* **Problema Risolto:** Il RAG lineare (naive) esegue una sola ricerca per similarità. Se il documento dice "Vedi Pagina 131" ma la pagina 131 non contiene le keyword della query originale, le informazioni non vengono recuperate. L'agente riconosce questi riferimenti e esegue ricerche aggiuntive.
* **Flusso Agentico:**
    1. L'agente riceve la domanda dell'utente
    2. Usa il tool `search_maintenance_docs` per cercare nel knowledge base
    3. Analizza i risultati e identifica riferimenti a altre pagine/tabelle/note
    4. Esegue ricerche aggiuntive per recuperare il contenuto referenziato
    5. Integra tutte le informazioni e genera la risposta finale
* **Configurazione:**
    * `USE_AGENTIC_RAG`: Flag per abilitare/disabilitare (default: True)
    * `MAX_AGENT_ITERATIONS`: Limite massimo di hop (default: 5)
* **Loop Detection:** Il sistema rileva e previene loop infiniti tracciando le query già eseguite.
* **Metadata Response:** La risposta include metadati sul processo RAG:
    * `mode`: "agentic" o "legacy"
    * `iterations`: Numero di iterazioni di retrieval
    * `queries_executed`: Lista delle query eseguite

---

## 6. Frontend & UX Requirements

**Stack:** Next.js 14 (App Router), React, Tailwind CSS.

### UI Structure (Split Screen Layout)
1.  **Sidebar (Left):**
    * Configurazione Modello (Dropdown).
    * Status connessione DB.
    * Pulsante "Nuova Chat".
2.  **Main Chat (Center):**
    * Stream dei messaggi.
    * Stile differenziato User/AI.
    * Supporto Markdown (per liste, grassetti, codice).
3.  **Input Zone (Bottom):**
    * Input text area.
    * Pulsante Upload Immagine (icona graffetta/camera).
    * Pulsante Send.
4.  **Evidence Panel (Right - Collapsible):**
    * Mostra i dettagli tecnici dei documenti recuperati per la risposta corrente (Snippet di testo o metadati).
    * Serve a dare "Trust" all'utente esperto.

**Visual Style:**
* **Theme:** Industrial Dark Mode (Sfondi Slate-900, Testo Slate-200).
* **Accents:** Emerald-500 (Success/Online), Blue-500 (Processing), Amber-500 (Warning).
* **Typography:** Font `Inter` per UI, `JetBrains Mono` per codici e dati tecnici.

---

## 7. API Interface (v2.0)

Il Frontend comunicherà con il Backend FastAPI tramite le seguenti rotte:

| Method | Endpoint | Payload | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | - | Verifica stato sistema e DB |
| `POST` | `/api/chat` | `{ query: string, history: [], model: string, image: base64? }` | Invia messaggio e recupera risposta |
| `GET` | `/api/documents` | - | Lista i documenti indicizzati nel DB |
| `POST` | `/api/ingest` | - | Forza il re-indexing della cartella raw_pdfs |

### Chat Response Schema (v2.0)
```json
{
  "answer": "string",
  "sources": [
    {
      "content": "string",
      "source": "filename.pdf",
      "page": 123
    }
  ],
  "conversation_id": "uuid",
  "model_used": "openai/gpt-4o",
  "rag_metadata": {
    "mode": "agentic | legacy",
    "iterations": 2,
    "queries_executed": ["query1", "query2"]
  }
}
```

---

## 8. Non-Functional Requirements (NFR)

* **NFR-01 (Performance):** Tempo di Retrieval (ricerca vettoriale) < 500ms. Tempo totale di risposta (Time to First Token) < 3s (dipendente da API esterna, ma il backend non deve aggiungere latenza).
* **NFR-02 (Data Privacy):** I documenti PDF e gli Embeddings rimangono strettamente in locale. Solo i chunk rilevanti per la domanda e la query utente vengono inviati a OpenRouter.
* **NFR-03 (Reliability):** Gestione degli errori API. Se OpenRouter fallisce, mostrare un messaggio di errore user-friendly (non stack trace Python).

---

## 9. Implementation Roadmap

**Phase 1: Setup & Backend Core (Days 1-3)**
* Init progetto Repository (Next.js + FastAPI).
* Setup Environment DOE (`directives/`, `execution/`).
* Sviluppo Script Ingestion (`execution/ingest.py`) e setup ChromaDB.
* Test API OpenRouter via script Python.

**Phase 2: API Development (Days 4-5)**
* Sviluppo FastAPI Endpoints.
* Implementazione LangChain logic (Retrieval Chain).
* Testing con Postman.

**Phase 3: Frontend Construction (Days 6-8)**
* Sviluppo UI Components (Chat Bubble, Layout).
* Integrazione API Client.
* State Management (Messaggi, Loading).

**Phase 4: Refinement (Days 9-10)**
* System Prompt Engineering (Migliorare la personalità dell'AI).
* UI Polish (Dark mode, icone, animazioni loading).
* Demo Preparation.

**Phase 5: Advanced RAG Architecture (Days 11-12) - COMPLETED**
* Integrazione LlamaParse per parsing PDF con vision models.
* Implementazione LangGraph per Agentic RAG con multi-hop retrieval.
* Loop detection e gestione limiti di iterazione.
* Aggiornamento API response con RAG metadata.
* Testing end-to-end del sistema agentico.

---

## 10. Configuration Reference (v2.0)

### Environment Variables (.env)
```bash
# OpenRouter API
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# OpenAI API (Embeddings)
OPENAI_API_KEY=sk-proj-...

# LlamaCloud API (LlamaParse)
LLAMA_CLOUD_API_KEY=llx-...

# Feature Flags
USE_LLAMA_PARSE=true
USE_AGENTIC_RAG=true
MAX_AGENT_ITERATIONS=5
```

### Dependencies Added (v2.0)
```
llama-parse>=0.4.0
llama-index>=0.10.0
langgraph>=0.2.0
nest-asyncio
```