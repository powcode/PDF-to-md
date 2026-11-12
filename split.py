import io
import fitz

def parse_page_ranges(range_str: str, total_pages: int) -> tuple[list[int] | None, str | None]:
    if not range_str or not range_str.strip():
        return None, "Rentang halaman tidak boleh kosong."

    chosen_pages = set()
    parts = [p.strip() for p in range_str.split(",") if p.strip()]
    if not parts:
        return None, "Rentang halaman tidak valid."

    for part in parts:
        if "-" in part:
            subparts = [s.strip() for s in part.split("-")]
            if len(subparts) != 2:
                return None, f"Format rentang '{part}' tidak valid."
            start_str, end_str = subparts
            if not start_str.isdigit() or not end_str.isdigit():
                return None, f"Rentang '{part}' harus berupa angka numerik."
            start = int(start_str)
            end = int(end_str)
            if start < 1:
                return None, f"Halaman awal {start} tidak boleh kurang dari 1."
            if end > total_pages:
                return None, f"Halaman akhir {end} melebihi jumlah halaman dokumen ({total_pages})."
            if start > end:
                return None, f"Halaman awal {start} lebih besar dari halaman akhir {end} pada rentang '{part}'."
            for p in range(start, end + 1):
                chosen_pages.add(p - 1)  # 0-indexed
        else:
            if not part.isdigit():
                return None, f"Halaman '{part}' harus berupa angka numerik."
            page = int(part)
            if page < 1:
                return None, f"Halaman {page} tidak boleh kurang dari 1."
            if page > total_pages:
                return None, f"Halaman {page} melebihi jumlah halaman dokumen ({total_pages})."
            chosen_pages.add(page - 1)

    sorted_pages = sorted(list(chosen_pages))
    if not sorted_pages:
        return None, "Tidak ada halaman yang dipilih."
    return sorted_pages, None

def split_pdf_doc(doc: fitz.Document, sorted_page_indices: list[int]) -> bytes:
    new_doc = fitz.open()
    for pno in sorted_page_indices:
        new_doc.insert_pdf(doc, from_page=pno, to_page=pno)
    out_bytes = new_doc.tobytes()
    new_doc.close()
    return out_bytes
