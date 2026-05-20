from copy import deepcopy


class SchemaValidationError(ValueError):
    pass


SCHEMAS = {
    "document_metadata": {
        "type": "object",
        "required": ["file_name", "file_type", "category", "document_types", "major_categories", "description"],
        "properties": {
            "file_name": {"type": "string", "minLength": 1},
            "file_type": {"type": "string", "minLength": 1},
            "category": {"type": "string", "minLength": 1},
            "document_types": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "major_categories": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "description": {"type": "string"},
            "file_created_at": {"type": "string"},
            "received_at": {"type": "string"},
        },
    },
    "submission_metadata": {
        "type": "object",
        "required": ["id", "title", "status", "applicant", "coverage", "documents"],
        "properties": {
            "id": {"type": "string", "minLength": 1},
            "title": {"type": "string", "minLength": 1},
            "status": {"type": "string", "minLength": 1},
            "file_created_at": {"type": "string"},
            "received_at": {"type": "string"},
            "updated_at": {"type": "string"},
            "applicant": {
                "type": "object",
                "required": ["insured_name", "industry"],
                "properties": {
                    "insured_name": {"type": "string", "minLength": 1},
                    "industry": {"type": "string"},
                    "industry_bucket": {"type": "string"},
                    "industry_group": {"type": "string"},
                    "location": {"type": "string"},
                    "annual_revenue": {"type": "number"},
                    "employee_count": {"type": "number"},
                    "records_count": {"type": "number"},
                    "technology_profile": {"type": "string"},
                },
            },
            "coverage": {
                "type": "object",
                "properties": {
                    "lines_requested": {"type": "array", "items": {"type": "string"}},
                    "requested_effective_date": {"type": "string"},
                    "requested_limits": {"type": "object"},
                    "retention_requested": {"type": "string"},
                },
            },
            "broker": {"type": "object"},
            "security_controls": {"type": "object"},
            "documents": {"type": "array", "items": {"$ref": "document_metadata"}},
            "risk_flags": {"type": "array", "items": {"type": "string"}},
            "open_questions": {"type": "array", "items": {"type": "string"}},
            "timeline": {"type": "array", "items": {"type": "object"}},
            "summary": {"type": ["string", "object"]},
        },
    },
    "note_record": {
        "type": "object",
        "required": ["submission_id", "notes"],
        "properties": {
            "submission_id": {"type": "string", "minLength": 1},
            "updated_at": {"type": ["string", "null"]},
            "notes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "text", "created_at", "updated_at"],
                    "properties": {
                        "id": {"type": "string", "minLength": 1},
                        "text": {"type": "string", "minLength": 1},
                        "created_at": {"type": "string"},
                        "updated_at": {"type": "string"},
                    },
                },
            },
        },
    },
    "guide_record": {
        "type": "object",
        "required": ["submission_id", "guides"],
        "properties": {
            "submission_id": {"type": "string", "minLength": 1},
            "updated_at": {"type": ["string", "null"]},
            "guides": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "text", "created_at", "updated_at"],
                    "properties": {
                        "id": {"type": "string", "minLength": 1},
                        "text": {"type": "string", "minLength": 1},
                        "created_at": {"type": "string"},
                        "updated_at": {"type": "string"},
                    },
                },
            },
        },
    },
    "task_record": {
        "type": "object",
        "required": ["submission_id", "tasks"],
        "properties": {
            "submission_id": {"type": "string", "minLength": 1},
            "updated_at": {"type": ["string", "null"]},
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "title", "due_date", "status", "created_at", "updated_at"],
                    "properties": {
                        "id": {"type": "string", "minLength": 1},
                        "title": {"type": "string", "minLength": 1},
                        "due_date": {"type": "string", "pattern": "date"},
                        "status": {"type": "string", "enum": ["open", "done"]},
                        "created_at": {"type": "string"},
                        "updated_at": {"type": "string"},
                    },
                },
            },
        },
    },
    "stage_state_record": {
        "type": "object",
        "required": ["submission_id", "stages"],
        "properties": {
            "submission_id": {"type": "string", "minLength": 1},
            "updated_at": {"type": ["string", "null"]},
            "submitted_at": {"type": ["string", "null"]},
            "stages": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["key", "label", "checked", "locked"],
                    "properties": {
                        "key": {"type": "string", "minLength": 1},
                        "label": {"type": "string", "minLength": 1},
                        "checked": {"type": "boolean"},
                        "locked": {"type": "boolean"},
                    },
                },
            },
        },
    },
    "decision_workflow_record": {
        "type": "object",
        "required": ["submission_id", "generated_at", "gates"],
        "properties": {
            "submission_id": {"type": "string", "minLength": 1},
            "generated_at": {"type": "string"},
            "updated_at": {"type": ["string", "null"]},
            "gates": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["key", "label", "status", "score", "rationale", "blockers", "required_actions"],
                    "properties": {
                        "key": {"type": "string", "minLength": 1},
                        "label": {"type": "string", "minLength": 1},
                        "status": {"type": "string", "minLength": 1},
                        "score": {"type": "number"},
                        "rationale": {"type": "string"},
                        "blockers": {"type": "array", "items": {"type": "string"}},
                        "required_actions": {"type": "array", "items": {"type": "string"}},
                        "sources": {"type": "array", "items": {"type": "string"}},
                        "decision": {"type": "object"},
                    },
                },
            },
        },
    },
    "agent_trace_record": {
        "type": "object",
        "required": ["trace_id", "submission_id", "created_at", "updated_at", "status", "steps"],
        "properties": {
            "trace_id": {"type": "string", "minLength": 1},
            "submission_id": {"type": "string", "minLength": 1},
            "created_at": {"type": "string"},
            "updated_at": {"type": "string"},
            "status": {"type": "string", "minLength": 1},
            "agent": {"type": "string"},
            "prompt_preview": {"type": "string"},
            "attempt_count": {"type": "number"},
            "confidence": {"type": "object"},
            "steps": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["phase", "title", "status", "detail"],
                    "properties": {
                        "phase": {"type": "string", "minLength": 1},
                        "title": {"type": "string", "minLength": 1},
                        "status": {"type": "string", "minLength": 1},
                        "detail": {"type": "string"},
                    },
                },
            },
        },
    },
}


def get_schema_catalog():
    return deepcopy(SCHEMAS)


def validate_named_schema(schema_name, value):
    schema = SCHEMAS.get(schema_name)
    if not schema:
        raise SchemaValidationError(f"Unknown schema: {schema_name}")
    validate_schema(value, schema, schema_name)
    return value


def validate_schema(value, schema, path="$"):
    if "$ref" in schema:
        schema = SCHEMAS[schema["$ref"]]

    expected = schema.get("type")
    if expected is not None and not matches_type(value, expected):
        raise SchemaValidationError(f"{path} must be {format_type(expected)}.")

    if value is None:
        return

    if "enum" in schema and value not in schema["enum"]:
        raise SchemaValidationError(f"{path} must be one of: {', '.join(map(str, schema['enum']))}.")

    if schema.get("minLength") and isinstance(value, str) and len(value) < schema["minLength"]:
        raise SchemaValidationError(f"{path} cannot be empty.")

    if schema.get("pattern") == "date" and isinstance(value, str):
        parts = value.split("-")
        if len(parts) != 3 or not all(part.isdigit() for part in parts):
            raise SchemaValidationError(f"{path} must be an ISO date.")

    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                raise SchemaValidationError(f"{path}.{key} is required.")

        properties = schema.get("properties", {})
        for key, child_value in value.items():
            child_schema = properties.get(key)
            if child_schema:
                validate_schema(child_value, child_schema, f"{path}.{key}")

    if isinstance(value, list):
        min_items = schema.get("minItems")
        if min_items is not None and len(value) < min_items:
            raise SchemaValidationError(f"{path} must contain at least {min_items} item(s).")
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                validate_schema(item, item_schema, f"{path}[{index}]")


def matches_type(value, expected):
    if isinstance(expected, list):
        return any(matches_type(value, item) for item in expected)
    if expected == "null":
        return value is None
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    return True


def format_type(expected):
    if isinstance(expected, list):
        return " or ".join(expected)
    return str(expected)
