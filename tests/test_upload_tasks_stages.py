import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.services import stage_state_service, submission_service, task_service, upload_service


class UploadTaskStageTests(unittest.TestCase):
    def test_upload_txt_adds_document_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / "submissions"
            folder = data_dir / "test-submission"
            folder.mkdir(parents=True)
            (folder / "metadata.json").write_text(
                json.dumps(
                    {
                        "id": "test-submission",
                        "title": "Test Submission",
                        "status": "New",
                        "applicant": {"insured_name": "Test Co", "industry": "Technology"},
                        "coverage": {"lines_requested": ["Cyber liability"]},
                        "documents": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with patch.object(upload_service, "DATA_DIR", data_dir), patch.object(submission_service, "DATA_DIR", data_dir):
                result = upload_service.upload_submission_file(
                    "test-submission",
                    "Broker Email.txt",
                    b"Broker email: Cyber application attached. MFA is deployed for all remote access.",
                )

            document = result["document"]
            self.assertEqual(document["file_name"], "broker-email.txt")
            self.assertIn("cyber_security", document["major_categories"])
            self.assertTrue((folder / "broker-email.txt").exists())

    def test_task_save_uses_temp_directory_and_validates_shape(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(task_service, "TASK_DIR", Path(temp_dir)), patch.object(task_service, "submission_exists", lambda _: True):
                record = task_service.save_task_record(
                    "test-submission",
                    [{"id": "task-1", "title": "Request loss runs", "due_date": "2026-05-22", "status": "open"}],
                )

            self.assertEqual(record["tasks"][0]["title"], "Request loss runs")
            self.assertEqual(record["tasks"][0]["status"], "open")

    def test_stage_submit_locks_checked_stages_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(stage_state_service, "STATES_DIR", Path(temp_dir)), patch.object(stage_state_service, "submission_exists", lambda _: True):
                record = stage_state_service.submit_stage_state_record(
                    "test-submission",
                    [
                        {"key": "intake", "label": "Intake", "checked": True},
                        {"key": "quote", "label": "Quote", "checked": False},
                    ],
                )

            intake, quote = record["stages"]
            self.assertTrue(intake["locked"])
            self.assertFalse(quote["locked"])

    def test_delete_submission_record_removes_related_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            submission_id = "test-submission"
            submissions_dir = root / "submissions"
            submission_folder = submissions_dir / submission_id
            submission_folder.mkdir(parents=True)
            (submission_folder / "metadata.json").write_text(
                json.dumps(
                    {
                        "id": submission_id,
                        "title": "Test Submission",
                        "status": "New",
                        "applicant": {"insured_name": "Test Co", "industry": "Technology"},
                        "coverage": {"lines_requested": ["Cyber liability"]},
                        "documents": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            search_metadata_path = root / "metadata.json"
            search_metadata_path.write_text(
                json.dumps({"submissions": [{"id": submission_id}, {"id": "keep-me"}]}) + "\n",
                encoding="utf-8",
            )

            related_dirs = {
                "CHAT_HISTORY_DIR": root / "chat_history",
                "CLAIMS_DIR": root / "claims",
                "DECISION_WORKFLOW_DIR": root / "decision_workflow",
                "GUIDE_DIR": root / "guide",
                "INTAKE_STATUS_DIR": root / "intake_status",
                "NOTE_DIR": root / "note",
                "STATES_DIR": root / "states",
                "TASK_DIR": root / "task",
                "UNDERWRITING_DIR": root / "underwriting",
            }
            for name, directory in related_dirs.items():
                directory.mkdir(parents=True)
                if name == "CHAT_HISTORY_DIR":
                    history_folder = directory / submission_id
                    history_folder.mkdir()
                    (history_folder / "history.json").write_text("{}\n", encoding="utf-8")
                else:
                    (directory / f"{submission_id}.json").write_text("{}\n", encoding="utf-8")

            patches = [
                patch.object(submission_service, "DATA_DIR", submissions_dir),
                patch.object(submission_service, "SEARCH_METADATA_PATH", search_metadata_path),
                *[
                    patch.object(submission_service, name, directory)
                    for name, directory in related_dirs.items()
                ],
            ]
            for patcher in patches:
                patcher.start()
            try:
                result = submission_service.delete_submission_record(submission_id)
            finally:
                for patcher in reversed(patches):
                    patcher.stop()

            self.assertEqual(result["submission_id"], submission_id)
            self.assertFalse(submission_folder.exists())
            self.assertFalse((related_dirs["CHAT_HISTORY_DIR"] / submission_id).exists())
            self.assertFalse((related_dirs["CLAIMS_DIR"] / f"{submission_id}.json").exists())
            remaining = json.loads(search_metadata_path.read_text(encoding="utf-8"))["submissions"]
            self.assertEqual(remaining, [{"id": "keep-me"}])


if __name__ == "__main__":
    unittest.main()
