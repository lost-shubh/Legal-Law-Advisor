from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from legal_db.llm.rag import LocalLegalRagPipeline, RagResponse
from legal_db.retrieval.staging import SearchResult, tokenize


@dataclass(frozen=True)
class VerifiedClaim:
    text: str
    support: str
    overlap_score: float
    evidence_ids: list[str]
    matched_terms: list[str]
    evidence_excerpts: list[str]
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "support": self.support,
            "overlap_score": self.overlap_score,
            "evidence_ids": self.evidence_ids,
            "matched_terms": self.matched_terms,
            "evidence_excerpts": self.evidence_excerpts,
            "confidence": self.confidence,
        }


def _sentences(answer: str) -> list[str]:
    return [item.strip() for item in re.split(r"(?<=[.!?])\s+", answer.strip()) if item.strip()]


def _evidence_id(result: SearchResult, index: int) -> str:
    return f"evidence-{index + 1}-{result.source_type.lower()}"


def _evidence_payload(results: list[SearchResult]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for index, result in enumerate(results):
        item = result.to_dict()
        item["evidence_id"] = _evidence_id(result, index)
        payload.append(item)
    return payload


def _verify_claim(sentence: str, results: list[SearchResult]) -> VerifiedClaim:
    claim_terms = tokenize(sentence)
    candidates: list[tuple[float, str, list[str], str]] = []
    for index, result in enumerate(results):
        evidence_terms = tokenize(result.snippet)
        matched = sorted(claim_terms & evidence_terms)
        overlap = len(matched) / max(len(claim_terms), 1)
        if overlap > 0:
            candidates.append((overlap, _evidence_id(result, index), matched, result.snippet))
    candidates.sort(reverse=True)
    best_score = candidates[0][0] if candidates else 0.0
    if best_score >= 0.5:
        support = "supported"
    elif best_score >= 0.25:
        support = "partially_supported"
    else:
        support = "unverified"
    accepted = [item for item in candidates[:2] if item[0] >= 0.25]
    return VerifiedClaim(
        text=sentence,
        support=support,
        overlap_score=round(best_score, 3),
        evidence_ids=[item[1] for item in accepted],
        matched_terms=accepted[0][2] if accepted else [],
        evidence_excerpts=[item[3] for item in accepted],
        confidence=round(min(best_score, 1.0), 3),
    )


def build_verified_research(
    question: str,
    *,
    context_limit: int = 5,
    use_llm: bool = True,
    pipeline: LocalLegalRagPipeline | None = None,
) -> dict[str, Any]:
    """Return an answer together with transparent claim/evidence verification.

    This is intentionally conservative: unsupported generated sentences are not
    presented as verified legal claims.
    """
    response: RagResponse = (pipeline or LocalLegalRagPipeline()).answer(
        question, context_limit=context_limit, use_llm=use_llm
    )
    evidence = _evidence_payload(response.retrieved_results)
    if not response.retrieved_results:
        return {
            "question": question,
            "answer": None,
            "verified_answer": None,
            "claims": [],
            "evidence": [],
            "verification_status": "abstained_no_evidence",
            "model": response.model,
            "model_status": response.model_status,
            "abstention_reason": "No searchable authority matched the question.",
            "error": response.error,
        }

    claims = [_verify_claim(sentence, response.retrieved_results) for sentence in _sentences(response.answer or "")]
    supported_text = " ".join(claim.text for claim in claims if claim.support == "supported")
    if not use_llm:
        status = "evidence_only"
        reason = "LLM generation was disabled; review the cited evidence directly."
    elif not claims or not supported_text:
        status = "abstained_unverified"
        reason = "The generated response did not contain claims with sufficient evidence overlap."
    elif any(claim.support != "supported" for claim in claims):
        status = "partially_verified"
        reason = "Partially supported or unsupported sentences were withheld from the verified answer."
    else:
        status = "verified_with_evidence"
        reason = None
    return {
        "question": question,
        "answer": response.answer,
        "verified_answer": supported_text or None,
        "claims": [claim.to_dict() for claim in claims],
        "evidence": evidence,
        "verification_status": status,
        "model": response.model,
        "model_status": response.model_status,
        "abstention_reason": reason,
        "error": response.error,
    }
