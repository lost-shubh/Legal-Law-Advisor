from __future__ import annotations

import re
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path


@dataclass(frozen=True)
class PdfTextResult:
    pdf_type: str
    raw_text: str
    clean_text: str
    page_count: int
    word_count: int
    extraction_method: str
    ocr_quality: float = 0.0


def clean_ocr_text(text: str) -> str:
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[Ss]ec\.\s*([0-9A-Za-z-]+)", r"Section \1", text)
    text = re.sub(r"[Ss]ection\s+([0-9A-Za-z-]+)", r"Section \1", text)
    return text.strip()


def estimate_text_quality(clean_text: str, page_count: int) -> float:
    text = clean_text.strip()
    if not text:
        return 0.0
    total_chars = len(text)
    alnum_chars = sum(1 for char in text if char.isalnum())
    replacement_chars = text.count("\ufffd")
    words = text.split()
    words_per_page = len(words) / max(page_count, 1)
    alnum_ratio = alnum_chars / max(total_chars, 1)
    replacement_penalty = min(replacement_chars / max(total_chars, 1), 0.5)
    density_score = min(words_per_page / 250, 1.0)
    quality = (0.55 * alnum_ratio) + (0.35 * density_score) + 0.10
    return round(max(min(quality - replacement_penalty, 1.0), 0.0), 3)


def should_extract_for_ai(word_count: int, ocr_quality: float | None) -> tuple[bool, str | None]:
    if word_count < 100:
        return False, "TOO_SHORT"
    if ocr_quality is not None and ocr_quality < 0.6:
        return False, "OCR_QUALITY_TOO_LOW"
    return True, None


def classify_pdf(path: Path) -> str:
    if find_spec("pdfplumber") is not None:
        import pdfplumber

        with pdfplumber.open(path) as pdf:
            page_count = len(pdf.pages)
            total_chars = sum(len(page.extract_text() or "") for page in pdf.pages)
    else:
        raw_text, page_count = extract_text_pymupdf(path)
        total_chars = len(raw_text)
    chars_per_page = total_chars / max(page_count, 1)
    if chars_per_page > 100:
        return "TEXT_PDF"
    if chars_per_page > 20:
        return "MIXED_PDF"
    return "SCANNED_PDF"


def extract_text_pdf(path: Path) -> tuple[str, int]:
    if find_spec("pdfplumber") is None:
        return extract_text_pymupdf(path)

    import pdfplumber
    text_parts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text_parts.append(page.extract_text() or "")
        return "\n\n".join(text_parts), len(pdf.pages)


def extract_text_pymupdf(path: Path) -> tuple[str, int]:
    import fitz

    text_parts: list[str] = []
    with fitz.open(path) as doc:
        for page in doc:
            text_parts.append(page.get_text("text") or "")
        return "\n\n".join(text_parts), doc.page_count


def ocr_pdf(path: Path, lang: str = "eng+hin", dpi: int = 300) -> tuple[str, int]:
    import fitz
    import pytesseract
    from PIL import Image

    doc = fitz.open(path)
    text_parts: list[str] = []
    for page in doc:
        matrix = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=matrix)
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        text_parts.append(pytesseract.image_to_string(image, lang=lang, config="--psm 6 --oem 3"))
    return "\n\n".join(text_parts), doc.page_count


def extract_pdf_text(path: str | Path, lang: str = "eng+hin") -> PdfTextResult:
    pdf_path = Path(path)
    pdf_type = classify_pdf(pdf_path)
    if pdf_type == "TEXT_PDF":
        raw_text, page_count = extract_text_pdf(pdf_path)
        method = "PDF_TEXT"
    elif pdf_type == "MIXED_PDF":
        raw_text, page_count = extract_text_pdf(pdf_path)
        if len(raw_text.split()) < 100:
            raw_text, page_count = ocr_pdf(pdf_path, lang=lang)
            method = "OCR"
        else:
            method = "MIXED"
    else:
        raw_text, page_count = ocr_pdf(pdf_path, lang=lang)
        method = "OCR"
    clean_text = clean_ocr_text(raw_text)
    word_count = len(clean_text.split())
    ocr_quality = estimate_text_quality(clean_text, page_count)
    return PdfTextResult(
        pdf_type=pdf_type,
        raw_text=raw_text,
        clean_text=clean_text,
        page_count=page_count,
        word_count=word_count,
        extraction_method=method,
        ocr_quality=ocr_quality,
    )

