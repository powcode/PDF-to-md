import re
import fitz

def detect_footers(doc: fitz.Document) -> set[str]:
    # Text that repeats at similar position on at least 50% of slides, in bottom 8% of page.
    # Ignore digits when comparing, so slide numbers are removed.
    footer_candidates: dict[str, int] = {}
    total_pages = len(doc)
    if total_pages < 2:
        return set()

    for page in doc:
        page_height = page.rect.height
        bottom_threshold = page_height * 0.92  # bottom 8%
        blocks = page.get_text("dict", sort=True).get("blocks", [])
        page_patterns = set()

        for b in blocks:
            if b.get("type") == 0:  # text
                bbox = fitz.Rect(b["bbox"])
                if bbox.y0 >= bottom_threshold or bbox.y1 >= bottom_threshold:
                    # Extract text
                    raw_text = ""
                    for line in b.get("lines", []):
                        for span in line.get("spans", []):
                            raw_text += span.get("text", "")
                    raw_text = raw_text.strip()
                    # Pattern without digits
                    cleaned = re.sub(r"\d+", "", raw_text).strip().lower()
                    if cleaned:
                        page_patterns.add(cleaned)

        for pat in page_patterns:
            footer_candidates[pat] = footer_candidates.get(pat, 0) + 1

    common_footers = set()
    for pat, count in footer_candidates.items():
        if count >= (total_pages * 0.5):
            common_footers.add(pat)

    return common_footers

def table_to_markdown(tab) -> str:
    # tab is fitz.table.Table
    try:
        data = tab.extract()
    except Exception:
        return ""
    if not data or len(data) == 0:
        return ""

    def clean_cell(cell):
        if cell is None:
            return ""
        s = str(cell).replace("\n", " ").replace("\r", " ").replace("|", "\\|").strip()
        return s

    lines = []
    # Header row
    headers = [clean_cell(c) for c in data[0]]
    if not any(headers):
        headers = [f"Kolom {i+1}" for i in range(len(headers))]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    # Body rows
    for row in data[1:]:
        cells = [clean_cell(c) for c in row]
        # Pad cells if needed
        while len(cells) < len(headers):
            cells.append("")
        lines.append("| " + " | ".join(cells[:len(headers)]) + " |")

    return "\n".join(lines)

def extract_slide_markdown(
    page: fitz.Page,
    slide_num: int,
    page_figures: list[dict],
    figure_descriptions: list[str],
    global_figure_start_index: int,
    footer_patterns: set[str]
) -> tuple[str, int]:
    # Returns (slide_md, next_global_figure_index)
    page_height = page.rect.height
    bottom_threshold = page_height * 0.92

    # 1. Detect tables
    tables = []
    table_rects = []
    try:
        tab_finder = page.find_tables()
        if tab_finder and tab_finder.tables:
            for t in tab_finder.tables:
                tables.append({
                    "rect": fitz.Rect(t.bbox),
                    "md": table_to_markdown(t)
                })
                table_rects.append(fitz.Rect(t.bbox))
    except Exception:
        pass

    # 2. Collect content blocks (text, tables, figures)
    blocks = page.get_text("dict", sort=True).get("blocks", [])
    content_items = []

    # Filter out text inside tables, text inside figure areas (expanded by 5pt, unless caption),
    # and repeating footers
    from figures import CAPTION_PATTERN

    for b in blocks:
        if b.get("type") == 0:
            bbox = fitz.Rect(b["bbox"])
            raw_text = ""
            for line in b.get("lines", []):
                for span in line.get("spans", []):
                    raw_text += span.get("text", "") + " "
            raw_text = raw_text.strip()
            if not raw_text:
                continue

            # Check footer
            if bbox.y0 >= bottom_threshold or bbox.y1 >= bottom_threshold:
                cleaned = re.sub(r"\d+", "", raw_text).strip().lower()
                if cleaned in footer_patterns:
                    continue
                # Also if it's purely a slide number at the bottom
                if raw_text.isdigit():
                    continue

            # Check table overlap
            if any(bbox.intersects(tr) for tr in table_rects):
                continue

            # Check figure overlap (expanded rect)
            is_caption = bool(CAPTION_PATTERN.match(raw_text))
            in_figure = False
            if not is_caption:
                for fig in page_figures:
                    if bbox.intersects(fig["expanded_rect"]):
                        in_figure = True
                        break
            if in_figure:
                continue

            content_items.append({
                "type": "text",
                "y0": bbox.y0,
                "x0": bbox.x0,
                "content": raw_text
            })

    # Add tables as content items
    for t in tables:
        if t["md"]:
            content_items.append({
                "type": "table",
                "y0": t["rect"].y0,
                "x0": t["rect"].x0,
                "content": t["md"]
            })

    # Add figures as content items
    curr_fig_idx = global_figure_start_index
    for i, fig in enumerate(page_figures):
        curr_fig_idx += 1
        desc = figure_descriptions[i] if i < len(figure_descriptions) else "Deskripsi gambar."
        placeholder = f"> **Gambar {curr_fig_idx} (slide {slide_num}):** {desc}"
        content_items.append({
            "type": "figure",
            "y0": fig["rect"].y0,
            "x0": fig["rect"].x0,
            "content": placeholder
        })

    # Sort all content items by top edge, then left edge
    content_items.sort(key=lambda item: (round(item["y0"], 1), round(item["x0"], 1)))

    slide_lines = [f"## Slide {slide_num}", ""]
    for item in content_items:
        slide_lines.append(item["content"])
        slide_lines.append("")

    return "\n".join(slide_lines).strip(), curr_fig_idx
