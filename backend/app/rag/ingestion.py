"""PDF Ingestion Pipeline for Knowledge Base."""
import os
import re
from pathlib import Path
from typing import List, Dict, Optional
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader

from app.core.config import settings
from app.rag.vector_store import get_vector_store, clear_collection, get_collection_stats


def extract_metadata_from_filename(filename: str) -> Dict[str, str]:
    """
    Extract metadata from PDF filename.
    Example: 'Manuale_Pressa_T800.pdf' -> {'machine': 'pressa_t800', 'doc_type': 'manuale'}
    """
    # Remove extension and convert to lowercase
    name = Path(filename).stem.lower()

    # Replace common separators with spaces
    name_clean = re.sub(r'[-_]', ' ', name)

    # Try to identify document type
    doc_types = ['manual', 'manuale', 'maintenance', 'manutenzione', 'user', 'service']
    doc_type = 'technical'
    for dt in doc_types:
        if dt in name_clean:
            doc_type = dt
            break

    # Extract machine/equipment name (remove common words)
    stop_words = ['manual', 'manuale', 'maintenance', 'manutenzione', 'user', 'service', 'guide', 'guida', 'series']
    words = name_clean.split()
    machine_words = [w for w in words if w not in stop_words and len(w) > 1]
    machine_name = '_'.join(machine_words) if machine_words else name

    return {
        "machine": machine_name,
        "doc_type": doc_type,
        "original_filename": filename
    }


def load_pdf(pdf_path: Path) -> List[Document]:
    """Load a single PDF and return documents with metadata."""
    try:
        loader = PyPDFLoader(str(pdf_path))
        pages = loader.load()

        # Extract metadata from filename
        file_metadata = extract_metadata_from_filename(pdf_path.name)

        # Add metadata to each page
        for page in pages:
            page.metadata.update(file_metadata)
            page.metadata["source"] = pdf_path.name

        return pages
    except Exception as e:
        print(f"Error loading {pdf_path.name}: {e}")
        return []


def chunk_documents(documents: List[Document], chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Document]:
    """Split documents into chunks for embedding with chunk index metadata."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    chunks = text_splitter.split_documents(documents)

    # Group chunks by source and add chunk index metadata
    source_chunks: Dict[str, List[Document]] = {}
    for chunk in chunks:
        source = chunk.metadata.get("source", "unknown")
        if source not in source_chunks:
            source_chunks[source] = []
        source_chunks[source].append(chunk)

    # Add chunk index and total chunks metadata
    for source, source_chunk_list in source_chunks.items():
        total = len(source_chunk_list)
        for idx, chunk in enumerate(source_chunk_list, 1):
            chunk.metadata["chunk_index"] = idx
            chunk.metadata["total_chunks"] = total
            # Try to extract section info from content
            content_preview = chunk.page_content[:200].lower()
            if "chapter" in content_preview or "capitolo" in content_preview:
                chunk.metadata["section_type"] = "chapter"
            elif "section" in content_preview or "sezione" in content_preview:
                chunk.metadata["section_type"] = "section"

    return chunks


def ingest_pdfs(
    pdf_directory: Optional[str] = None,
    clear_existing: bool = False,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> Dict[str, any]:
    """
    Ingest all PDFs from directory into ChromaDB.

    Args:
        pdf_directory: Path to PDF directory. Uses config default if not provided.
        clear_existing: If True, clears existing collection before ingestion.
        chunk_size: Size of text chunks.
        chunk_overlap: Overlap between chunks.

    Returns:
        Dict with ingestion statistics.
    """
    pdf_dir = Path(pdf_directory or settings.RAW_PDFS_DIRECTORY)

    if not pdf_dir.exists():
        return {
            "success": False,
            "error": f"Directory not found: {pdf_dir}",
            "files_processed": 0,
            "chunks_created": 0
        }

    # Find all PDFs
    pdf_files = list(pdf_dir.glob("*.pdf"))

    if not pdf_files:
        return {
            "success": False,
            "error": f"No PDF files found in {pdf_dir}",
            "files_processed": 0,
            "chunks_created": 0
        }

    # Clear existing if requested
    if clear_existing:
        clear_collection()

    # Load all PDFs
    all_documents = []
    files_processed = []
    files_failed = []

    for pdf_path in pdf_files:
        print(f"Loading: {pdf_path.name}")
        docs = load_pdf(pdf_path)
        if docs:
            all_documents.extend(docs)
            files_processed.append(pdf_path.name)
        else:
            files_failed.append(pdf_path.name)

    if not all_documents:
        return {
            "success": False,
            "error": "No documents could be loaded from PDFs",
            "files_processed": 0,
            "chunks_created": 0
        }

    # Chunk documents
    print(f"Chunking {len(all_documents)} pages...")
    chunks = chunk_documents(all_documents, chunk_size, chunk_overlap)

    # Add to vector store
    print(f"Adding {len(chunks)} chunks to vector store...")
    vector_store = get_vector_store()
    vector_store.add_documents(chunks)

    # Get final stats
    stats = get_collection_stats()

    return {
        "success": True,
        "files_processed": len(files_processed),
        "files_failed": len(files_failed),
        "pages_loaded": len(all_documents),
        "chunks_created": len(chunks),
        "total_documents_in_db": stats.get("count", 0),
        "processed_files": files_processed,
        "failed_files": files_failed
    }


def get_indexed_documents() -> List[Dict[str, any]]:
    """Get list of documents currently indexed in the vector store."""
    try:
        vector_store = get_vector_store()
        collection = vector_store._collection

        # Get all unique sources
        results = collection.get(include=["metadatas"])

        if not results or not results.get("metadatas"):
            return []

        # Aggregate by source file
        sources = {}
        for metadata in results["metadatas"]:
            source = metadata.get("source", "Unknown")
            if source not in sources:
                sources[source] = {
                    "filename": source,
                    "machine": metadata.get("machine", "Unknown"),
                    "doc_type": metadata.get("doc_type", "Unknown"),
                    "chunk_count": 0
                }
            sources[source]["chunk_count"] += 1

        return list(sources.values())
    except Exception as e:
        print(f"Error getting indexed documents: {e}")
        return []
