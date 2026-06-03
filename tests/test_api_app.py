import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))



class ApiAppTest(unittest.TestCase):
    def test_health_function_reports_service(self) -> None:
        from legal_api.main import health

        payload = health()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["service"], "legal-api")

    def test_fastapi_search_route_without_llm(self) -> None:
        from fastapi.testclient import TestClient

        from legal_api.main import app

        self.assertIsNotNone(app)
        client = TestClient(app)
        response = client.post(
            "/v1/search",
            json={"query": "constitution basic structure", "limit": 3},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.json())

    def test_model_status_route_is_safe_without_chat_call(self) -> None:
        from fastapi.testclient import TestClient

        from legal_api.main import app

        client = TestClient(app)
        response = client.get("/v1/models/ollama")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsInstance(payload["configured_model"], str)
        self.assertIn("available", payload)

    def test_chat_status_route_reports_model_and_corpus(self) -> None:
        from fastapi.testclient import TestClient

        from legal_api.main import app

        client = TestClient(app)
        response = client.get("/v1/chat/status")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("ready", payload)
        self.assertIn("model", payload)
        self.assertIn("corpus", payload)

    def test_ingestion_status_route_is_available(self) -> None:
        from fastapi.testclient import TestClient

        from legal_api.main import app

        client = TestClient(app)
        response = client.get("/v1/ingestion/status")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("jobs", payload)
        self.assertIn("items", payload)
        self.assertIn("recent_jobs", payload)

    def test_case_analyze_route_without_llm(self) -> None:
        from fastapi.testclient import TestClient

        from legal_api.main import app

        client = TestClient(app)
        response = client.post(
            "/v1/cases/analyze",
            json={
                "case_text": (
                    "Cheque was dishonoured on 12/04/2025. Legal notice was sent. "
                    "The complainant has the bank return memo and WhatsApp messages."
                ),
                "context_limit": 2,
                "use_llm": False,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["model_status"], "skipped")
        self.assertIn("CHEQUE_BOUNCE", payload["analysis"]["issue_tags"])

    def test_similar_cases_route_is_available(self) -> None:
        from fastapi.testclient import TestClient

        from legal_api.main import app

        client = TestClient(app)
        response = client.post(
            "/v1/similar-cases",
            json={
                "case_text": (
                    "Cheque dishonour with statutory legal notice, bank return memo, "
                    "and evidence of service."
                ),
                "limit": 3,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.json())

    def test_fastapi_search_route_accepts_semantic_mode(self) -> None:
        from fastapi.testclient import TestClient

        from legal_api.main import app

        client = TestClient(app)
        response = client.post(
            "/v1/search",
            json={
                "query": "cheque dishonour legal notice",
                "limit": 3,
                "source_types": ["JUDGMENT"],
                "mode": "semantic",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.json())
