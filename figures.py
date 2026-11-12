import re
import fitz
import config

CAPTION_PATTERN = re.compile(
    r"^(Gambar|Figure|Fig\.|Grafik|Diagram|Ilustrasi)\s*(\d+|:)",
    re.IGNORECASE
)

def rect_gap(r1: fitz.Rect, r2: fitz.Rect) -> float:
    # Gap between two rectangles (0 if overlapping/touching)
    dx = max(0.0, max(r1.x0, r2.x0) - min(r1.x1, r2.x1))
    dy = max(0.0, max(r1.y0, r2.y0) - min(r1.y1, r2.y1))
    return (dx * dx + dy * dy) ** 0.5

def cluster_drawings(drawings: list[dict], gap_limit: float = config.CLUSTER_GAP_PT) -> list[fitz.Rect]:
    rects = [d["rect"] for d in drawings if "rect" in d and not d["rect"].is_empty]
    if not rects:
        return []

    # Simple connected components / clustering
    clusters: list[list[fitz.Rect]] = []
    for r in rects:
        merged = False
        for c in clusters:
            if any(rect_gap(r, cr) <= gap_limit for cr in c):
                c.append(r)
                merged = True
                break
        if not merged:
            clusters.append([r])

    # Re-merge clusters that now bridge together
    changed = True
    while changed:
        changed = False
        new_clusters: list[list[fitz.Rect]] = []
        while clusters:
            c = clusters.pop(0)
            i = 0
            while i < len(clusters):
                c2 = clusters[i]
                if any(rect_gap(r1, r2) <= gap_limit for r1 in c for r2 in c2):
                    c.extend(c2)
                    clusters.pop(i)
                    changed = True
                else:
                    i += 1
            new_clusters.append(c)
        clusters = new_clusters

    valid_figures: list[fitz.Rect] = []
    for c in clusters:
        if len(c) >= config.MIN_DRAWING_ITEMS:
            bbox = fitz.Rect(c[0])
            for item in c[1:]:
                bbox.include_rect(item)
            if bbox.width >= config.MIN_FIGURE_SIZE_PT and bbox.height >= config.MIN_FIGURE_SIZE_PT:
                valid_figures.append(bbox)

    return valid_figures

def merge_overlapping_rects(rects: list[fitz.Rect]) -> list[fitz.Rect]:
    if not rects:
        return []
    
    merged: list[fitz.Rect] = []
    for r in rects:
        found = False
        for i, m in enumerate(merged):
            if r.intersects(m):
                merged[i] = m | r  # union
                found = True
                break
        if not found:
            merged.append(fitz.Rect(r))
    return merged

def detect_page_figures(page: fitz.Page, table_rects: list[fitz.Rect]) -> list[dict]:
    # 1. Raster figures from blocks
    blocks = page.get_text("dict", sort=True).get("blocks", [])
    raster_rects: list[fitz.Rect] = []
    for b in blocks:
        if b.get("type") == 1:  # image block
            r = fitz.Rect(b["bbox"])
            if r.width >= config.MIN_FIGURE_SIZE_PT and r.height >= config.MIN_FIGURE_SIZE_PT:
                # Check overlap with tables
                if not any(r.intersects(tr) for tr in table_rects):
                    raster_rects.append(r)

    # 2. Vector figures from drawings
    drawings = page.get_drawings()
    vector_rects = cluster_drawings(drawings)
    # Skip any vector cluster overlapping a table
    vector_rects = [r for r in vector_rects if not any(r.intersects(tr) for tr in table_rects)]

    # 3. Combine & merge overlapping raster + vector
    all_rects = merge_overlapping_rects(raster_rects + vector_rects)

    # Sort figures by top edge, then left edge
    all_rects.sort(key=lambda r: (round(r.y0, 1), round(r.x0, 1)))

    # Find captions and text blocks for context
    text_blocks = []
    for b in blocks:
        if b.get("type") == 0:  # text block
            full_text = ""
            for line in b.get("lines", []):
                line_text = "".join(span.get("text", "") for span in line.get("spans", []))
                full_text += line_text + " "
            full_text = full_text.strip()
            if full_text:
                text_blocks.append({
                    "bbox": fitz.Rect(b["bbox"]),
                    "text": full_text,
                    "is_caption": bool(CAPTION_PATTERN.match(full_text))
                })

    figure_items = []
    scale = config.RENDER_DPI / 72.0
    matrix = fitz.Matrix(scale, scale)

    for r in all_rects:
        # Find nearest caption
        caption = "none"
        nearest_cap_dist = float("inf")
        for tb in text_blocks:
            if tb["is_caption"]:
                d = rect_gap(r, tb["bbox"])
                if d < nearest_cap_dist:
                    nearest_cap_dist = d
                    caption = tb["text"]

        # Context = caption plus nearby text, at most CONTEXT_MAX_CHARS
        nearby_texts = []
        if caption != "none":
            nearby_texts.append(f"Caption: {caption}")
        for tb in text_blocks:
            if tb["text"] != caption and rect_gap(r, tb["bbox"]) <= 100:  # within 100 pt
                nearby_texts.append(tb["text"])
        
        context_str = "\n".join(nearby_texts)
        if len(context_str) > config.CONTEXT_MAX_CHARS:
            context_str = context_str[:config.CONTEXT_MAX_CHARS]

        # Render figure PNG
        pix = page.get_pixmap(matrix=matrix, clip=r)
        png_bytes = pix.tobytes(output="png")

        figure_items.append({
            "rect": r,
            "png_bytes": png_bytes,
            "caption": caption,
            "context": context_str,
            # Expanded by 5 pt for text filtering
            "expanded_rect": fitz.Rect(r.x0 - 5, r.y0 - 5, r.x1 + 5, r.y1 + 5)
        })

    return figure_items

def count_document_figures(doc: fitz.Document) -> tuple[int, list[list[dict]]]:
    import hashlib

    total_pages = len(doc)
    raw_doc_figures: list[list[dict]] = []
    pos_counts: dict[tuple, int] = {}
    hash_counts: dict[str, int] = {}

    for page in doc:
        try:
            tabs = page.find_tables()
            table_rects = [fitz.Rect(t.bbox) for t in tabs.tables] if tabs else []
        except Exception:
            table_rects = []
        page_figs = detect_page_figures(page, table_rects)
        raw_doc_figures.append(page_figs)

        for f in page_figs:
            r = f["rect"]
            pos_key = (round(r.x0 / 5) * 5, round(r.y0 / 5) * 5, round(r.width / 5) * 5, round(r.height / 5) * 5)
            pos_counts[pos_key] = pos_counts.get(pos_key, 0) + 1
            h_key = hashlib.md5(f["png_bytes"]).hexdigest()
            hash_counts[h_key] = hash_counts.get(h_key, 0) + 1

    repeat_threshold = max(3, int(total_pages * 0.25))

    doc_figures: list[list[dict]] = []
    total = 0

    for page_idx, (page, page_figs) in enumerate(zip(doc, raw_doc_figures)):
        p_width = page.rect.width
        p_height = page.rect.height
        page_area = p_width * p_height

        important_figs = []
        for f in page_figs:
            r = f["rect"]
            area = r.width * r.height
            pos_key = (round(r.x0 / 5) * 5, round(r.y0 / 5) * 5, round(r.width / 5) * 5, round(r.height / 5) * 5)
            h_key = hashlib.md5(f["png_bytes"]).hexdigest()
            has_caption = bool(f.get("caption") and f["caption"] != "none")

            # 1. Skip repeated template elements (logos, watermarks, header graphics)
            if (pos_counts.get(pos_key, 0) >= repeat_threshold or hash_counts.get(h_key, 0) >= repeat_threshold) and not has_caption:
                continue

            # 2. Skip full-slide cover backgrounds (> 70% of page area)
            if area >= (page_area * 0.70) and not has_caption:
                continue

            # 3. Skip tiny decorative icons, bullets, or thin divider lines (< 40 pt dimension or < 2000 pt^2 area)
            if (r.width < 40 or r.height < 40 or area < 2000) and not has_caption:
                continue

            important_figs.append(f)

        doc_figures.append(important_figs)
        total += len(important_figs)

    return total, doc_figures
