from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable


@dataclass(frozen=True)
class RetrievalCase:
    query: str
    relevant_ids: frozenset[str]
    mode: str = "hybrid"

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RetrievalCase":
        relevant = value.get("relevant_ids", value.get("relevant", []))
        if not isinstance(relevant, list) or not relevant:
            raise ValueError("Each evaluation case needs a non-empty relevant_ids list.")
        query = str(value.get("query", "")).strip()
        if not query:
            raise ValueError("Each evaluation case needs a non-empty query.")
        return cls(query=query, relevant_ids=frozenset(str(item) for item in relevant), mode=str(value.get("mode", "hybrid")))


@dataclass(frozen=True)
class RetrievalEvaluation:
    cases: int
    recall_at_k: float
    mean_reciprocal_rank: float
    zero_result_rate: float
    k: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "cases": self.cases,
            "k": self.k,
            "recall_at_k": self.recall_at_k,
            "mean_reciprocal_rank": self.mean_reciprocal_rank,
            "zero_result_rate": self.zero_result_rate,
        }


def evaluate_retrieval(
    cases: Iterable[RetrievalCase],
    search: Callable[[str, int, str], list[Any]],
    *,
    k: int = 10,
    result_id: Callable[[Any], str] | None = None,
) -> RetrievalEvaluation:
    """Evaluate a search callable against human-labelled relevant IDs.

    ``search`` receives query, k and mode. ``result_id`` may extract a stable
    document/case ID; by default the result title is used for simple fixtures.
    """
    bounded_k = max(min(int(k), 50), 1)
    case_list = list(cases)
    if not case_list:
        return RetrievalEvaluation(0, 0.0, 0.0, 0.0, bounded_k)
    get_id = result_id or (lambda item: str(getattr(item, "title", item)))
    recalls: list[float] = []
    reciprocal_ranks: list[float] = []
    zero_results = 0
    for case in case_list:
        results = list(search(case.query, bounded_k, case.mode))[:bounded_k]
        if not results:
            zero_results += 1
        ranked_ids = [get_id(item) for item in results]
        relevant_positions = [index + 1 for index, item_id in enumerate(ranked_ids) if item_id in case.relevant_ids]
        recalls.append(1.0 if relevant_positions else 0.0)
        reciprocal_ranks.append(1.0 / relevant_positions[0] if relevant_positions else 0.0)
    return RetrievalEvaluation(
        cases=len(case_list),
        recall_at_k=round(sum(recalls) / len(recalls), 4),
        mean_reciprocal_rank=round(sum(reciprocal_ranks) / len(reciprocal_ranks), 4),
        zero_result_rate=round(zero_results / len(case_list), 4),
        k=bounded_k,
    )
