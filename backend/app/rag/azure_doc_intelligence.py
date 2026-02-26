"""
Azure Document Intelligence PDF Parser Module.

Replaces LlamaParse with Azure AI Document Intelligence for PDF parsing.
Uses the prebuilt-layout model for accurate extraction of tables,
figures, and structured content in Markdown format.
"""
import io
from pathlib import Path
from typing import List, Optional

from langchain_core.documents import Document
from app.core.config import settings


def _get_client():
    """Get Azure Document Intelligence client."""
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.core.credentials import AzureKeyCredential

    return DocumentIntelligenceClient(
        endpoint=settings.AZURE_DOC_INTELLIGENCE_ENDPOINT,
        credential=AzureKeyCredential(settings.AZURE_DOC_INTELLIGENCE_KEY),
    )


def load_pdf_with_azure_di(pdf_path: Path, file_metadata: dict) -> List[Document]:
    """
    Load a PDF using Azure Document Intelligence and add metadata.

    Uses prebuilt-layout for accurate table/figure extraction with
    Markdown output format (similar to LlamaParse markdown mode).

    Args:
        pdf_path: Path to the PDF file.
        file_metadata: Metadata extracted from filename.

    Returns:
        List of Document objects with content and metadata.
    """
    try:
        client = _get_client()

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        output_format = settings.DOC_INTELLIGENCE_OUTPUT_FORMAT

        poller = client.begin_analyze_document(
            "prebuilt-layout",
            body=pdf_bytes,
            content_type="application/pdf",
            output_content_format=output_format,
        )
        result = poller.result()

        documents = []

        if result.pages:
            for page in result.pages:
                page_number = page.page_number

                page_content = _extract_page_content(result, page_number)

                if page_content.strip():
                    lc_doc = Document(
                        page_content=page_content,
                        metadata={
                            **file_metadata,
                            "source": pdf_path.name,
                            "page": page_number,
                            "parser": "azure_doc_intelligence",
                            "result_type": output_format,
                        },
                    )
                    documents.append(lc_doc)

        if not documents and result.content:
            lc_doc = Document(
                page_content=result.content,
                metadata={
                    **file_metadata,
                    "source": pdf_path.name,
                    "page": 1,
                    "parser": "azure_doc_intelligence",
                    "result_type": output_format,
                },
            )
            documents.append(lc_doc)

        print(f"  -> Azure DI extracted {len(documents)} pages from {pdf_path.name}")
        return documents

    except Exception as e:
        print(f"Error loading {pdf_path.name} with Azure Document Intelligence: {e}")
        return []


def _extract_page_content(result, page_number: int) -> str:
    """
    Extract content for a specific page from the analysis result.

    If the result has markdown content, attempts to split by page.
    Otherwise falls back to the full content for page 1.
    """
    if not result.content:
        return ""

    if hasattr(result, "pages") and result.pages:
        page_spans = []
        for page in result.pages:
            if page.page_number == page_number and hasattr(page, "spans") and page.spans:
                for span in page.spans:
                    page_spans.append((span.offset, span.offset + span.length))

        if page_spans:
            content_parts = []
            for start, end in sorted(page_spans):
                content_parts.append(result.content[start:end])
            return "\n".join(content_parts)

    if page_number == 1:
        return result.content

    return ""


def is_azure_di_available() -> bool:
    """Check if Azure Document Intelligence is properly configured and available."""
    if not settings.AZURE_DOC_INTELLIGENCE_ENDPOINT:
        print("Warning: AZURE_DOC_INTELLIGENCE_ENDPOINT not configured")
        return False

    if not settings.AZURE_DOC_INTELLIGENCE_KEY:
        print("Warning: AZURE_DOC_INTELLIGENCE_KEY not configured")
        return False

    if not settings.USE_AZURE_DOC_INTELLIGENCE:
        print("Info: Azure Document Intelligence disabled in config")
        return False

    try:
        from azure.ai.documentintelligence import DocumentIntelligenceClient
        return True
    except ImportError:
        print("Warning: azure-ai-documentintelligence package not installed")
        return False
