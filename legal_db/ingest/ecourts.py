from __future__ import annotations

import re


CNR_RE = re.compile(r"^[A-Z]{4}\d{12}$")


def is_valid_cnr(cnr: str) -> bool:
    return bool(CNR_RE.match(cnr.strip().upper()))


def normalize_cnr(cnr: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]", "", cnr).upper()
    if not is_valid_cnr(cleaned):
        raise ValueError("CNR must look like four letters followed by twelve digits")
    return cleaned


def ecourts_collection_note() -> str:
    return (
        "Use official eCourts pages and permitted endpoints only. Do not bypass CAPTCHA, "
        "authentication, rate limits, or court portal access controls. District court public "
        "data usually contains metadata, orders, and judgments, not pleadings or evidence files."
    )

