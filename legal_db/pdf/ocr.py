from __future__ import annotations

import re
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from statistics import mean


@dataclass(frozen=True)
class PdfTextResult:
    pdf_type: str
    raw_text: str
    clean_text: str
    page_count: int
    word_count: int
    extraction_method: str
    ocr_quality: float = 0.0
    ocr_confidence: float = 0.0
    page_spans: tuple[dict[str, int], ...] = ()


def page_spans(text: str, page_count: int) -> tuple[dict[str, int], ...]:
    """Return deterministic character ranges for page-separated extracted text."""
    if page_count <= 0:
        return ()
    pages = text.split("\n\n")
    proportional = len(pages) != page_count
    if proportional:
        # Some extractors collapse page boundaries; retain a useful proportional map.
        pages = [text] if page_count == 1 else [text[start:end] for start, end in _proportional_ranges(text, page_count)]
    spans: list[dict[str, int]] = []
    cursor = 0
    for number, value in enumerate(pages, start=1):
        if proportional:
            start, end = _proportional_ranges(text, page_count)[number - 1]
        else:
            start = text.find(value, cursor) if value else cursor
            start = max(start, cursor)
            end = min(start + len(value), len(text))
        spans.append({"page": number, "character_start": start, "character_end": end})
        cursor = end + 2
    return tuple(spans)


def _proportional_ranges(text: str, count: int) -> list[tuple[int, int]]:
    length = len(text)
    return [(round(length * i / count), round(length * (i + 1) / count)) for i in range(count)]


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


def _available_ocr_language(requested: str) -> str:
    """Use the requested language packs, falling back safely when unavailable."""
    try:
        import pytesseract

        available = set(pytesseract.get_languages(config=""))
    except Exception:
        return "eng"
    requested_parts = [part for part in requested.split("+") if part]
    if requested_parts and all(part in available for part in requested_parts):
        return "+".join(requested_parts)
    return "eng" if "eng" in available else (next(iter(available), "eng"))


def _preprocess_page(image):
    """Improve scanned legal pages using only the project's existing Pillow dependency."""
    from PIL import ImageFilter, ImageOps

    gray = ImageOps.grayscale(image)
    return ImageOps.autocontrast(gray).filter(ImageFilter.MedianFilter(size=3))


def _ocr_page(image, language: str) -> tuple[str, float]:
    import pytesseract

    data = pytesseract.image_to_data(
        _preprocess_page(image),
        lang=language,
        config="--oem 3 --psm 6",
        output_type=pytesseract.Output.DICT,
    )
    words: list[str] = []
    confidences: list[float] = []
    for value, raw_conf in zip(data.get("text", []), data.get("conf", [])):
        value = (value or "").strip()
        if value:
            words.append(value)
        try:
            confidence = float(raw_conf)
        except (TypeError, ValueError):
            continue
        if confidence >= 0:
            confidences.append(confidence / 100.0)
    return " ".join(words), round(mean(confidences), 3) if confidences else 0.0


def _ocr_pdf_details(path: Path, lang: str = "eng+hin", dpi: int = 300) -> tuple[str, int, float]:
    import fitz
    from PIL import Image

    language = _available_ocr_language(lang)
    text_parts: list[str] = []
    confidences: list[float] = []
    with fitz.open(path) as doc:
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), alpha=False)
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text, confidence = _ocr_page(image, language)
            text_parts.append(text)
            if confidence:
                confidences.append(confidence)
        return "\n\n".join(text_parts), doc.page_count, round(mean(confidences), 3) if confidences else 0.0


def ocr_pdf(path: Path, lang: str = "eng+hin", dpi: int = 300) -> tuple[str, int]:
    """Backward-compatible OCR API; confidence is retained by extract_pdf_text."""
    text, page_count, _ = _ocr_pdf_details(path, lang=lang, dpi=dpi)
    return text, page_count


def _hybrid_pdf_details(path: Path, lang: str = "eng+hin", dpi: int = 300) -> tuple[str, int, float]:
    """Keep reliable native pages and OCR only pages with weak/no text."""
    import fitz
    from PIL import Image

    language = _available_ocr_language(lang)
    parts: list[str] = []
    confidences: list[float] = []
    with fitz.open(path) as doc:
        for page in doc:
            native = page.get_text("text") or ""
            if len(native.split()) >= 35 and estimate_text_quality(native, 1) >= 0.55:
                parts.append(native)
                continue
            pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), alpha=False)
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text, confidence = _ocr_page(image, language)
            parts.append(text if text else native)
            if confidence:
                confidences.append(confidence)
        return "\n\n".join(parts), doc.page_count, round(mean(confidences), 3) if confidences else 0.0


def extract_pdf_text(path: str | Path, lang: str = "eng+hin") -> PdfTextResult:
    pdf_path = Path(path)
    pdf_type = classify_pdf(pdf_path)
    ocr_confidence = 0.0
    if pdf_type == "TEXT_PDF":
        raw_text, page_count = extract_text_pdf(pdf_path)
        method = "PDF_TEXT"
    elif pdf_type == "MIXED_PDF":
        raw_text, page_count, ocr_confidence = _hybrid_pdf_details(pdf_path, lang=lang)
        method = "MIXED" if ocr_confidence == 0.0 else "MIXED_OCR"
    else:
        raw_text, page_count, ocr_confidence = _ocr_pdf_details(pdf_path, lang=lang)
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
        ocr_confidence=ocr_confidence,
        page_spans=page_spans(raw_text, page_count),
    )

