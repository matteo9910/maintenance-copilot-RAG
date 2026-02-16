"""
PDF Image Extraction Module using PyMuPDF (Region-based Rendering).

Uses a caption-anchored approach to extract complete figure regions:
1. Detects embedded image bounding boxes on each page
2. Groups nearby images into clusters
3. Searches for figure caption text (e.g. "Fig.2-4") below each cluster
4. Expands the region to include ALL content (annotations, labels, arrows)
   between the image cluster and the caption
5. Renders the complete region using get_pixmap(clip=rect) at high DPI

This captures the full visual composition including vector graphics,
text annotations, labels, and all embedded images - exactly as they
appear in the original PDF document.
"""
import json
import re
import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.core.config import settings

# Base directory for extracted images
IMAGES_BASE_DIR = Path(settings.RAW_PDFS_DIRECTORY).parent / "images"

# Rendering quality (DPI). PDF default is 72 DPI.
RENDER_DPI = 200
ZOOM_FACTOR = RENDER_DPI / 72

# Minimum dimensions for images to be considered (in PDF points, 1pt = 1/72 inch)
MIN_IMAGE_WIDTH_PT = 50
MIN_IMAGE_HEIGHT_PT = 50

# Images within this distance (in points) are grouped into one figure
MERGE_DISTANCE_PT = 50

# Padding around detected figure regions (in points)
FIGURE_PADDING_PT = 10

# Max distance (pts) below an image region to search for a figure caption.
# Technical manuals often have vector drawings, annotations, and labels between
# the image cluster and the "Fig.X-Y" caption text. Analysis of the Mitsubishi
# manual shows distances up to 493pt, so this must cover the full range.
CAPTION_SEARCH_DISTANCE_PT = 500

# Regex patterns that identify figure captions in technical manuals
FIGURE_CAPTION_PATTERNS = [
    re.compile(r"Fig\.\s*\d", re.IGNORECASE),
    re.compile(r"Figure\s+\d", re.IGNORECASE),
    re.compile(r"図\s*\d"),
]


def get_images_dir(pdf_name: str) -> Path:
    """Get the images directory for a specific PDF."""
    pdf_stem = Path(pdf_name).stem
    return IMAGES_BASE_DIR / pdf_stem


def get_manifest_path(pdf_name: str) -> Path:
    """Get the manifest JSON path for a specific PDF."""
    return get_images_dir(pdf_name) / "manifest.json"


def _merge_rectangles(rects: List[fitz.Rect], merge_distance: float) -> List[fitz.Rect]:
    """
    Merge overlapping or nearby rectangles into larger figure groups.

    Uses iterative merging: keeps combining rectangles that are within
    merge_distance of each other until no more merges are possible.
    This groups all sub-images of a composite figure into a single region.
    """
    if not rects:
        return []

    merged = [fitz.Rect(r) for r in rects]
    changed = True

    while changed:
        changed = False
        new_merged = []
        used = [False] * len(merged)

        for i in range(len(merged)):
            if used[i]:
                continue

            current = fitz.Rect(merged[i])

            for j in range(i + 1, len(merged)):
                if used[j]:
                    continue

                # Expand current rect by merge_distance and check overlap
                expanded = fitz.Rect(
                    current.x0 - merge_distance,
                    current.y0 - merge_distance,
                    current.x1 + merge_distance,
                    current.y1 + merge_distance
                )

                if expanded.intersects(merged[j]):
                    # Merge: union of current and the nearby rect
                    current = current | merged[j]
                    used[j] = True
                    changed = True

            new_merged.append(current)
            used[i] = True

        merged = new_merged

    return merged


def _find_caption_below(
    fig_rect: fitz.Rect,
    text_blocks: List[Tuple],
    search_distance: float,
) -> Optional[fitz.Rect]:
    """
    Search for a figure caption text block below a figure region.

    Looks for text blocks containing patterns like "Fig.2-4" or "Figure 3"
    that sit below the figure's bottom edge (within search_distance).
    The caption does NOT need to horizontally overlap with the image
    since annotations can shift captions left/right.

    Returns the caption's bounding rect, or None if not found.
    """
    best_caption = None
    best_distance = search_distance + 1  # sentinel

    for block in text_blocks:
        # text blocks: (x0, y0, x1, y1, text, block_no, block_type)
        # block_type 0 = text, 1 = image
        if block[6] != 0:
            continue

        bx0, by0, bx1, by1, text = block[0], block[1], block[2], block[3], block[4]

        # Caption must start below (or near the bottom of) the figure
        distance_below = by0 - fig_rect.y1
        if distance_below < -10 or distance_below > search_distance:
            continue

        # Check if the text matches a figure caption pattern
        for pattern in FIGURE_CAPTION_PATTERNS:
            if pattern.search(text):
                if distance_below < best_distance:
                    best_distance = distance_below
                    best_caption = fitz.Rect(bx0, by0, bx1, by1)
                break

    return best_caption


def _expand_region_with_content(
    fig_rect: fitz.Rect,
    text_blocks: List[Tuple],
    image_rects: List[fitz.Rect],
) -> fitz.Rect:
    """
    Expand the figure region horizontally to include all text annotations
    and images that fall within the figure's vertical range.

    Technical figures have labels (Wire, Base, Fixing plate, mass info, etc.)
    placed around the central image. These text blocks are vertically within
    the figure range but may extend far beyond the image's horizontal bounds.

    This function unions all such content to produce the full figure extent.
    """
    y_top = fig_rect.y0
    y_bottom = fig_rect.y1
    result = fitz.Rect(fig_rect)

    # Include text blocks that are vertically within the figure range
    for block in text_blocks:
        if block[6] != 0:
            continue

        bx0, by0, bx1, by1, text = block[0], block[1], block[2], block[3], block[4]
        block_rect = fitz.Rect(bx0, by0, bx1, by1)

        # Skip blocks that are entirely outside the vertical range
        if by1 < y_top - 5 or by0 > y_bottom + 5:
            continue

        # Skip page headers/footers (very top/bottom of page, small text)
        if by0 < 60 or by0 > 780:
            continue

        # Skip what looks like body text paragraphs (numbered instructions)
        # These typically start below the caption and are long text blocks
        if by0 > y_bottom and len(text.strip()) > 100:
            continue

        # Include this text block in the figure region
        result = result | block_rect

    # Also include all image rects that overlap vertically
    for img_rect in image_rects:
        if img_rect.y1 < y_top - 5 or img_rect.y0 > y_bottom + 5:
            continue
        result = result | img_rect

    return result


def extract_images_from_pdf(pdf_path: Path) -> Dict[int, List[str]]:
    """
    Extract complete figure regions from a PDF using page region rendering.

    Uses a caption-anchored approach:
    1. Detects all image bounding boxes using get_image_info()
    2. Filters out small decorative images (icons, bullets)
    3. Groups nearby images into figure clusters using rectangle merging
    4. For each cluster, searches for a figure caption ("Fig.X-Y") below
    5. Expands the region to include all text annotations within the
       vertical range of the figure (labels, notes, mass info, etc.)
    6. Renders the complete region with get_pixmap(clip=rect) at high DPI

    This produces complete figures with all vector graphics, annotations,
    captions and labels preserved - exactly as they appear in the PDF.
    """
    pdf_name = pdf_path.name
    images_dir = get_images_dir(pdf_name)

    # Clear existing images for this PDF
    if images_dir.exists():
        for old_file in images_dir.glob("*.png"):
            old_file.unlink()
        for old_file in images_dir.glob("*.jpeg"):
            old_file.unlink()
        for old_file in images_dir.glob("*.jpg"):
            old_file.unlink()

    images_dir.mkdir(parents=True, exist_ok=True)

    manifest: Dict[int, List[str]] = {}

    try:
        doc = fitz.open(str(pdf_path))
        print(f"  Extracting figure regions from {pdf_name} ({len(doc)} pages)...")

        zoom_matrix = fitz.Matrix(ZOOM_FACTOR, ZOOM_FACTOR)
        total_figures = 0

        for page_num in range(len(doc)):
            page = doc[page_num]
            page_number = page_num + 1

            # Get image info with bounding boxes on the page
            image_info = page.get_image_info(xrefs=True)

            if not image_info:
                continue

            # Collect valid image rectangles (filter out tiny decorative images)
            image_rects = []
            for img in image_info:
                bbox = img.get("bbox")
                if not bbox:
                    continue

                rect = fitz.Rect(bbox)

                # Filter out small images (icons, bullets, decorative elements)
                if rect.width < MIN_IMAGE_WIDTH_PT or rect.height < MIN_IMAGE_HEIGHT_PT:
                    continue

                image_rects.append(rect)

            if not image_rects:
                continue

            # Merge nearby images into figure groups
            figure_regions = _merge_rectangles(image_rects, MERGE_DISTANCE_PT)

            # Get text blocks for caption detection and content expansion
            text_blocks = page.get_text("blocks")

            page_rect = page.rect

            # Phase 1: Build expanded regions for each figure cluster
            expanded_regions = []
            for fig_rect in figure_regions:
                # Step 1: Search for a figure caption below this image cluster
                caption_rect = _find_caption_below(
                    fig_rect, text_blocks, CAPTION_SEARCH_DISTANCE_PT
                )

                # Step 2: Build vertical extent (images top -> caption bottom)
                if caption_rect:
                    fig_rect = fig_rect | caption_rect

                # Step 3: Expand horizontally to include all annotations/labels
                # within the figure's vertical range
                fig_rect = _expand_region_with_content(
                    fig_rect, text_blocks, image_rects
                )

                expanded_regions.append(fig_rect)

            # Phase 2: Merge overlapping expanded regions
            # (e.g. robot arm + CAUTION sign that both map to the same caption)
            final_regions = _merge_rectangles(expanded_regions, 0)

            # Phase 3: Render each unique figure region
            page_images = []
            for fig_idx, fig_rect in enumerate(final_regions):
                # Add small padding for visual breathing room
                padded = fitz.Rect(
                    fig_rect.x0 - FIGURE_PADDING_PT,
                    fig_rect.y0 - FIGURE_PADDING_PT,
                    fig_rect.x1 + FIGURE_PADDING_PT,
                    fig_rect.y1 + FIGURE_PADDING_PT
                )

                # Clip to page bounds
                padded = padded & page_rect

                if padded.is_empty:
                    continue

                # Render the figure region at high DPI
                pixmap = page.get_pixmap(matrix=zoom_matrix, clip=padded)

                image_filename = f"page_{page_number}_fig_{fig_idx + 1}.png"
                image_path = images_dir / image_filename
                pixmap.save(str(image_path))

                page_images.append(image_filename)
                total_figures += 1

            if page_images:
                manifest[page_number] = page_images

        doc.close()

        # Save manifest
        _save_manifest(pdf_name, manifest)

        print(f"  -> Rendered {total_figures} figure regions from {len(manifest)} pages of {pdf_name}")
        return manifest

    except Exception as e:
        print(f"  Error extracting figures from {pdf_name}: {e}")
        return {}


def _save_manifest(pdf_name: str, manifest: Dict[int, List[str]]) -> None:
    """Save the page-to-images manifest as JSON."""
    manifest_path = get_manifest_path(pdf_name)
    serializable = {str(k): v for k, v in manifest.items()}
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2)


def load_manifest(pdf_name: str) -> Dict[int, List[str]]:
    """Load the image manifest for a PDF."""
    manifest_path = get_manifest_path(pdf_name)
    if not manifest_path.exists():
        return {}

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {int(k): v for k, v in data.items()}
    except Exception as e:
        print(f"Warning: Could not load manifest for {pdf_name}: {e}")
        return {}


def get_images_for_page(pdf_name: str, page_number: int) -> List[str]:
    """Get image URLs for a specific page of a PDF."""
    manifest = load_manifest(pdf_name)
    image_files = manifest.get(page_number, [])

    pdf_stem = Path(pdf_name).stem
    return [
        f"/api/images/{pdf_stem}/{filename}"
        for filename in image_files
    ]


def get_images_for_sources(sources: list) -> list:
    """
    Enrich source documents with image URLs based on their page metadata.

    For each source that has a 'source' (PDF name) and 'page' field,
    looks up the manifest and adds matching image URLs.
    """
    manifest_cache: Dict[str, Dict[int, List[str]]] = {}

    for source in sources:
        pdf_name = source.get("source", "")
        page = source.get("page")

        if not pdf_name or page is None:
            source["images"] = []
            continue

        if pdf_name not in manifest_cache:
            manifest_cache[pdf_name] = load_manifest(pdf_name)

        manifest = manifest_cache[pdf_name]
        image_files = manifest.get(int(page), [])

        pdf_stem = Path(pdf_name).stem
        source["images"] = [
            f"/api/images/{pdf_stem}/{filename}"
            for filename in image_files
        ]

    return sources
