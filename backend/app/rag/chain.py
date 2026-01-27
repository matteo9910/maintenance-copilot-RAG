"""RAG Chain Implementation.

This module provides two RAG modes:
1. Agentic RAG (default): Uses LangGraph for multi-hop retrieval
2. Legacy RAG: Linear chain with single retrieval (fallback)

The mode is controlled by settings.USE_AGENTIC_RAG.
"""
from typing import Optional, List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings
from app.rag.llm import get_llm
from app.rag.vector_store import get_retriever
from app.rag.agent import query_rag_agent, is_agentic_rag_available


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
    formatted_sources = []
    for source in result.get("sources", []):
        formatted_sources.append({
            "content": "",  # Agent doesn't return full content
            "source": source.get("document", "Unknown"),
            "page": source.get("page"),
            "chapter": None,
            "section": None,
            "chunk_index": None,
            "total_chunks": None,
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
    k: int = 4
) -> Dict[str, Any]:
    """
    Query using the legacy linear RAG chain (single retrieval).

    This is the original implementation that performs one similarity search.
    """
    retriever = get_retriever(k=k)
    llm = get_llm(model_id=model_id)

    # Retrieve relevant documents
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
            "mode": "legacy",
            "iterations": 1,
            "queries_executed": [question]
        }
    }