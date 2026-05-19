import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app


class FastAPIRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_reports_fastapi_backend(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(response.json()["backend"], "fastapi")

    def test_submissions_route_returns_demo_portfolio(self):
        response = self.client.get("/api/submissions")

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()["submissions"]), 1)

    def test_intake_bootstrap_is_api_based(self):
        response = self.client.get("/api/intake/bootstrap")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertIn("submissions", payload)
        self.assertIn("brokers", payload)
        self.assertIn("intake_status", payload)

    def test_dev_submission_list_is_api_based(self):
        response = self.client.get("/api/dev/submissions")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["count"], len(payload["submissions"]))

    def test_dev_catalog_exposes_supporting_data(self):
        response = self.client.get("/api/dev/catalog")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertIn("overview", payload)
        self.assertIn("brokers", payload)
        self.assertIn("claims", payload)
        self.assertIn("agent_skills", payload)
        self.assertIn("workflow", payload)
        self.assertIn("data_sources", payload)
        self.assertGreaterEqual(payload["overview"]["data_source_count"], 1)

    def test_openapi_docs_are_available(self):
        response = self.client.get("/docs")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])

    def test_static_search_page_is_served_after_api_routes(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Search Submissions", response.text)

    def test_static_dev_page_is_refreshable(self):
        response = self.client.get("/dev.html?q=acme")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Developer Tools", response.text)

    def test_chat_validation_uses_existing_error_shape(self):
        response = self.client.post("/api/chat", json={"messages": []})

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_application_file_draft_accepts_multipart_upload(self):
        sample_path = Path("tests/sample_submission/cyber-application-sample.txt")

        with sample_path.open("rb") as sample_file:
            response = self.client.post(
                "/api/intake/draft-file",
                files={"file": ("cyber-application-sample.txt", sample_file, "text/plain")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("application_form", response.json())

    def test_intake_review_previews_downstream_population(self):
        response = self.client.post(
            "/api/intake/review",
            json={
                "draft": {
                    "title": "Review Preview Foods",
                    "insured_name": "Review Preview Foods LLC",
                    "industry": "Food distribution",
                    "location": "Chicago, IL",
                    "annual_revenue": 12500000,
                    "records_count": 25000,
                    "mfa": "Enabled for email",
                    "edr": "Deployed",
                    "backup": "Daily backups",
                },
                "intake_status": {
                    "documents": [
                        {"key": "cyber_application", "label": "Cyber application", "status": "received"}
                    ]
                },
            },
        )
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["review"]["status"], "awaiting_underwriter_confirmation")
        self.assertIn("steps", payload["review"])
        self.assertTrue(any(step["key"] == "analytics_initialization" for step in payload["review"]["steps"]))

    def test_intake_and_dev_routes_are_in_openapi_schema(self):
        schema = self.client.get("/openapi.json").json()

        self.assertIn("/api/intake/submissions", schema["paths"])
        self.assertIn("/api/intake/review", schema["paths"])
        self.assertIn("/api/intake/draft-file", schema["paths"])
        self.assertIn("/api/dev/catalog", schema["paths"])
        self.assertIn("/api/dev/submissions", schema["paths"])
        self.assertIn("/api/dev/submissions/{submission_id}", schema["paths"])


if __name__ == "__main__":
    unittest.main()
