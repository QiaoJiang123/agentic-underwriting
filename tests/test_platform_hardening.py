import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from backend import mcp_server
from backend.services import maintenance_service
from backend.services.agent_tool_registry import list_mcp_tool_names


class PlatformHardeningTests(unittest.TestCase):
    def test_mcp_tool_allowlist_is_generated_from_registry(self):
        tool_names = list_mcp_tool_names(read_only=True)

        self.assertIn("extract_metadata", tool_names)
        self.assertIn("read_selected_documents", tool_names)
        self.assertIn("list_agent_tool_contracts", tool_names)
        self.assertIn("get_decision_package", tool_names)
        self.assertIn("get_model_governance", tool_names)
        self.assertNotIn("add_scheduled_task", tool_names)

    def test_mcp_registry_tools_return_contracts_and_governance(self):
        registry = mcp_server.list_agent_tool_contracts(compact=True)
        contract = mcp_server.get_agent_tool_contract("decision_package", compact=True)
        governance = mcp_server.get_model_governance("quote_prob")

        self.assertGreaterEqual(registry["summary"]["tool_count"], 20)
        self.assertEqual(contract["tool"]["skill"], "decision_package")
        self.assertEqual(governance["model"]["approval_status"], "demo_only_not_approved")

    def test_mcp_decision_package_tool_returns_structured_package(self):
        package = mcp_server.get_decision_package("001-acme-foods", "bind")

        self.assertEqual(package["package_type"], "bind")
        self.assertEqual(package["submission_id"], "001-acme-foods")
        self.assertTrue(package["citations"])

    def test_intake_upload_cleanup_supports_dry_run_and_delete(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            upload_dir = Path(temp_dir) / "intake_uploads"
            stale_dir = upload_dir / "stale"
            fresh_dir = upload_dir / "fresh"
            stale_dir.mkdir(parents=True)
            fresh_dir.mkdir(parents=True)
            (stale_dir / "old.txt").write_text("old", encoding="utf-8")
            (fresh_dir / "new.txt").write_text("new", encoding="utf-8")

            now = datetime(2026, 5, 29, tzinfo=timezone.utc)
            old_timestamp = (now - timedelta(hours=72)).timestamp()
            fresh_timestamp = (now - timedelta(hours=1)).timestamp()
            os.utime(stale_dir / "old.txt", (old_timestamp, old_timestamp))
            os.utime(stale_dir, (old_timestamp, old_timestamp))
            os.utime(fresh_dir / "new.txt", (fresh_timestamp, fresh_timestamp))
            os.utime(fresh_dir, (fresh_timestamp, fresh_timestamp))

            with patch.object(maintenance_service, "INTAKE_UPLOAD_DIR", upload_dir):
                dry_run = maintenance_service.cleanup_intake_uploads(
                    max_age_hours=24,
                    dry_run=True,
                    now=now,
                )
                deleted = maintenance_service.cleanup_intake_uploads(
                    max_age_hours=24,
                    dry_run=False,
                    now=now,
                )

            self.assertEqual(dry_run["candidate_count"], 1)
            self.assertEqual(dry_run["deleted_count"], 0)
            self.assertEqual(deleted["deleted_count"], 1)
            self.assertFalse(stale_dir.exists())
            self.assertTrue(fresh_dir.exists())


if __name__ == "__main__":
    unittest.main()
