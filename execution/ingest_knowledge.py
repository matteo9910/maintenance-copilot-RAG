"""
Knowledge Ingestion Script
Parses PDF documents and stores embeddings in ChromaDB.
This script is IDEMPOTENT - running it twice won't duplicate vectors.
"""
import os
import sys
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# Change to backend directory for correct .env loading
os.chdir(backend_path)

from dotenv import load_dotenv

# Load environment variables
load_dotenv(backend_path / ".env")


def main():
    """Main ingestion function."""
    print("=" * 60)
    print("  MAINTENANCE AI COPILOT - Knowledge Ingestion")
    print("=" * 60)

    # Import after path setup
    from app.rag.ingestion import ingest_pdfs, get_indexed_documents
    from app.rag.vector_store import get_collection_stats

    # Get current stats
    print("\n[1/3] Checking current knowledge base status...")
    stats = get_collection_stats()
    print(f"      Collection: {stats.get('name')}")
    print(f"      Current documents: {stats.get('count', 0)}")

    # Run ingestion
    print("\n[2/3] Starting PDF ingestion...")
    print("-" * 40)

    result = ingest_pdfs(clear_existing=True)

    if result["success"]:
        print("-" * 40)
        print(f"\n[SUCCESS] Ingestion completed!")
        print(f"      Files processed: {result['files_processed']}")
        print(f"      Pages loaded: {result.get('pages_loaded', 'N/A')}")
        print(f"      Chunks created: {result['chunks_created']}")
        print(f"      Total in DB: {result['total_documents_in_db']}")

        if result.get("processed_files"):
            print("\n      Processed files:")
            for f in result["processed_files"]:
                print(f"        - {f}")

        if result.get("failed_files"):
            print("\n      Failed files:")
            for f in result["failed_files"]:
                print(f"        - {f}")
    else:
        print(f"\n[ERROR] Ingestion failed: {result.get('error')}")
        return

    # Show indexed documents summary
    print("\n[3/3] Knowledge base summary:")
    print("-" * 40)
    documents = get_indexed_documents()
    for doc in documents:
        print(f"      {doc['filename']}")
        print(f"        Machine: {doc['machine']}")
        print(f"        Type: {doc['doc_type']}")
        print(f"        Chunks: {doc['chunk_count']}")

    print("\n" + "=" * 60)
    print("  Ingestion complete. Backend ready to serve queries.")
    print("=" * 60)


if __name__ == "__main__":
    main()
