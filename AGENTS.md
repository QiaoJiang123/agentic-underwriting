# Agent Instructions

This repo is a local demo platform for agentic commercial cyber underwriting. Use this file as the standing coding direction for future agent work in this project.

## Product Direction

- Build a usable underwriting workbench, not a marketing site.
- Keep the underwriter in control. AI can retrieve, summarize, suggest, and draft, but final underwriting decisions stay human-owned.
- Treat this as a demo that should still look and behave like a credible commercial insurance system.
- Prefer features that improve intake, evidence review, broker follow-up, claims review, model interpretation, workflow control, auditability, and data retrieval.

## Architecture Rules

- Backend is Python FastAPI. Do not add or restore a separate Node backend.
- Frontend is vanilla HTML, CSS, and JavaScript served by FastAPI.
- Keep API routes in `backend/api/routes.py` unless a route group clearly deserves extraction.
- Keep business logic in `backend/services/`.
- Keep local demo data under `data/`.
- Keep model artifacts under `model/`.
- Keep browser UI files under `public/`.
- Keep tests under `tests/`.
- Do not put API keys, model keys, or secrets in frontend files or committed data.

## Agent And Retrieval Rules

- The centralized information agent is the orchestration layer for chat retrieval.
- Use `backend/services/agent_tool_registry.py` as the source of truth for tool contracts, permissions, scope, citation policy, and MCP readiness.
- When adding a new retrieval or write capability, update the registry, permission mapping, trace output, and tests.
- Retrieval should return cited sources whenever possible.
- Full selected document text may be sent for the active chat request, but it must not be saved into chat history.
- Notes are underwriter-supplied ground truth and may be sent as context.
- Guides are operating instructions and should be treated as higher-priority prompt guidance.
- SOP should be retrieved when the prompt asks for process, next steps, evidence standards, follow-up, referral, quote readiness, or underwriting discipline.
- Write actions such as stage submission, document deletion, metadata update, and upload should require explicit UI confirmation when there is meaningful risk.

## Data Rules

- Prefer structured JSON or SQLite over hard-coded UI data.
- Keep submission records keyed by submission id.
- Keep company-level analytics joinable by `company_id`.
- Keep claim rows separate from submission rows.
- Validate records before writing when a schema exists.
- When adding new dummy data, keep it plausible for commercial cyber underwriting.
- Avoid random runtime values for important underwriting outputs. Use deterministic seeds or stored artifacts.

## Frontend Rules

- Follow `STYLE_GUIDE.md` for visual design, layout, colors, typography, and interaction patterns.
- Keep the interface dense, professional, light, and technical.
- Avoid oversized marketing hero sections inside the operating app.
- Preserve the two-panel workbench model: left navigation/evidence, center chat, right underwriting surfaces.
- Expanded pages should have clear titles and a visible `Back to Chat` control.
- Do not add decorative gradient blobs, one-note palettes, or large visual clutter.
- Important selected surfaces should be highlighted only where selected, not across unrelated sections.
- Use stable dimensions for cards, buttons, tabs, lists, charts, and controls so layout does not jump.
- Make text fit on desktop and mobile. Long values should reveal full content through title/tooltips or expanded views.

## Backend Rules

- Keep endpoints API-driven when a page reads or writes state.
- Use local services for file/document work; do not expose raw filesystem paths to users unless needed for local dev documentation.
- Preserve login/session behavior and permission checks on protected API routes.
- Add audit entries for meaningful protected reads and writes when existing patterns support it.
- Use safe file handling for uploads. Accept only intended demo file types unless the requirement changes.

## Testing Rules

Run focused tests after small changes and the full suite after broad backend/frontend contract changes:

```bash
.venv/bin/python -m unittest discover tests
```

For frontend JavaScript syntax checks:

```bash
node --check public/app.js
node --check public/search.js
node --check public/dev.js
```

When UI behavior changes, check it in the local browser at `http://localhost:3000`.

## Documentation Rules

- Update `README.md` when adding a user-visible feature, data store, API behavior, or workflow.
- Update `docs/platform-requirements-readiness.md` when changing platform architecture, agent design, readiness, or major capabilities.
- Update `STYLE_GUIDE.md` when introducing a new reusable UI pattern.

## Constraints

- Do not delete or overwrite user-created data unless explicitly requested.
- Do not silently change seeded credentials or demo login behavior.
- Do not remove existing sample submissions unless asked.
- Keep changes scoped and explain tradeoffs when a feature is demo-only.
