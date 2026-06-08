from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


DEFAULT_OUTPUT_DIR = Path("data/raw/new_criminal_laws_public")
USER_AGENT = "Legal-Law-Advisor/0.1 (+local official public legal corpus)"


@dataclass(frozen=True)
class PublicLegalDocument:
    title: str
    url: str
    filename: str
    source: str
    document_type: str
    law_tag: str
    material_type: str = "OTHER"
    subject_tags: tuple[str, ...] = (
        "CRIMINAL_LAW",
        "NEW_CRIMINAL_LAWS",
        "OFFICIAL_PUBLIC",
    )

    def all_subject_tags(self) -> tuple[str, ...]:
        tags = {*self.subject_tags, self.law_tag}
        if "Gazette" in self.title or "Notification" in self.title:
            tags.add("GAZETTE")
        return tuple(sorted(tags))


PUBLIC_NEW_CRIMINAL_LAW_DOCUMENTS: tuple[PublicLegalDocument, ...] = (
    PublicLegalDocument(
        title="MHA - The Bharatiya Nyaya Sanhita, 2023",
        url="https://www.mha.gov.in/sites/default/files/2024-04/250883_english_01042024.pdf",
        filename="mha_bharatiya_nyaya_sanhita_2023.pdf",
        source="Ministry of Home Affairs",
        document_type="ACT_PDF",
        law_tag="BNS",
    ),
    PublicLegalDocument(
        title="MHA - The Bharatiya Sakshya Adhiniyam, 2023",
        url="https://www.mha.gov.in/sites/default/files/2024-04/250882_english_01042024_0.pdf",
        filename="mha_bharatiya_sakshya_adhiniyam_2023.pdf",
        source="Ministry of Home Affairs",
        document_type="ACT_PDF",
        law_tag="BSA",
    ),
    PublicLegalDocument(
        title="MHA - The Bharatiya Nagarik Suraksha Sanhita, 2023",
        url="https://www.mha.gov.in/sites/default/files/2024-04/250884_2_english_01042024.pdf",
        filename="mha_bharatiya_nagarik_suraksha_sanhita_2023.pdf",
        source="Ministry of Home Affairs",
        document_type="ACT_PDF",
        law_tag="BNSS",
    ),
    PublicLegalDocument(
        title="NCRB Sankalan - BNS Complete PDF",
        url="https://www.ncrb.gov.in/uploads/SankalanPortal/DownloadPDF/BNS2023.pdf",
        filename="ncrb_sankalan_bns_2023.pdf",
        source="National Crime Records Bureau",
        document_type="MANUAL_PDF",
        law_tag="BNS",
        material_type="GUIDE",
    ),
    PublicLegalDocument(
        title="NCRB Sankalan - BNS Index",
        url="https://www.ncrb.gov.in/uploads/SankalanPortal/IndexBNS.html",
        filename="ncrb_sankalan_bns_index.html",
        source="National Crime Records Bureau",
        document_type="HTML_PAGE",
        law_tag="BNS",
        material_type="GUIDE",
    ),
    PublicLegalDocument(
        title="NCRB Sankalan - BNS to IPC Corresponding Section Table",
        url="https://www.ncrb.gov.in/uploads/SankalanPortal/SectionTableBNS.html",
        filename="ncrb_sankalan_bns_ipc_corresponding_section_table.html",
        source="National Crime Records Bureau",
        document_type="HTML_PAGE",
        law_tag="BNS",
        material_type="GUIDE",
    ),
    PublicLegalDocument(
        title="NCRB Sankalan - BNS Chapters and Sections",
        url="https://www.ncrb.gov.in/uploads/SankalanPortal/ChaptersBNS.html",
        filename="ncrb_sankalan_bns_chapters_and_sections.html",
        source="National Crime Records Bureau",
        document_type="HTML_PAGE",
        law_tag="BNS",
        material_type="GUIDE",
    ),
    PublicLegalDocument(
        title="NCRB Sankalan - Gazette BNS 2023",
        url="https://www.ncrb.gov.in/uploads/SankalanPortal/DownloadPDF/GazetteBNS2023.pdf",
        filename="ncrb_gazette_bns_2023.pdf",
        source="National Crime Records Bureau",
        document_type="GAZETTE_PDF",
        law_tag="BNS",
    ),
    PublicLegalDocument(
        title="NCRB Sankalan - BNSS Complete PDF",
        url="https://www.ncrb.gov.in/uploads/SankalanPortal/DownloadPDF/BNSS2023.pdf",
        filename="ncrb_sankalan_bnss_2023.pdf",
        source="National Crime Records Bureau",
        document_type="MANUAL_PDF",
        law_tag="BNSS",
        material_type="GUIDE",
    ),
    PublicLegalDocument(
        title="NCRB Sankalan - BNSS Index",
        url="https://www.ncrb.gov.in/uploads/SankalanPortal/IndexBNSS.html",
        filename="ncrb_sankalan_bnss_index.html",
        source="National Crime Records Bureau",
        document_type="HTML_PAGE",
        law_tag="BNSS",
        material_type="GUIDE",
    ),
    PublicLegalDocument(
        title="NCRB Sankalan - BNSS to CrPC Corresponding Section Table",
        url="https://www.ncrb.gov.in/uploads/SankalanPortal/SectionTableBNSS.html",
        filename="ncrb_sankalan_bnss_crpc_corresponding_section_table.html",
        source="National Crime Records Bureau",
        document_type="HTML_PAGE",
        law_tag="BNSS",
        material_type="GUIDE",
    ),
    PublicLegalDocument(
        title="NCRB Sankalan - BNSS Chapters and Sections",
        url="https://www.ncrb.gov.in/uploads/SankalanPortal/ChaptersBNSS.html",
        filename="ncrb_sankalan_bnss_chapters_and_sections.html",
        source="National Crime Records Bureau",
        document_type="HTML_PAGE",
        law_tag="BNSS",
        material_type="GUIDE",
    ),
    PublicLegalDocument(
        title="NCRB Sankalan - BNSS Schedule",
        url="https://www.ncrb.gov.in/uploads/SankalanPortal/ScheduleBNSS.html",
        filename="ncrb_sankalan_bnss_schedule.html",
        source="National Crime Records Bureau",
        document_type="HTML_PAGE",
        law_tag="BNSS",
        material_type="GUIDE",
    ),
    PublicLegalDocument(
        title="NCRB Sankalan - Gazette BNSS 2023",
        url="https://www.ncrb.gov.in/uploads/SankalanPortal/DownloadPDF/GazetteBNSS2023.pdf",
        filename="ncrb_gazette_bnss_2023.pdf",
        source="National Crime Records Bureau",
        document_type="GAZETTE_PDF",
        law_tag="BNSS",
    ),
    PublicLegalDocument(
        title="NCRB Sankalan - BSA Complete PDF",
        url="https://www.ncrb.gov.in/uploads/SankalanPortal/DownloadPDF/BSA2023.pdf",
        filename="ncrb_sankalan_bsa_2023.pdf",
        source="National Crime Records Bureau",
        document_type="MANUAL_PDF",
        law_tag="BSA",
        material_type="GUIDE",
    ),
    PublicLegalDocument(
        title="NCRB Sankalan - BSA Index",
        url="https://www.ncrb.gov.in/uploads/SankalanPortal/IndexBSA.html",
        filename="ncrb_sankalan_bsa_index.html",
        source="National Crime Records Bureau",
        document_type="HTML_PAGE",
        law_tag="BSA",
        material_type="GUIDE",
    ),
    PublicLegalDocument(
        title="NCRB Sankalan - BSA to Indian Evidence Act Corresponding Section Table",
        url="https://www.ncrb.gov.in/uploads/SankalanPortal/SectionTableBSA.html",
        filename="ncrb_sankalan_bsa_evidence_act_corresponding_section_table.html",
        source="National Crime Records Bureau",
        document_type="HTML_PAGE",
        law_tag="BSA",
        material_type="GUIDE",
    ),
    PublicLegalDocument(
        title="NCRB Sankalan - BSA Chapters and Sections",
        url="https://www.ncrb.gov.in/uploads/SankalanPortal/ChaptersBSA.html",
        filename="ncrb_sankalan_bsa_chapters_and_sections.html",
        source="National Crime Records Bureau",
        document_type="HTML_PAGE",
        law_tag="BSA",
        material_type="GUIDE",
    ),
    PublicLegalDocument(
        title="NCRB Sankalan - BSA Schedule",
        url="https://www.ncrb.gov.in/uploads/SankalanPortal/ScheduleBSA.html",
        filename="ncrb_sankalan_bsa_schedule.html",
        source="National Crime Records Bureau",
        document_type="HTML_PAGE",
        law_tag="BSA",
        material_type="GUIDE",
    ),
    PublicLegalDocument(
        title="NCRB Sankalan - Gazette BSA 2023",
        url="https://www.ncrb.gov.in/uploads/SankalanPortal/DownloadPDF/GazetteBSA2023.pdf",
        filename="ncrb_gazette_bsa_2023.pdf",
        source="National Crime Records Bureau",
        document_type="GAZETTE_PDF",
        law_tag="BSA",
    ),
    PublicLegalDocument(
        title="NCRB Sankalan - Gazette Notifications of BNS, BNSS and BSA",
        url="https://www.ncrb.gov.in/uploads/SankalanPortal/DownloadPDF/GazetteNotificationOfBNS%2CBNSS%2CBSA.pdf",
        filename="ncrb_gazette_notifications_bns_bnss_bsa.pdf",
        source="National Crime Records Bureau",
        document_type="GAZETTE_PDF",
        law_tag="NEW_CRIMINAL_LAWS",
    ),
)


@dataclass
class PublicDocumentDownloadSummary:
    dry_run: bool
    output_dir: str
    source_code: str
    source_name: str
    documents: list[dict[str, Any]] = field(default_factory=list)
    failed: list[dict[str, Any]] = field(default_factory=list)
    manifest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "dry_run": self.dry_run,
            "output_dir": self.output_dir,
            "source_code": self.source_code,
            "source_name": self.source_name,
            "documents": self.documents,
            "failed": self.failed,
            "manifest_path": self.manifest_path,
            "downloaded": len([item for item in self.documents if item.get("status") == "downloaded"]),
            "existing": len([item for item in self.documents if item.get("status") == "existing"]),
            "planned": len([item for item in self.documents if item.get("status") == "planned"]),
        }


def content_type_for_filename(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return "application/pdf"
    if suffix in {".html", ".htm"}:
        return "text/html"
    return "application/octet-stream"


def build_manifest_entry(
    document: PublicLegalDocument,
    *,
    path: Path,
    status: str,
    byte_size: int | None = None,
    content_type: str | None = None,
    status_code: int | None = None,
) -> dict[str, Any]:
    entry = asdict(document)
    entry["subject_tags"] = list(document.all_subject_tags())
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
    *,
    source_code: str,
    source_name: str,
) -> Path:
    manifest_path = output_dir / "manifest.json"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_code": source_code,
        "source_name": source_name,
        "documents": documents,
        "failed": failed,
    }
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return manifest_path


def download_public_new_criminal_law_documents(
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    *,
    dry_run: bool = False,
    replace: bool = False,
    timeout: int = 60,
    session: requests.Session | None = None,
    documents: tuple[PublicLegalDocument, ...] = PUBLIC_NEW_CRIMINAL_LAW_DOCUMENTS,
    source_code: str = "NEW_CRIMINAL_LAWS_PUBLIC",
    source_name: str = "Official Public New Criminal Laws Documents",
) -> PublicDocumentDownloadSummary:
    root = Path(output_dir)
    summary = PublicDocumentDownloadSummary(
        dry_run=dry_run,
        output_dir=str(root),
        source_code=source_code,
        source_name=source_name,
    )
    if dry_run:
        for document in documents:
            summary.documents.append(
                build_manifest_entry(document, path=root / document.filename, status="planned")
            )
        return summary

    root.mkdir(parents=True, exist_ok=True)
    client = session or requests.Session()
    headers = {"User-Agent": USER_AGENT}

    for document in documents:
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

    summary.manifest_path = str(
        write_manifest(
            root,
            summary.documents,
            summary.failed,
            source_code=source_code,
            source_name=source_name,
        )
    )
    return summary
