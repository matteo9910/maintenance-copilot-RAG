"""
Agentic RAG Module using LangGraph.

This module implements an intelligent RAG agent that can perform
multi-hop retrieval to answer complex questions that require
cross-referencing multiple sections of documentation.

Key Features:
- Multi-hop retrieval: Agent can search multiple times to gather complete information
- Loop detection: Prevents infinite loops by tracking search queries
- Configurable iteration limit: Safety net for maximum agent iterations
- Transparent reasoning: Each step is logged for debugging and trust
"""
from typing import TypedDict, Annotated, List, Dict, Any, Optional, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
import operator

from app.core.config import settings
from app.rag.vector_store import get_retriever
from app.rag.llm import get_llm


# =============================================================================
# STATE DEFINITION
# =============================================================================

class AgentState(TypedDict):
    """State schema for the RAG agent."""
    # Conversation messages
    messages: Annotated[Sequence[BaseMessage], operator.add]
    # Original user question
    original_question: str
    # Retrieved documents accumulated across hops
    retrieved_documents: List[Dict[str, Any]]
    # Search queries already executed (for loop detection)
    executed_queries: List[str]
    # Number of retrieval iterations
    iteration_count: int
    # Final answer (when ready)
    final_answer: Optional[str]


# =============================================================================
# RETRIEVAL TOOL
# =============================================================================

# Global storage for retrieved documents during agent execution
# This allows us to capture full document content for the trust layer
_retrieved_documents_store: List[Dict[str, Any]] = []


def clear_retrieved_documents():
    """Clear the retrieved documents store before a new query."""
    global _retrieved_documents_store
    _retrieved_documents_store = []


def get_retrieved_documents() -> List[Dict[str, Any]]:
    """Get all documents retrieved during agent execution."""
    global _retrieved_documents_store
    return _retrieved_documents_store


def create_retrieval_tool(k: int = 4):
    """
    Create a retrieval tool for the agent.

    This tool searches the maintenance documentation knowledge base
    and returns relevant document chunks.

    Args:
        k: Number of documents to retrieve per search.

    Returns:
        Configured retrieval tool.
    """
    retriever = get_retriever(k=k)

    @tool
    def search_maintenance_docs(query: str) -> str:
        """
        Search the maintenance documentation knowledge base.

        Use this tool to find information about:
        - Maintenance procedures and schedules
        - Error codes and troubleshooting
        - Part specifications and replacement procedures
        - Lubrication intervals and requirements
        - Safety procedures and warnings

        If the search results mention references to other pages, tables,
        or notes (e.g., "See Table 5-10", "Refer to Page 131", "Note 4"),
        you should perform another search to find that specific content.

        Args:
            query: Search query describing what information you need.

        Returns:
            Relevant documentation excerpts with source information.
        """
        global _retrieved_documents_store
        docs = retriever.invoke(query)

        if not docs:
            return "No relevant documents found for this query."

        # Format results with clear source attribution
        results = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "Unknown")
            page = doc.metadata.get("page", "N/A")
            chapter = doc.metadata.get("chapter")
            section = doc.metadata.get("section")
            chunk_index = doc.metadata.get("chunk_index")
            total_chunks = doc.metadata.get("total_chunks")
            # Store full content for trust layer (1500 chars as per requirement)
            full_content = doc.page_content[:1500]

            # Store document with full metadata for trust layer
            doc_entry = {
                "content": full_content,
                "source": source,
                "page": page if page != "N/A" else None,
                "chapter": chapter,
                "section": section,
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
                "query": query
            }

            # Avoid duplicates based on source + page + chunk_index
            is_duplicate = any(
                d["source"] == source and d["page"] == doc_entry["page"] and d.get("chunk_index") == chunk_index
                for d in _retrieved_documents_store
            )
            if not is_duplicate:
                _retrieved_documents_store.append(doc_entry)

            results.append(
                f"[Document {i}]\n"
                f"Source: {source} (Page {page})\n"
                f"Content:\n{full_content}\n"
                f"---"
            )

        return "\n\n".join(results)

    return search_maintenance_docs


# =============================================================================
# AGENT PROMPTS
# =============================================================================

AGENT_SYSTEM_PROMPT = """You are an expert maintenance technician assistant with access to a comprehensive knowledge base of technical maintenance manuals.

## Your Mission
Help users with maintenance questions by searching the documentation and providing accurate, actionable answers.

## Critical Instructions

1. **ALWAYS Search First**: Before answering any maintenance question, use the search_maintenance_docs tool to find relevant information.

2. **Follow References**: If search results mention:
   - "See Table X" or "Refer to Table X"
   - "See Page X" or "Refer to Page X"
   - "Note X" or "See Note X"
   - "Section X" or "Chapter X"

   You MUST perform an additional search to find that referenced content. Do NOT guess or assume what the reference contains.

3. **Multi-hop Reasoning**: Complex questions often require multiple searches. For example:
   - First search: Find the maintenance schedule
   - Second search: Find the referenced lubrication specifications
   - Third search: Find the specific procedure details

4. **When to Stop Searching**:
   - You have found all referenced information
   - You have performed the same search query twice (avoid loops)
   - You have gathered enough information to provide a complete answer

5. **Answer Format**:
   - Provide clear, step-by-step instructions when applicable
   - Always cite your sources (document name and page number)
   - If information is incomplete or contradictory, acknowledge this
   - Use technical terminology accurately

6. **Language**: ALWAYS respond in English, regardless of the document language.

## Example Reasoning

User: "At 300 operating hours, do I need to lubricate the components?"

Your thought process:
1. Search for "300 hours maintenance schedule"
2. Find: "Lubrication: As appropriate (Note 4)"
3. Recognize: Need to find Note 4 content
4. Search for "Note 4 lubrication interval" or "lubrication specifications table"
5. Find: "Table 5-10: J1 axis = 24,000 Hr, Shaft = Every 2,000km movement"
6. Now provide complete answer with all details

Remember: Incomplete information leads to incorrect maintenance, which can cause equipment damage or safety hazards. Always be thorough."""


# =============================================================================
# AGENT NODES
# =============================================================================

def create_agent_node(model_id: Optional[str] = None):
    """
    Create the agent reasoning node.

    This node decides whether to search for more information
    or provide a final answer.
    """
    llm = get_llm(model_id=model_id)
    tools = [create_retrieval_tool()]

    # Bind tools to LLM
    llm_with_tools = llm.bind_tools(tools)

    prompt = ChatPromptTemplate.from_messages([
        ("system", AGENT_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
    ])

    chain = prompt | llm_with_tools

    def agent_node(state: AgentState) -> Dict[str, Any]:
        """Process the current state and decide next action."""
        response = chain.invoke({"messages": state["messages"]})
        return {"messages": [response]}

    return agent_node


def should_continue(state: AgentState) -> str:
    """
    Determine if the agent should continue searching or end.

    Returns:
        "tools" to continue with tool execution
        "end" to finish and return answer
    """
    messages = state["messages"]
    last_message = messages[-1]

    # If no tool calls, agent is done
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return "end"

    # Check iteration limit
    iteration_count = state.get("iteration_count", 0)
    max_iterations = settings.MAX_AGENT_ITERATIONS

    if iteration_count >= max_iterations:
        print(f"Agent reached max iterations ({max_iterations}), forcing end")
        return "end"

    # Loop detection: check if we're repeating queries
    executed_queries = state.get("executed_queries", [])
    for tool_call in last_message.tool_calls:
        if tool_call.get("name") == "search_maintenance_docs":
            query = tool_call.get("args", {}).get("query", "")
            if query in executed_queries:
                print(f"Loop detected: query '{query}' already executed")
                return "end"

    return "tools"


def create_tool_node():
    """Create the tool execution node."""
    tools = [create_retrieval_tool()]
    return ToolNode(tools)


def update_state_after_tools(state: AgentState) -> Dict[str, Any]:
    """
    Update state after tool execution.

    Tracks executed queries and increments iteration count.
    """
    messages = state["messages"]
    executed_queries = list(state.get("executed_queries", []))
    iteration_count = state.get("iteration_count", 0)

    # Find the most recent AI message with tool calls
    for msg in reversed(messages):
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tool_call in msg.tool_calls:
                if tool_call.get("name") == "search_maintenance_docs":
                    query = tool_call.get("args", {}).get("query", "")
                    if query and query not in executed_queries:
                        executed_queries.append(query)
            break

    return {
        "executed_queries": executed_queries,
        "iteration_count": iteration_count + 1
    }


# =============================================================================
# GRAPH CONSTRUCTION
# =============================================================================

def create_rag_agent(model_id: Optional[str] = None) -> StateGraph:
    """
    Create the RAG agent graph.

    The graph structure:

    START -> agent -> [should_continue?]
                          |
              +-----------+-----------+
              |                       |
           "tools"                  "end"
              |                       |
              v                       v
         tool_node                   END
              |
              v
        update_state
              |
              +---> agent (loop back)

    Args:
        model_id: Optional LLM model ID to use.

    Returns:
        Compiled LangGraph agent.
    """
    # Create the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent", create_agent_node(model_id))
    workflow.add_node("tools", create_tool_node())
    workflow.add_node("update_state", update_state_after_tools)

    # Set entry point
    workflow.set_entry_point("agent")

    # Add conditional edges from agent
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END
        }
    )

    # Tools -> update_state -> agent (loop)
    workflow.add_edge("tools", "update_state")
    workflow.add_edge("update_state", "agent")

    # Compile the graph
    return workflow.compile()


# =============================================================================
# MAIN QUERY FUNCTION
# =============================================================================

async def query_rag_agent(
    question: str,
    model_id: Optional[str] = None,
    chat_history: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Query the RAG agent with a question.

    This is the main entry point for the agentic RAG system.

    Args:
        question: User's question.
        model_id: Optional LLM model ID.
        chat_history: Optional conversation history.

    Returns:
        Dict containing:
        - answer: The agent's response
        - sources: List of sources used (with full content for trust layer)
        - iterations: Number of retrieval iterations
        - queries_executed: List of search queries performed
    """
    # Clear retrieved documents store before new query
    clear_retrieved_documents()

    # Build initial messages
    messages = []

    # Add chat history if provided
    if chat_history:
        for msg in chat_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

    # Add current question
    messages.append(HumanMessage(content=question))

    # Create initial state
    initial_state: AgentState = {
        "messages": messages,
        "original_question": question,
        "retrieved_documents": [],
        "executed_queries": [],
        "iteration_count": 0,
        "final_answer": None
    }

    # Create and run the agent
    agent = create_rag_agent(model_id)
    final_state = await agent.ainvoke(initial_state)

    # Extract the final answer
    final_messages = final_state["messages"]
    answer = ""
    for msg in reversed(final_messages):
        if isinstance(msg, AIMessage) and not hasattr(msg, "tool_calls"):
            answer = msg.content
            break
        elif isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and not msg.tool_calls:
            answer = msg.content
            break

    # If no clean answer found, get the last AI message content
    if not answer:
        for msg in reversed(final_messages):
            if isinstance(msg, AIMessage):
                answer = msg.content
                break

    # Get all retrieved documents with full content for trust layer
    retrieved_docs = get_retrieved_documents()

    # Format sources with full metadata and content
    sources = []
    seen_sources = set()
    for doc in retrieved_docs:
        source_key = f"{doc['source']}_{doc.get('page')}_{doc.get('chunk_index')}"
        if source_key not in seen_sources:
            seen_sources.add(source_key)
            sources.append({
                "document": doc["source"],
                "page": doc.get("page"),
                "chapter": doc.get("chapter"),
                "section": doc.get("section"),
                "chunk_index": doc.get("chunk_index"),
                "total_chunks": doc.get("total_chunks"),
                "content": doc.get("content", "")  # Full content for trust layer
            })

    return {
        "answer": answer,
        "sources": sources,
        "iterations": final_state.get("iteration_count", 0),
        "queries_executed": final_state.get("executed_queries", [])
    }


def is_agentic_rag_available() -> bool:
    """
    Check if Agentic RAG is enabled and available.

    Returns:
        bool: True if Agentic RAG can be used.
    """
    if not settings.USE_AGENTIC_RAG:
        return False

    try:
        from langgraph.graph import StateGraph
        return True
    except ImportError:
        print("Warning: langgraph package not installed")
        return False
