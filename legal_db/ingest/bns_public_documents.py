from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


DEFAULT_OUTPUT_DIR = Path("data/raw/bns_public")
USER_AGENT = (
    "Legal-Law-Advisor/0.1 (+local public legal corpus; contact: local-user)"
)


@dataclass(frozen=True)
class PublicBnsDocument:
    title: str
    url: str
    filename: str
    source: str
    document_type: str
    material_type: str = "OTHER"
    subject_tags: tuple[str, ...] = (
        "BNS",
        "CRIMINAL_LAW",
        "NEW_CRIMINAL_LAWS",
        "OFFICIAL_PUBLIC",
    )


PUBLIC_BNS_DOCUMENTS: tuple[PublicBnsDocument, ...] = (
    PublicBnsDocument(
        title="The Bharatiya Nyaya Sanhita, 2023",
        url="https://www.mha.gov.in/sites/default/files/2024-04/250883_english_01042024.pdf",
        filename="mha_bharatiya_nyaya_sanhita_2023.pdf",
        source="Ministry of Home Affairs",
        document_type="ACT_PDF",
    ),
    PublicBnsDocument(
        title="NCRB Sankalan BNS Index",
        url="https://www.ncrb.gov.in/uploads/SankalanPortal/IndexBNS.html",
        filename="ncrb_sankalan_bns_index.html",
        source="National Crime Records Bureau",
        document_type="HTML_PAGE",
        material_type="GUIDE",
    ),
    PublicBnsDocument(
        title="NCRB Sankalan BNS to IPC Corresponding Section Table",
        url="https://www.ncrb.gov.in/uploads/SankalanPortal/SectionTableBNS.html",
        filename="ncrb_sankalan_bns_ipc_corresponding_section_table.html",
        source="National Crime Records Bureau",
        document_type="HTML_PAGE",
        material_type="GUIDE",
    ),
    PublicBnsDocument(
        title="NCRB Sankalan BNS Chapters and Sections",
        url="https://www.ncrb.gov.in/uploads/SankalanPortal/ChaptersBNS.html",
        filename="ncrb_sankalan_bns_chapters_and_sections.html",
        source="National Crime Records Bureau",
        document_type="HTML_PAGE",
        material_type="GUIDE",
    ),
)


@dataclass
class BnsPublicDownloadSummary:
    dry_run: bool
    output_dir: str
    documents: list[dict[str, Any]] = field(default_factory=list)
    failed: list[dict[str, Any]] = field(default_factory=list)
    manifest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "dry_run": self.dry_run,
            "output_dir": self.output_dir,
            "documents": self.documents,
            "failed": self.failed,
            "manifest_path": self.manifest_path,
            "downloaded": len([item for item in self.documents if item.get("status") == "downloaded"]),
            "existing": len([item for item in self.documents if item.get("status") == "existing"]),
        }


def content_type_for_filename(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return "application/pdf"
    if suffix in {".html", ".htm"}:
        return "text/html"
    return "application/octet-stream"


def build_manifest_entry(
    document: PublicBnsDocument,
    *,
    path: Path,
    status: str,
    byte_size: int | None = None,
    content_type: str | None = None,
    status_code: int | None = None,
) -> dict[str, Any]:
    entry = asdict(document)
    entry.update(
        {
            "path": str(path),
            "content_type": (content_type or content_type_for_filename(document.filename)).split(";")[0],
            "byte_size": byte_size,
            "status_code": status_code,
            "status": status,
        }
    )
    return entry


def write_manifest(
    output_dir: Path,
    documents: list[dict[str, Any]],
    failed: list[dict[str, Any]],
) -> Path:
    manifest_path = output_dir / "manifest.json"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_code": "BNS_PUBLIC",
        "source_name": "Official Public BNS Documents",
        "documents": documents,
        "failed": failed,
    }
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return manifest_path


def download_public_bns_documents(
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    *,
    dry_run: bool = False,
    replace: bool = False,
    timeout: int = 60,
    session: requests.Session | None = None,
) -> BnsPublicDownloadSummary:
    root = Path(output_dir)
    summary = BnsPublicDownloadSummary(dry_run=dry_run, output_dir=str(root))
    if dry_run:
        for document in PUBLIC_BNS_DOCUMENTS:
            summary.documents.append(
                build_manifest_entry(document, path=root / document.filename, status="planned")
            )
        return summary

    root.mkdir(parents=True, exist_ok=True)
    client = session or requests.Session()
    headers = {"User-Agent": USER_AGENT}

    for document in PUBLIC_BNS_DOCUMENTS:
        path = root / Path(document.filename).name
        if path.exists() and not replace:
            summary.documents.append(
                build_manifest_entry(
                    document,
                    path=path,
                    status="existing",
                    byte_size=path.stat().st_size,
                )
            )
            continue
        try:
            response = client.get(document.url, headers=headers, timeout=timeout)
            status_code = int(response.status_code)
            if status_code >= 400:
                summary.failed.append(
                    {"title": document.title, "url": document.url, "status_code": status_code}
                )
                continue
            content = response.content
            if not content:
                summary.failed.append({"title": document.title, "url": document.url, "error": "empty"})
                continue
            path.write_bytes(content)
            summary.documents.append(
                build_manifest_entry(
                    document,
                    path=path,
                    status="downloaded",
                    byte_size=len(content),
                    content_type=response.headers.get("Content-Type"),
                    status_code=status_code,
                )
            )
        except requests.RequestException as exc:
            summary.failed.append({"title": document.title, "url": document.url, "error": str(exc)})

    summary.manifest_path = str(write_manifest(root, summary.documents, summary.failed))
    return summary
