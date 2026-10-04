import unittest

from legal_db.evaluation.retrieval import RetrievalCase, evaluate_retrieval


class Result:
    def __init__(self, title: str) -> None:
        self.title = title


class RetrievalEvaluationTest(unittest.TestCase):
    def test_metrics_measure_ranked_relevance(self) -> None:
        cases = [RetrievalCase("q1", frozenset({"right"})), RetrievalCase("q2", frozenset({"missing"}))]

        def search(query: str, k: int, mode: str):
            return [Result("right"), Result("other")] if query == "q1" else []

        metrics = evaluate_retrieval(cases, search, k=2)
        self.assertEqual(metrics.cases, 2)
        self.assertEqual(metrics.recall_at_k, 0.5)
        self.assertEqual(metrics.mean_reciprocal_rank, 0.5)
        self.assertEqual(metrics.zero_result_rate, 0.5)

    def test_case_loader_rejects_missing_labels(self) -> None:
        with self.assertRaises(ValueError):
            RetrievalCase.from_dict({"query": "unlabelled"})


if __name__ == "__main__":
    unittest.main()
