"""
LlamaParse PDF Parser Module.

This module provides advanced PDF parsing capabilities using LlamaParse,
which uses vision models to accurately extract structured content from PDFs,
including complex tables with merged cells.
"""
import os
import asyncio
from pathlib import Path
from typing import List, Optional
from langchain_core.documents import Document

from app.core.config import settings


def get_llama_parse_client():
    """
    Get LlamaParse client instance.

    Returns:
        LlamaParse: Configured LlamaParse client.
    """
    from llama_parse import LlamaParse

    return LlamaParse(
        api_key=settings.LLAMA_CLOUD_API_KEY,
        result_type=settings.LLAMA_PARSE_RESULT_TYPE,  # "markdown" for structured tables
        verbose=True,
        language="en",  # Can be changed to "it" for Italian documents
    )


async def parse_pdf_with_llama(pdf_path: Path) -> List[Document]:
    """
    Parse a single PDF using LlamaParse (async version).

    LlamaParse uses vision models to understand document layout,
    preserving table structure and merged cells in Markdown format.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        List of Document objects with parsed content.
    """
    try:
        parser = get_llama_parse_client()

        # LlamaParse returns a list of parsed documents
        parsed_documents = await parser.aload_data(str(pdf_path))

        # Convert to LangChain Document format
        documents = []
        for idx, doc in enumerate(parsed_documents):
            # Create LangChain Document with metadata
            lc_doc = Document(
                page_content=doc.text,
                metadata={
                    "source": pdf_path.name,
                    "page": idx + 1,
                    "parser": "llama_parse",
                    "result_type": settings.LLAMA_PARSE_RESULT_TYPE
                }
            )
            documents.append(lc_doc)

        return documents

    except Exception as e:
        print(f"Error parsing {pdf_path.name} with LlamaParse: {e}")
        return []


def parse_pdf_with_llama_sync(pdf_path: Path) -> List[Document]:
    """
    Parse a single PDF using LlamaParse (sync wrapper).

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        List of Document objects with parsed content.
    """
    try:
        # Run async function in sync context
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If already in async context, create new loop
            import nest_asyncio
            nest_asyncio.apply()
        return asyncio.run(parse_pdf_with_llama(pdf_path))
    except RuntimeError:
        # Fallback for environments without event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(parse_pdf_with_llama(pdf_path))
        finally:
            loop.close()


def load_pdf_with_llama_parse(pdf_path: Path, file_metadata: dict) -> List[Document]:
    """
    Load a PDF using LlamaParse and add metadata.

    This is the main entry point for PDF loading, compatible with
    the existing ingestion pipeline.

    Args:
        pdf_path: Path to the PDF file.
        file_metadata: Metadata extracted from filename.

    Returns:
        List of Document objects with content and metadata.
    """
    try:
        parser = get_llama_parse_client()

        # Use sync load for simplicity in ingestion pipeline
        parsed_documents = parser.load_data(str(pdf_path))

        # Convert to LangChain Document format with metadata
        documents = []
        for idx, doc in enumerate(parsed_documents):
            lc_doc = Document(
                page_content=doc.text,
                metadata={
                    **file_metadata,
                    "source": pdf_path.name,
                    "page": idx + 1,
                    "parser": "llama_parse",
                    "result_type": settings.LLAMA_PARSE_RESULT_TYPE
                }
            )
            documents.append(lc_doc)

        print(f"  -> LlamaParse extracted {len(documents)} pages from {pdf_path.name}")
        return documents

    except Exception as e:
        print(f"Error loading {pdf_path.name} with LlamaParse: {e}")
        # Return empty list, caller can fallback to PyPDFLoader
        return []


def is_llama_parse_available() -> bool:
    """
    Check if LlamaParse is properly configured and available.

    Returns:
        bool: True if LlamaParse can be used.
    """
    if not settings.LLAMA_CLOUD_API_KEY:
        print("Warning: LLAMA_CLOUD_API_KEY not configured")
        return False

    if not settings.USE_LLAMA_PARSE:
        print("Info: LlamaParse disabled in config (USE_LLAMA_PARSE=False)")
        return False

    try:
        from llama_parse import LlamaParse
        return True
    except ImportError:
        print("Warning: llama-parse package not installed")
        return False
