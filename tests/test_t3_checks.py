import io
import fitz
import pytest
import config
from pdf_checks import (
    check_pdf_signature,
    check_pdf_size,
    check_pdf_pages,
    check_powerpoint_origin,
    check_text_layer,
    validate_pdf,
)

def test_signature_check():
    assert check_pdf_signature(b"NOT_A_PDF") is not None
    assert check_pdf_signature(b"%PDF-1.4 sample") is None

def test_size_check():
    large_bytes = b"x" * (config.MAX_CONTENT_LENGTH + 1)
    assert check_pdf_size(large_bytes) is not None
    assert check_pdf_size(b"small") is None

def test_pages_check():
    doc = fitz.open()
    for _ in range(35):
        doc.new_page()
    assert check_pdf_pages(doc) is not None
    doc.close()

def test_powerpoint_origin_check():
    doc = fitz.open()
    doc.new_page()
    doc.set_metadata({"producer": "iLovePDF", "creator": "Adobe InDesign"})
    assert check_powerpoint_origin(doc) is not None

    doc.set_metadata({"producer": "Microsoft: PowerPoint", "creator": "PowerPoint"})
    assert check_powerpoint_origin(doc) is None
    doc.close()

def test_text_layer_check():
    doc = fitz.open()
    doc.new_page()  # Blank page without text
    assert check_text_layer(doc) is not None

    page = doc[0]
    page.insert_text((50, 50), "Hello text layer")
    assert check_text_layer(doc) is None
    doc.close()
