Schema registry for the demo underwriting platform.

The backend exposes the active schema catalog at `/api/schemas` and validates
write paths through `backend/services/schema_service.py`. These schemas are
intentionally lightweight JSON-schema-style definitions so the demo can stay
dependency-free while still enforcing the core shapes used by submissions,
documents, tasks, stages, notes, guides, and decision workflow gates.
