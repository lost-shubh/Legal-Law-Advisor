import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))



class ApiAppTest(unittest.TestCase):
    def test_health_function_reports_service(self) -> None:
        from legal_api.main import health

        payload = health()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["service"], "legal-api")

    def test_local_browser_app_route_is_available(self) -> None:
        from fastapi.testclient import TestClient

        from legal_api.main import app

        client = TestClient(app)
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Legal Law Advisor", response.text)
        self.assertIn("Case Analyzer", response.text)
        self.assertIn("/v1/cases/analyze", response.text)
        self.assertIn("/v1/cases/brief", response.text)

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

    def test_extraction_model_status_route(self) -> None:
        from fastapi.testclient import TestClient

        from legal_api.main import app

        client = TestClient(app)
        response = client.get("/v1/models/extraction")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["local_available"])
        self.assertIn("local_model", payload)
        self.assertIn("prompt_version", payload)

    def test_extraction_status_route_is_available(self) -> None:
        from fastapi.testclient import TestClient

        from legal_api.main import app

        client = TestClient(app)
        response = client.get("/v1/extractions/status")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("database_available", payload)
        self.assertIn("extractions", payload)

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

    def test_admin_overview_route_is_available(self) -> None:
        from fastapi.testclient import TestClient

        from legal_api.main import app

        client = TestClient(app)
        response = client.get("/v1/admin/overview")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("corpus", payload)
        self.assertIn("ingestion", payload)
        self.assertIn("extraction", payload)
        self.assertIn("models", payload)
        self.assertIn("quality", payload)

    def test_admin_backend_completion_routes_are_available(self) -> None:
        from fastapi.testclient import TestClient

        from legal_api.main import app

        client = TestClient(app)
        for path in [
            "/health/deep",
            "/v1/admin/panels",
            "/v1/admin/corpus",
            "/v1/admin/sources",
            "/v1/admin/quality",
            "/v1/admin/operations",
        ]:
            response = client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertIn("database_available", response.json() if path != "/health/deep" else {"database_available": True})

    def test_gazette_notification_route_is_available(self) -> None:
        from fastapi.testclient import TestClient

        from legal_api.main import app

        class FakeSummary:
            def to_dict(self) -> dict:
                return {
                    "database_available": False,
                    "notification_id": None,
                    "source_document_id": None,
                    "notification_type": "COMMENCEMENT",
                    "act_name": "The Bharatiya Nyaya Sanhita, 2023",
                    "statute_id": None,
                    "notification_date": "2024-07-01",
                    "sections_affected": [],
                    "updated_statutes": 0,
                    "updated_sections": 0,
                    "error": "test double",
                }

        client = TestClient(app)
        with patch("legal_api.main.upsert_gazette_notification", return_value=FakeSummary()):
            response = client.post(
                "/v1/gazette/notifications",
                json={
                    "text": (
                        "MINISTRY OF HOME AFFAIRS S.O. 850(E). The Bharatiya Nyaya "
                        "Sanhita, 2023 shall come into force on the 1st day of July, 2024."
                    ),
                    "update_effective_dates": False,
                },
            )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("database_available", payload)
        self.assertEqual(payload["notification_type"], "COMMENCEMENT")

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

    def test_case_brief_route_is_available(self) -> None:
        from fastapi.testclient import TestClient

        from legal_api.main import app

        client = TestClient(app)
        response = client.post(
            "/v1/cases/brief",
            json={
                "case_text": (
                    "Cheque was dishonoured on 12/04/2025. Legal notice was sent. "
                    "The complainant has the bank return memo and WhatsApp messages."
                ),
                "context_limit": 2,
                "max_sources": 4,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("Research Brief", payload["title"])
        self.assertIn("CHEQUE_BOUNCE", payload["issue_tags"])
        self.assertIn("markdown", payload)
        self.assertIn("Research aid only", payload["disclaimer"])

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
