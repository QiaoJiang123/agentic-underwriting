import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.config import AUTH_DB_PATH
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

    def test_auth_context_exposes_local_policy(self):
        response = self.client.get("/api/auth/context", headers={"x-au-user": "uw-assistant"})
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["auth"]["user_id"], "uw-assistant")
        self.assertEqual(payload["auth"]["role"], "underwriting_assistant")
        self.assertIn("submission:read", payload["auth"]["permissions"])
        self.assertIn("policy", payload)

    def test_admin_login_uses_local_login_database(self):
        client = TestClient(app)
        response = client.post("/api/auth/login", json={"username": "admin", "password": "AU-Admin-2026!"})
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(AUTH_DB_PATH.exists())
        self.assertEqual(payload["login"]["auth"]["user_id"], "admin")
        self.assertEqual(payload["login"]["auth"]["role"], "senior_underwriter")

        context_response = client.get("/api/auth/context")
        context_payload = context_response.json()
        self.assertEqual(context_response.status_code, 200)
        self.assertEqual(context_payload["auth"]["user_id"], "admin")
        self.assertEqual(context_payload["auth"]["auth_source"], "local login session")

    def test_admin_login_rejects_bad_password(self):
        client = TestClient(app)
        response = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})

        self.assertEqual(response.status_code, 401)
        self.assertIn("Invalid username or password", response.json()["error"])

    def test_submission_scope_blocks_unauthorized_account(self):
        response = self.client.get(
            "/api/submissions/010-sunrise-hospitality-group/claims",
            headers={"x-au-user": "uw-assistant"},
        )
        payload = response.json()

        self.assertEqual(response.status_code, 403)
        self.assertIn("outside user scope", payload["error"])

    def test_read_only_user_cannot_delete_submission(self):
        response = self.client.delete(
            "/api/dev/submissions/001-acme-foods",
            headers={"x-au-user": "audit-demo"},
        )
        payload = response.json()

        self.assertEqual(response.status_code, 403)
        self.assertIn("Missing permission dev:delete", payload["error"])

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
        self.assertIn("agent_tools", payload)
        self.assertIn("workflow", payload)
        self.assertIn("data_sources", payload)
        self.assertGreaterEqual(payload["overview"]["data_source_count"], 1)
        self.assertGreaterEqual(len(payload["workflow"]["cycles"]), 1)
        self.assertTrue(any(source["key"] == "agent_traces" for source in payload["data_sources"]))
        self.assertTrue(any(source["key"] == "portfolio_queue" for source in payload["data_sources"]))
        self.assertTrue(any(source["key"] == "underwriting_claim_analytics_db" for source in payload["data_sources"]))
        workflow_labels = {node["label"] for node in payload["workflow"]["nodes"]}
        self.assertIn("Multi-Step Planner", workflow_labels)
        self.assertIn("Tool Execution Loop", workflow_labels)
        self.assertIn("Confidence Check", workflow_labels)
        self.assertIn("Retry Expansion", workflow_labels)
        self.assertIn("Trace Persistence", workflow_labels)
        orchestration = payload["workflow"]["orchestration"]
        layer_keys = {layer["key"] for layer in orchestration["layers"]}
        self.assertEqual(layer_keys, {"planner", "tool_loop", "confidence", "retry", "trace"})
        self.assertGreaterEqual(len(orchestration["execution_paths"]), 3)
        self.assertIn("trace_id", orchestration["trace_contract"])
        self.assertIn("tool_registry", orchestration)
        self.assertGreaterEqual(orchestration["tool_registry"]["summary"]["tool_count"], 20)

    def test_agent_tools_route_exposes_tool_contracts(self):
        response = self.client.get("/api/agent-tools")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertIn("tools", payload)
        self.assertIn("contract_fields", payload)
        self.assertGreaterEqual(payload["summary"]["read_tool_count"], 10)
        self.assertGreaterEqual(payload["summary"]["write_tool_count"], 1)
        document_tool = next(tool for tool in payload["tools"] if tool["skill"] == "documents")
        self.assertEqual(document_tool["required_permission"], "submission:read")
        self.assertTrue(document_tool["mcp_exposed"])
        task_tool = next(tool for tool in payload["tools"] if tool["skill"] == "write_task")
        self.assertEqual(task_tool["tool_type"], "write")

    def test_portfolio_and_workbench_feature_routes(self):
        queue_response = self.client.get("/api/portfolio/queue")
        queue_payload = queue_response.json()

        self.assertEqual(queue_response.status_code, 200)
        self.assertIn("overview", queue_payload["portfolio"])
        self.assertGreaterEqual(queue_payload["portfolio"]["overview"]["submission_count"], 1)
        self.assertLess(
            queue_payload["portfolio"]["overview"]["referral_count"],
            queue_payload["portfolio"]["overview"]["submission_count"],
        )

        for suffix, key in [
            ("clearance", "clearance"),
            ("external-research", "external_research"),
            ("rating-quote", "rating_quote"),
        ]:
            response = self.client.get(f"/api/submissions/001-acme-foods/{suffix}")
            self.assertEqual(response.status_code, 200)
            self.assertIn(key, response.json())

        rating = self.client.get("/api/submissions/001-acme-foods/rating-quote").json()["rating_quote"]
        self.assertIn("calculation", rating)
        self.assertIn("authority_path", rating)
        self.assertIn("referral_reasons", rating)

    def test_dev_agent_traces_route_is_api_based(self):
        response = self.client.get("/api/dev/agent-traces")

        self.assertEqual(response.status_code, 200)
        self.assertIn("agent_traces", response.json())

    def test_analytics_db_route_builds_two_table_mart(self):
        response = self.client.get("/api/analytics-db?refresh=true")
        payload = response.json()["analytics_db"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["table_names"], ["underwriting_submission_analytics", "claim_analytics"])
        self.assertEqual(payload["join_key"], "company_id")
        self.assertGreaterEqual(payload["row_count"]["underwriting_submission_analytics"], 50)
        self.assertGreaterEqual(payload["row_count"]["claim_analytics"], 1)
        self.assertIn("underwriting_submission_analytics", payload["schemas"])
        self.assertIn("claim_analytics", payload["schemas"])
        claim_columns = {column["name"] for column in payload["schemas"]["claim_analytics"]}
        submission_columns = {column["name"] for column in payload["schemas"]["underwriting_submission_analytics"]}
        self.assertIn("CLM_CLMT_ID", claim_columns)
        self.assertIn("company_id", claim_columns)
        self.assertIn("submission_id", submission_columns)
        self.assertIn("company_id", submission_columns)
        self.assertIn("total_claims", payload["overview"])
        self.assertIn("broker_summary", payload)

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

    def test_static_business_deck_page_is_served(self):
        response = self.client.get("/business.html")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Business Deck", response.text)

    def test_static_login_page_is_served(self):
        response = self.client.get("/login.html")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Login", response.text)

    def test_chat_validation_uses_existing_error_shape(self):
        response = self.client.post("/api/chat", json={"messages": []})

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_chat_body_submission_scope_is_authorized(self):
        response = self.client.post(
            "/api/chat",
            headers={"x-au-user": "uw-assistant"},
            json={
                "submission_id": "010-sunrise-hospitality-group",
                "user_prompt": "show claim information",
                "messages": [{"role": "user", "content": "show claim information"}],
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn("outside user scope", response.json()["error"])

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
        self.assertIn("/api/auth/context", schema["paths"])
        self.assertIn("/api/auth/login", schema["paths"])
        self.assertIn("/api/auth/logout", schema["paths"])
        self.assertIn("/api/agent-tools", schema["paths"])
        self.assertIn("/api/intake/review", schema["paths"])
        self.assertIn("/api/intake/draft-file", schema["paths"])
        self.assertIn("/api/dev/catalog", schema["paths"])
        self.assertIn("/api/dev/submissions", schema["paths"])
        self.assertIn("/api/dev/submissions/{submission_id}", schema["paths"])
        self.assertIn("/api/dev/agent-traces", schema["paths"])
        self.assertIn("/api/portfolio/queue", schema["paths"])
        self.assertIn("/api/analytics-db", schema["paths"])
        self.assertIn("/api/analytics-db/refresh", schema["paths"])
        self.assertIn("/api/submissions/{submission_id}/clearance", schema["paths"])
        self.assertIn("/api/submissions/{submission_id}/external-research", schema["paths"])
        self.assertIn("/api/submissions/{submission_id}/rating-quote", schema["paths"])
        self.assertIn("/api/submissions/{submission_id}/agent-traces", schema["paths"])
        self.assertIn("/api/submissions/{submission_id}/agent-traces/{trace_id}", schema["paths"])


if __name__ == "__main__":
    unittest.main()
