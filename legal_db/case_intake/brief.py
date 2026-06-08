from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from legal_db.case_intake.analyzer import CaseAnalysis
from legal_db.retrieval.staging import SearchResult


BRIEF_DISCLAIMER = (
    "Research aid only. This is not legal advice, and an advocate should verify the "
    "facts, limitation, current law and forum strategy before any action is taken."
)

RESEARCH_QUESTIONS_BY_ISSUE: dict[str, tuple[str, ...]] = {
    "CHEQUE_BOUNCE": (
        "Are the cheque dishonour, demand notice and complaint filing timelines satisfied?",
        "Do the cheque, return memo and notice-service records prove the statutory ingredients?",
        "Are there facts showing legally enforceable debt or a probable defence?",
    ),
    "CRIMINAL": (
        "What are the alleged offences, ingredients and available procedural safeguards?",
        "What bail, notice, summons or investigation-stage deadlines are active?",
    ),
    "MURDER_CHARGE": (
        "What facts support or weaken the prosecution theory of intention or knowledge?",
        "Can the facts support a reduction to culpable homicide not amounting to murder?",
    ),
    "PRIVATE_DEFENCE": (
        "Did the threat reasonably create apprehension of death, grievous hurt or serious property offence?",
        "Was the defensive force proportionate and within the statutory limits?",
    ),
    "NIGHT_HOUSE_BREAKING": (
        "Do the time, entry method and property facts establish house-breaking after sunset and before sunrise?",
        "Which scene evidence proves the intrusion, continuity of threat and property loss?",
    ),
    "LEGAL_AID_NEED": (
        "Is the person entitled to state-funded legal aid or immediate court-appointed counsel?",
    ),
    "FAMILY": (
        "Which matrimonial, maintenance, custody or residence issues need urgent interim relief?",
        "What income, residence and prior-order records are needed?",
    ),
    "DOMESTIC_VIOLENCE": (
        "Is protection, residence, monetary or custody relief required immediately?",
        "What incident chronology and medical or digital evidence supports the application?",
    ),
    "PROPERTY": (
        "Who has title, possession and documentary continuity over the property?",
        "Are limitation, notice, mutation or injunction issues present?",
    ),
    "CYBER": (
        "Were complaint acknowledgements, transaction IDs and bank escalation records preserved?",
        "Which intermediaries or accounts need preservation requests?",
    ),
    "CONSUMER": (
        "Does the record show defect, deficiency in service or unfair trade practice?",
        "Which invoices, warranty records and complaint trails prove the loss?",
    ),
    "LABOUR": (
        "What contract, wage, termination and statutory-benefit records establish the claim?",
        "Which limitation or forum-selection issues apply?",
    ),
}

NEXT_STEPS_BY_ISSUE: dict[str, tuple[str, ...]] = {
    "CHEQUE_BOUNCE": (
        "Arrange the cheque, return memo, demand notice, postal/courier proof and payment history in date order.",
        "Verify notice and complaint limitation dates before drafting or filing.",
    ),
    "CRIMINAL": (
        "Collect FIR/complaint, summons, remand, bail and investigation papers in one indexed bundle.",
        "Speak to an advocate or legal aid office before making further statements.",
    ),
    "MURDER_CHARGE": (
        "Treat this as urgent and get criminal defence counsel or legal aid immediately.",
        "Preserve medical, forensic, seizure, CCTV and witness records without alteration.",
    ),
    "PRIVATE_DEFENCE": (
        "Preserve evidence showing the threat, entry, injuries, timing and proportionality of response.",
        "Prepare a minute-by-minute chronology for counsel.",
    ),
    "NIGHT_HOUSE_BREAKING": (
        "Photograph and preserve broken entry points, lockers, scene condition and property-loss records.",
        "Secure CCTV/DVR originals and chain-of-custody details.",
    ),
    "LEGAL_AID_NEED": (
        "Contact the court legal services authority or district legal services authority at once.",
    ),
    "FAMILY": (
        "Collect marriage, residence, income, bank, school and prior-case/order documents.",
    ),
    "DOMESTIC_VIOLENCE": (
        "Prepare an incident chronology with dates, witnesses, medical records and message screenshots.",
    ),
    "PROPERTY": (
        "Collect title chain, possession proof, tax/utility records, notices and prior litigation papers.",
    ),
    "CYBER": (
        "Preserve screenshots, transaction IDs, bank complaints, cyber-portal acknowledgements and device logs.",
    ),
    "CONSUMER": (
        "Collect invoices, warranty terms, job sheets, complaint emails and loss calculations.",
    ),
    "LABOUR": (
        "Collect appointment letter, salary slips, attendance, termination notice and employer communications.",
    ),
}

DEFAULT_RESEARCH_QUESTIONS = (
    "What legal forum, limitation period and interim relief options should be checked first?",
    "What additional documents are required before a lawyer can assess merits?",
)

DEFAULT_NEXT_STEPS = (
    "Build a dated chronology with all notices, payments, communications and official documents.",
    "Separate original evidence from working copies and avoid altering digital material.",
)

BROAD_TITLE_TAGS = {"CRIMINAL", "UNKNOWN"}


@dataclass(frozen=True)
class BriefSource:
    source_type: str
    title: str
    snippet: str
    score: float
    source_url: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "title": self.title,
            "snippet": self.snippet,
            "score": self.score,
            "source_url": self.source_url,
            "metadata": self.metadata or {},
        }


@dataclass(frozen=True)
class CaseResearchBrief:
    title: str
    summary: str
    issue_tags: list[str]
    confidence: float
    key_dates: list[str]
    evidence_found: dict[str, list[str]]
    missing_documents: list[str]
    urgency_warnings: list[str]
    research_questions: list[str]
    next_steps: list[str]
    source_digest: list[BriefSource]
    disclaimer: str = BRIEF_DISCLAIMER

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "issue_tags": self.issue_tags,
            "confidence": self.confidence,
            "key_dates": self.key_dates,
            "evidence_found": self.evidence_found,
            "missing_documents": self.missing_documents,
            "urgency_warnings": self.urgency_warnings,
            "research_questions": self.research_questions,
            "next_steps": self.next_steps,
            "source_digest": [source.to_dict() for source in self.source_digest],
            "disclaimer": self.disclaimer,
            "markdown": self.to_markdown(),
        }

    def to_markdown(self) -> str:
        parts = [
            f"# {self.title}",
            "",
            "## Case Summary",
            self.summary or "No summary available.",
            "",
            "## Issues",
            *_bullets(self.issue_tags),
            "",
            "## Key Dates",
            *_bullets(self.key_dates or ["No dates detected."]),
            "",
            "## Evidence Mentioned",
            *_evidence_bullets(self.evidence_found),
            "",
            "## Missing Documents",
            *_bullets(self.missing_documents or ["No missing documents detected from the current facts."]),
            "",
            "## Research Questions",
            *_bullets(self.research_questions),
            "",
            "## Next Steps",
            *_bullets(self.next_steps),
        ]
        if self.urgency_warnings:
            parts.extend(["", "## Urgency Warnings", *_bullets(self.urgency_warnings)])
        parts.extend(["", "## Source Digest"])
        if self.source_digest:
            for index, source in enumerate(self.source_digest, start=1):
                url = f"\n   Source: {source.source_url}" if source.source_url else ""
                parts.append(
                    f"{index}. **{source.title}** ({source.source_type}, score {source.score:.3f})\n"
                    f"   {source.snippet}{url}"
                )
        else:
            parts.append("- No source matches were available.")
        parts.extend(["", "## Disclaimer", self.disclaimer])
        return "\n".join(parts)


def build_case_research_brief(
    analysis: CaseAnalysis,
    retrieved_results: list[SearchResult],
    *,
    max_sources: int = 8,
) -> CaseResearchBrief:
    issue_tags = analysis.issue_tags or ["UNKNOWN"]
    return CaseResearchBrief(
        title=_brief_title(issue_tags),
        summary=analysis.summary,
        issue_tags=issue_tags,
        confidence=analysis.confidence,
        key_dates=analysis.dates_found,
        evidence_found=analysis.evidence_found,
        missing_documents=analysis.missing_documents,
        urgency_warnings=analysis.warnings,
        research_questions=_questions_for_issues(issue_tags),
        next_steps=_next_steps_for_issues(issue_tags, analysis.missing_documents),
        source_digest=_source_digest(retrieved_results, max_sources=max_sources),
    )


def _brief_title(issue_tags: list[str]) -> str:
    primary = next((issue for issue in issue_tags if issue not in BROAD_TITLE_TAGS), None)
    primary = primary or next((issue for issue in issue_tags if issue != "UNKNOWN"), None)
    if not primary:
        return "Preliminary Legal Research Brief"
    return f"{primary.replace('_', ' ').title()} Research Brief"


def _questions_for_issues(issue_tags: list[str]) -> list[str]:
    questions: list[str] = []
    for issue in issue_tags:
        questions.extend(RESEARCH_QUESTIONS_BY_ISSUE.get(issue, ()))
    questions.extend(DEFAULT_RESEARCH_QUESTIONS)
    return _ordered_unique(questions)


def _next_steps_for_issues(issue_tags: list[str], missing_documents: list[str]) -> list[str]:
    steps: list[str] = []
    for issue in issue_tags:
        steps.extend(NEXT_STEPS_BY_ISSUE.get(issue, ()))
    if missing_documents:
        steps.append("Request or collect the missing documents identified in this brief.")
    steps.extend(DEFAULT_NEXT_STEPS)
    return _ordered_unique(steps)


def _source_digest(results: list[SearchResult], *, max_sources: int) -> list[BriefSource]:
    digest: list[BriefSource] = []
    seen: set[tuple[str, str | None]] = set()
    for result in results:
        key = (result.title, result.source_url)
        if key in seen:
            continue
        seen.add(key)
        digest.append(
            BriefSource(
                source_type=result.source_type,
                title=result.title,
                snippet=result.snippet,
                score=result.score,
                source_url=result.source_url,
                metadata=result.metadata,
            )
        )
        if len(digest) >= max(max_sources, 0):
            break
    return digest


def _ordered_unique(values: list[str] | tuple[str, ...]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = value.strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        unique.append(clean)
    return unique


def _bullets(values: list[str]) -> list[str]:
    return [f"- {value}" for value in values]


def _evidence_bullets(evidence: dict[str, list[str]]) -> list[str]:
    if not evidence:
        return ["- No evidence categories detected."]
    return [
        f"- {category.replace('_', ' ').title()}: {', '.join(matches)}"
        for category, matches in evidence.items()
    ]
