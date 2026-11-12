import fitz
import config

def check_pdf_signature(file_bytes: bytes) -> str | None:
    if not file_bytes.startswith(b"%PDF"):
        return "File harus berformat PDF yang valid dan diawali dengan %PDF."
    return None

def check_pdf_size(file_bytes: bytes) -> str | None:
    if len(file_bytes) > config.MAX_CONTENT_LENGTH:
        return f"Ukuran file melebihi batas {config.MAX_UPLOAD_MB} MB."
    return None

def check_pdf_pages(doc: fitz.Document) -> str | None:
    if len(doc) > config.MAX_PAGES:
        return f"Jumlah halaman ({len(doc)}) melebihi batas {config.MAX_PAGES} slide."
    if len(doc) == 0:
        return "Dokumen PDF kosong."
    return None

def check_powerpoint_origin(doc: fitz.Document) -> str | None:
    meta = doc.metadata or {}
    producer = (meta.get("producer") or "").lower()
    creator = (meta.get("creator") or "").lower()
    
    if "powerpoint" not in producer and "powerpoint" not in creator:
        return "File ini tidak terdeteksi berasal dari PowerPoint. Ekspor ulang dari PowerPoint lalu unggah lagi."
    return None

def check_text_layer(doc: fitz.Document) -> str | None:
    has_text = False
    for page in doc:
        text = page.get_text().strip()
        if text:
            has_text = True
            break
    if not has_text:
        return "PDF ini tampak hasil scan dan belum didukung."
    return None

def validate_pdf(
    file_bytes: bytes,
    check_limits: bool = True,
    require_text: bool = True
) -> tuple[fitz.Document | None, str | None]:
    sig_err = check_pdf_signature(file_bytes)
    if sig_err:
        return None, sig_err

    if check_limits:
        size_err = check_pdf_size(file_bytes)
        if size_err:
            return None, size_err

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception:
        return None, "Gagal membaca file PDF. Pastikan file tidak rusak."

    if check_limits:
        pages_err = check_pdf_pages(doc)
        if pages_err:
            doc.close()
            return None, pages_err
    else:
        if len(doc) == 0:
            doc.close()
            return None, "Dokumen PDF kosong."

    if getattr(config, "REQUIRE_POWERPOINT", False):
        ppt_err = check_powerpoint_origin(doc)
        if ppt_err:
            doc.close()
            return None, ppt_err

    if require_text:
        text_err = check_text_layer(doc)
        if text_err:
            doc.close()
            return None, text_err

    return doc, None
