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
