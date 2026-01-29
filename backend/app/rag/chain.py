"""RAG Chain Implementation.

This module provides two RAG modes:
1. Agentic RAG (default): Uses LangGraph for multi-hop retrieval
2. Legacy RAG: Linear chain with single retrieval (fallback)

The mode is controlled by settings.USE_AGENTIC_RAG.

Features:
- Query Expansion: Automatically reformulates queries for better retrieval
- Multi-hop retrieval (agentic mode): Follows references across documents
- Full content extraction for trust layer
- Streaming responses for reduced latency
"""
from typing import Optional, List, Dict, Any, AsyncGenerator
import json
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings
from app.rag.llm import get_llm
from app.rag.vector_store import get_retriever
from app.rag.agent import query_rag_agent, is_agentic_rag_available


# =============================================================================
# QUERY EXPANSION
# =============================================================================

QUERY_EXPANSION_PROMPT = """You are a query expansion specialist for a technical maintenance documentation system.

Given a user's question, generate 2-3 alternative search queries that would help find relevant information in maintenance manuals.

Consider:
- Technical synonyms (e.g., "replace" → "substitute", "change", "swap")
- Related concepts (e.g., "lubrication" → "oil", "grease", "lubricant intervals")
- Specific technical terms that might be used in manuals
- Inverse queries that might find related procedures

Original question: {question}

Return ONLY the alternative queries, one per line, without numbering or explanations.
Keep each query concise (under 15 words).
Do not repeat the original question."""


async def expand_query(question: str, model_id: Optional[str] = None) -> List[str]:
    """
    Expand a user's question into multiple search queries for better retrieval.

    This uses an LLM to generate semantically similar queries that might
    match different phrasings in the documentation.

    Args:
        question: The original user question.
        model_id: Optional LLM model ID.

    Returns:
        List of expanded queries including the original.
    """
    try:
        llm = get_llm(model_id=model_id)

        prompt = ChatPromptTemplate.from_template(QUERY_EXPANSION_PROMPT)
        chain = prompt | llm | StrOutputParser()

        result = await chain.ainvoke({"question": question})

        # Parse the expanded queries
        expanded = [q.strip() for q in result.strip().split('\n') if q.strip()]

        # Always include original question first, then add expanded queries
        all_queries = [question] + expanded[:3]  # Limit to 3 expansions

        print(f"Query expansion: {question} → {all_queries}")
        return all_queries

    except Exception as e:
        print(f"Query expansion failed: {e}, using original query only")
        return [question]


async def retrieve_with_expansion(
    question: str,
    model_id: Optional[str] = None,
    k: int = 4
) -> List[Document]:
    """
    Retrieve documents using query expansion for better coverage.

    Performs retrieval with the original query and expanded variants,
    then deduplicates and ranks the results.

    Args:
        question: The user's question.
        model_id: LLM model for query expansion.
        k: Number of documents to retrieve per query.

    Returns:
        Deduplicated list of relevant documents.
    """
    retriever = get_retriever(k=k)

    # Get expanded queries
    queries = await expand_query(question, model_id)

    # Retrieve documents for each query
    all_docs = []
    seen_content = set()

    for query in queries:
        docs = retriever.invoke(query)
        for doc in docs:
            # Deduplicate by content hash
            content_hash = hash(doc.page_content[:500])
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                all_docs.append(doc)

    # Limit total documents to avoid context overflow
    return all_docs[:k * 2]  # Allow up to 2x the normal limit for expanded queries


# System prompt for the Maintenance AI Copilot
SYSTEM_PROMPT = """You are an expert industrial maintenance technician assistant. Your task is to help technicians quickly resolve faults using EXCLUSIVELY the information contained in the provided technical documents.

IMPORTANT: Always respond in English, regardless of the language of the question.

FUNDAMENTAL RULES:
1. Answer ONLY based on the documents provided in the context
2. If the information is not present in the documents, clearly state "I could not find this information in the available manuals"
3. Always cite the source: indicate the document name and page number when possible
4. Provide clear, step-by-step instructions in numbered list format
5. Use appropriate but understandable technical terminology
6. If the question concerns safety procedures, always highlight them

RESPONSE FORMAT:
- Start with a brief summary of the solution
- List the steps in an orderly manner
- Indicate any safety warnings
- Cite sources at the end

DOCUMENT CONTEXT:
{context}

Answer the technician's question professionally and precisely in English."""


def format_docs(docs: List[Document]) -> str:
    """Format retrieved documents for context."""
    formatted = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "Unknown document")
        page = doc.metadata.get("page", "N/A")
        chapter = doc.metadata.get("chapter", "")
        section = doc.metadata.get("section", "")

        location_info = f"Source: {source}, Page: {page}"
        if chapter:
            location_info += f", Chapter: {chapter}"
        if section:
            location_info += f", Section: {section}"

        formatted.append(f"[Document {i}] {location_info}\n{doc.page_content}")
    return "\n\n---\n\n".join(formatted)


def get_rag_chain(model_id: Optional[str] = None, k: int = 4):
    """
    Create RAG chain for question answering.

    Args:
        model_id: LLM model ID to use
        k: Number of documents to retrieve

    Returns:
        Runnable RAG chain
    """
    retriever = get_retriever(k=k)
    llm = get_llm(model_id=model_id)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{question}")
    ])

    chain = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough(),
            "chat_history": lambda x: x.get("chat_history", [])
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain


def format_chat_history(history: List[Dict[str, str]]) -> List[BaseMessage]:
    """Convert chat history dict to LangChain messages."""
    messages = []
    for msg in history:
        if msg.get("role") == "user":
            messages.append(HumanMessage(content=msg.get("content", "")))
        elif msg.get("role") == "assistant":
            messages.append(AIMessage(content=msg.get("content", "")))
    return messages


async def query_rag(
    question: str,
    model_id: Optional[str] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
    k: int = 4,
    use_agent: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Query the RAG system.

    Uses Agentic RAG (multi-hop) by default if enabled in settings.
    Falls back to legacy linear chain if agent is disabled or unavailable.

    Args:
        question: User's question
        model_id: LLM model to use
        chat_history: Previous conversation history
        k: Number of documents to retrieve
        use_agent: Override settings to force agent/legacy mode

    Returns:
        Dict with answer, sources, and metadata
    """
    # Determine if we should use the agentic system
    should_use_agent = use_agent if use_agent is not None else settings.USE_AGENTIC_RAG

    if should_use_agent and is_agentic_rag_available():
        print("Using Agentic RAG (multi-hop retrieval)")
        return await _query_rag_agentic(question, model_id, chat_history)
    else:
        print("Using Legacy RAG (single retrieval)")
        return await _query_rag_legacy(question, model_id, chat_history, k)


async def _query_rag_agentic(
    question: str,
    model_id: Optional[str] = None,
    chat_history: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Query using the Agentic RAG system (multi-hop retrieval).

    The agent can perform multiple searches to gather complete information,
    following references to other pages, tables, or notes.
    """
    result = await query_rag_agent(
        question=question,
        model_id=model_id,
        chat_history=chat_history
    )

    # Format sources for compatibility with existing frontend
    # Now includes full content for trust layer (1000-1500 chars)
    formatted_sources = []
    for source in result.get("sources", []):
        formatted_sources.append({
            "content": source.get("content", "")[:1500],  # Full content for trust layer
            "source": source.get("document", "Unknown"),
            "page": source.get("page"),
            "chapter": source.get("chapter"),
            "section": source.get("section"),
            "chunk_index": source.get("chunk_index"),
            "total_chunks": source.get("total_chunks"),
            "relevance_score": None
        })

    return {
        "answer": result["answer"],
        "sources": formatted_sources,
        "metadata": {
            "mode": "agentic",
            "iterations": result.get("iterations", 0),
            "queries_executed": result.get("queries_executed", [])
        }
    }


async def _query_rag_legacy(
    question: str,
    model_id: Optional[str] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
    k: int = 4,
    use_query_expansion: bool = True
) -> Dict[str, Any]:
    """
    Query using the legacy linear RAG chain with query expansion.

    This implementation now includes query expansion for better retrieval coverage.

    Args:
        question: User's question.
        model_id: LLM model to use.
        chat_history: Previous conversation history.
        k: Number of documents to retrieve.
        use_query_expansion: Whether to use query expansion (default True).
    """
    llm = get_llm(model_id=model_id)
    queries_executed = [question]

    # Retrieve documents - with or without query expansion
    if use_query_expansion:
        docs = await retrieve_with_expansion(question, model_id, k)
        # Track expanded queries for metadata
        expanded_queries = await expand_query(question, model_id)
        queries_executed = expanded_queries
    else:
        retriever = get_retriever(k=k)
        docs = retriever.invoke(question)

    # Format context
    context = format_docs(docs)

    # Format history
    history_messages = format_chat_history(chat_history or [])

    # Create prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{question}")
    ])

    # Generate response
    chain = prompt | llm | StrOutputParser()
    answer = await chain.ainvoke({
        "context": context,
        "question": question,
        "chat_history": history_messages
    })

    # Format source documents for response with extended metadata
    sources = [
        {
            "content": doc.page_content[:1500],  # Extended content for trust layer
            "source": doc.metadata.get("source", "Unknown"),
            "page": doc.metadata.get("page"),
            "chapter": doc.metadata.get("chapter"),
            "section": doc.metadata.get("section"),
            "chunk_index": doc.metadata.get("chunk_index"),
            "total_chunks": doc.metadata.get("total_chunks"),
            "relevance_score": doc.metadata.get("score")
        }
        for doc in docs
    ]

    return {
        "answer": answer,
        "sources": sources,
        "metadata": {
            "mode": "legacy_with_expansion" if use_query_expansion else "legacy",
            "iterations": 1,
            "queries_executed": queries_executed
        }
    }


# =============================================================================
# STREAMING RAG
# =============================================================================

async def query_rag_stream(
    question: str,
    model_id: Optional[str] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
    k: int = 4,
    use_query_expansion: bool = True
) -> AsyncGenerator[str, None]:
    """
    Stream RAG responses for reduced perceived latency.

    Uses Agentic RAG (multi-hop retrieval via LangGraph) when enabled,
    falling back to legacy single-pass retrieval with query expansion.

    This function yields Server-Sent Events (SSE) formatted messages:
    - "event: status" + "data: <json>" for processing status updates
    - "event: token" + "data: <token>" for each generated token
    - "event: sources" + "data: <json>" for source documents at the end
    - "event: metadata" + "data: <json>" for RAG metadata at the end
    - "event: done" + "data: [DONE]" when streaming is complete

    Args:
        question: User's question.
        model_id: LLM model to use.
        chat_history: Previous conversation history.
        k: Number of documents to retrieve.
        use_query_expansion: Whether to use query expansion (legacy mode).

    Yields:
        SSE formatted strings.
    """
    llm = get_llm(model_id=model_id)
    queries_executed = [question]

    # Emit initial status
    yield f"event: status\ndata: {json.dumps({'step': 'analyzing', 'message': 'Analyzing your question...'})}\n\n"

    # Check if we should use agentic multi-hop retrieval
    should_use_agent = settings.USE_AGENTIC_RAG and is_agentic_rag_available()

    if should_use_agent:
        # =============================================================
        # AGENTIC RAG: Multi-hop retrieval with LangGraph
        # The agent follows references across pages for complete answers
        # =============================================================
        from app.rag.agent import run_agentic_retrieval_streaming

        print("Streaming: Using Agentic RAG (multi-hop retrieval)")
        yield f"event: status\ndata: {json.dumps({'step': 'expanding', 'message': 'Planning multi-hop retrieval...'})}\n\n"

        agent_docs = []
        async for event in run_agentic_retrieval_streaming(question, model_id, chat_history):
            if event['type'] == 'status':
                yield f"event: status\ndata: {json.dumps({'step': event['step'], 'message': event['message'], 'query': event.get('query', ''), 'index': event.get('index')})}\n\n"
            elif event['type'] == 'result':
                agent_docs = event['docs']
                queries_executed = event['queries_executed']

        # Convert agent docs to Document objects for format_docs
        docs = []
        for d in agent_docs:
            doc = Document(
                page_content=d.get('content', ''),
                metadata={
                    'source': d.get('source', 'Unknown'),
                    'page': d.get('page'),
                    'chapter': d.get('chapter'),
                    'section': d.get('section'),
                    'chunk_index': d.get('chunk_index'),
                    'total_chunks': d.get('total_chunks'),
                }
            )
            docs.append(doc)

        yield f"event: status\ndata: {json.dumps({'step': 'processing', 'message': f'Retrieved {len(docs)} documents across {len(queries_executed)} searches'})}\n\n"

        mode = "agentic_streaming"

    elif use_query_expansion:
        # =============================================================
        # LEGACY RAG: Single-pass retrieval with query expansion
        # =============================================================
        print("Streaming: Using Legacy RAG (query expansion)")
        yield f"event: status\ndata: {json.dumps({'step': 'expanding', 'message': 'Expanding search queries...'})}\n\n"

        expanded_queries = await expand_query(question, model_id)
        queries_executed = expanded_queries

        retriever = get_retriever(k=k)
        all_docs = []
        seen_content = set()

        for i, query in enumerate(expanded_queries, 1):
            short_query = query[:50] + "..." if len(query) > 50 else query
            yield f"event: status\ndata: {json.dumps({'step': 'searching', 'message': f'Search {i}: {short_query}', 'query': query, 'index': i, 'total': len(expanded_queries)})}\n\n"

            retriever_docs = retriever.invoke(query)
            for doc in retriever_docs:
                content_hash = hash(doc.page_content[:500])
                if content_hash not in seen_content:
                    seen_content.add(content_hash)
                    all_docs.append(doc)

        docs = all_docs[:k * 2]

        yield f"event: status\ndata: {json.dumps({'step': 'processing', 'message': f'Found {len(docs)} relevant documents'})}\n\n"

        mode = "streaming_with_expansion"

    else:
        # =============================================================
        # BASIC RAG: Simple single-query retrieval
        # =============================================================
        print("Streaming: Using Basic RAG (no expansion)")
        yield f"event: status\ndata: {json.dumps({'step': 'searching', 'message': 'Searching documentation...'})}\n\n"
        retriever = get_retriever(k=k)
        docs = retriever.invoke(question)

        mode = "streaming"

    # =============================================================
    # GENERATE STREAMED RESPONSE
    # =============================================================
    yield f"event: status\ndata: {json.dumps({'step': 'generating', 'message': 'Generating response...'})}\n\n"

    # Format context from retrieved documents
    context = format_docs(docs)

    # Format history
    history_messages = format_chat_history(chat_history or [])

    # Create prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{question}")
    ])

    # Prepare chain for streaming
    chain = prompt | llm

    # Stream tokens
    full_answer = ""
    async for chunk in chain.astream({
        "context": context,
        "question": question,
        "chat_history": history_messages
    }):
        # Extract token from chunk
        if hasattr(chunk, 'content'):
            token = chunk.content
        else:
            token = str(chunk)

        if token:
            full_answer += token
            # Yield SSE formatted token
            yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"

    # Format source documents for response
    sources = [
        {
            "content": doc.page_content[:1500],
            "source": doc.metadata.get("source", "Unknown"),
            "page": doc.metadata.get("page"),
            "chapter": doc.metadata.get("chapter"),
            "section": doc.metadata.get("section"),
            "chunk_index": doc.metadata.get("chunk_index"),
            "total_chunks": doc.metadata.get("total_chunks"),
            "relevance_score": doc.metadata.get("score")
        }
        for doc in docs
    ]

    # Yield sources
    yield f"event: sources\ndata: {json.dumps(sources)}\n\n"

    # Yield metadata
    metadata = {
        "mode": mode,
        "iterations": len(queries_executed),
        "queries_executed": queries_executed
    }
    yield f"event: metadata\ndata: {json.dumps(metadata)}\n\n"

    # Signal completion
    yield f"event: done\ndata: [DONE]\n\n"