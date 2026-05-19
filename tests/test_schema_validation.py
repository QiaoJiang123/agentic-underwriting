import unittest

from backend.services.schema_service import SchemaValidationError, validate_named_schema


class SchemaValidationTests(unittest.TestCase):
    def test_document_metadata_schema_accepts_valid_record(self):
        record = {
            "file_name": "cyber-application.txt",
            "file_type": "cyber_application",
            "category": "submission",
            "document_types": ["cyber_application"],
            "major_categories": ["submission"],
            "description": "Cyber application uploaded by broker.",
        }

        self.assertIs(validate_named_schema("document_metadata", record), record)

    def test_task_schema_rejects_missing_required_field(self):
        record = {
            "submission_id": "001-acme-foods",
            "tasks": [{"id": "task-1", "title": "Request MFA evidence"}],
        }

        with self.assertRaises(SchemaValidationError):
            validate_named_schema("task_record", record)


if __name__ == "__main__":
    unittest.main()
