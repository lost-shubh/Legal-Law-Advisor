from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


DATE_RE = re.compile(
    r"\b(?:\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|"
    r"\d{1,2}(?:st|nd|rd|th)?(?:\s+of)?\s+[A-Za-z]{3,9}\s+\d{2,4})\b",
    re.IGNORECASE,
)

ISSUE_KEYWORDS: dict[str, list[str]] = {
    "CRIMINAL": ["fir", "police", "arrest", "bail", "accused", "complaint", "charge"],
    "MURDER_CHARGE": [
        "murder",
        "killed",
        "dead",
        "death",
        "no sign of life",
        "found to be dead",
        "section 103",
    ],
    "PRIVATE_DEFENCE": [
        "private defence",
        "self defence",
        "self-defense",
        "protect me",
        "protect my family",
        "protect",
        "intruder",
        "attacked me",
        "attacked him",
    ],
    "NIGHT_HOUSE_BREAKING": [
        "broke into",
        "break into",
        "house-breaking",
        "house breaking",
        "intruder",
        "back entrance",
        "locker",
        "safe",
        "12 am",
        "midnight",
    ],
    "CULPABLE_HOMICIDE": ["culpable homicide", "unconscious", "wooden stick", "stick", "death"],
    "CHEQUE_BOUNCE": ["cheque", "138", "dishonour", "notice", "bank"],
    "FAMILY": ["divorce", "maintenance", "custody", "wife", "husband", "matrimonial"],
    "DOMESTIC_VIOLENCE": ["domestic violence", "dv act", "protection order"],
    "PROPERTY": ["property", "possession", "sale deed", "tenant", "land", "title"],
    "CYBER": ["cyber", "upi", "otp", "fraud", "online", "account hacked"],
    "CONSUMER": ["consumer", "defect", "refund", "warranty", "service deficiency"],
    "LABOUR": ["salary", "termination", "employer", "employee", "wages"],
}

EVIDENCE_KEYWORDS: dict[str, list[str]] = {
    "identity_documents": ["aadhaar", "pan", "passport", "id proof"],
    "police_records": ["fir", "complaint", "charge sheet", "closure report"],
    "financial_records": ["bank statement", "transaction", "cheque", "receipt", "invoice"],
    "digital_evidence": [
        "whatsapp",
        "email",
        "sms",
        "call recording",
        "screenshot",
        "upi",
        "cctv",
        "camera",
        "video",
        "dvr",
    ],
    "medical_forensic_records": [
        "injury",
        "injuries",
        "medical",
        "postmortem",
        "post-mortem",
        "dead",
        "death",
    ],
    "crime_scene_material": ["wooden stick", "stick", "locker", "safe", "blood", "clothes"],
    "property_documents": ["sale deed", "lease", "rent agreement", "mutation", "registry"],
    "court_documents": ["notice", "summons", "petition", "order", "judgment"],
}

MISSING_DOCS_BY_ISSUE: dict[str, list[str]] = {
    "CRIMINAL": ["FIR/complaint copy", "notice/summons", "bail/order history", "witness list"],
    "CHEQUE_BOUNCE": ["dishonoured cheque copy", "bank return memo", "legal notice", "postal proof"],
    "FAMILY": ["marriage proof", "income proof", "residence proof", "prior case/order copies"],
    "DOMESTIC_VIOLENCE": [
        "incident chronology",
        "medical records if any",
        "messages/call records",
        "residence proof",
    ],
    "PROPERTY": ["title documents", "possession proof", "tax/utility records", "prior notices"],
    "CYBER": ["transaction IDs", "screenshots", "bank complaint", "cyber complaint acknowledgement"],
    "CONSUMER": ["invoice", "warranty", "complaint emails", "service/job sheet"],
    "LABOUR": ["appointment letter", "salary slips", "termination notice", "emails/chats"],
    "MURDER_CHARGE": [
        "FIR and arrest memo",
        "remand order",
        "postmortem report",
        "injury/MLC records for you and family members",
        "CCTV/DVR seizure memo",
        "site plan and forensic report",
    ],
    "PRIVATE_DEFENCE": [
        "original CCTV/DVR with hash or seizure memo",
        "photos of broken entry/locker/safe",
        "medical records showing your injuries",
        "witness statements from family/neighbours",
        "seizure memo for wooden stick/clothes",
    ],
    "NIGHT_HOUSE_BREAKING": [
        "CCTV footage showing entry time",
        "photos of broken door/entrance/locker",
        "property-loss list",
        "scene inspection memo",
    ],
}


@dataclass(frozen=True)
class CaseAnalysis:
    issue_tags: list[str]
    dates_found: list[str]
    evidence_found: dict[str, list[str]]
    missing_documents: list[str]
    summary: str
    confidence: float
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_tags": self.issue_tags,
            "dates_found": self.dates_found,
            "evidence_found": self.evidence_found,
            "missing_documents": self.missing_documents,
            "summary": self.summary,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }


def _contains_any(text: str, keywords: list[str]) -> list[str]:
    lowered = text.lower()
    return [keyword for keyword in keywords if keyword in lowered]


def analyze_case_text(case_text: str) -> CaseAnalysis:
    clean = re.sub(r"\s+", " ", case_text).strip()
    issue_tags: list[str] = []
    for issue, keywords in ISSUE_KEYWORDS.items():
        if _contains_any(clean, keywords):
            issue_tags.append(issue)

    evidence_found: dict[str, list[str]] = {}
    for evidence_type, keywords in EVIDENCE_KEYWORDS.items():
        matches = _contains_any(clean, keywords)
        if matches:
            evidence_found[evidence_type] = matches

    missing: list[str] = []
    for issue in issue_tags:
        missing.extend(MISSING_DOCS_BY_ISSUE.get(issue, []))
    missing = sorted(set(missing))

    dates = sorted(set(DATE_RE.findall(clean)))
    warnings: list[str] = []
    urgent_terms = _contains_any(
        clean,
        ["arrest", "threat", "violence", "suicide", "deadline", "murder", "dead", "death"],
    )
    if urgent_terms:
        warnings.append(
            "Urgent-risk terms detected. The user should contact an advocate/legal aid or emergency authority immediately where appropriate."
        )
    if "MURDER_CHARGE" in issue_tags and "PRIVATE_DEFENCE" in issue_tags:
        warnings.append(
            "Murder/private-defence fact pattern detected. Preserve CCTV, medical records, seizure memos and get criminal defence counsel or legal aid immediately."
        )
    if len(clean.split()) < 80:
        warnings.append("Case text is short. More facts and documents are needed for reliable analysis.")

    summary = clean[:500] + ("..." if len(clean) > 500 else "")
    confidence = min(
        0.2 + (0.12 * len(issue_tags)) + (0.08 * len(evidence_found)) + (0.03 * len(dates)),
        0.85,
    )
    return CaseAnalysis(
        issue_tags=issue_tags or ["UNKNOWN"],
        dates_found=dates,
        evidence_found=evidence_found,
        missing_documents=missing,
        summary=summary,
        confidence=round(confidence, 3),
        warnings=warnings,
    )


def build_case_llm_prompt(case_text: str, analysis: CaseAnalysis, retrieved_context: str) -> str:
    return f"""
Analyze this Indian legal case intake using only the case text and retrieved legal context.

Return a concise lawyer-ready intake note with:
1. probable legal domain
2. key facts
3. evidence already mentioned
4. missing documents
5. similar legal material from retrieved context
6. next safe steps

Do not give final legal advice. Say that an advocate must verify before action.

PRELIMINARY ANALYSIS:
{analysis.to_dict()}

CASE TEXT:
{case_text[:5000]}

RETRIEVED CONTEXT:
{retrieved_context[:7000]}
""".strip()
