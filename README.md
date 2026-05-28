# Agentic Underwriting

A local agentic underwriting workspace for cyber submissions. The app combines a Python backend, a full-window underwriting chat UI, submission document handling, guide/note context, Auto document selection, and demo quote/bind analytics models.

For a fuller platform explanation, revised requirements, and readiness assessment, see `docs/platform-requirements-readiness.md`. The in-app business deck is available at `http://localhost:3000/business.html`.

The local demo login page is available at `http://localhost:3000/login.html`.

Project-level coding guidance lives in `AGENTS.md`. Product UI guidance lives in `STYLE_GUIDE.md`.

```text
Username: admin
Password: AU-Admin-2026!
```

## Run Locally

1. Add your OpenAI key and model to `.env`.

   ```bash
   OPENAI_API_KEY=your_key_here
   OPENAI_MODEL=gpt-5.4-nano
   ```

2. Install Python backend dependencies.

   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

3. Start the local backend.

   ```bash
   .venv/bin/python -m backend.main
   ```

   `npm run dev` and `npm start` point to the same FastAPI backend.

4. Open the app.

   ```text
   http://localhost:3000
   ```

The browser sends chat requests to `/api/chat`. The backend calls the OpenAI Responses API, so the API key stays out of frontend code. FastAPI interactive API docs are available at `http://localhost:3000/docs`.

## What Is Built

- Search page for choosing one of 50 dummy cyber submissions.
- Submission Work Queue on the search page with ready/review/referral counts, average quote readiness, top queue items, broker context, and next action.
- Add Submission intake panel on the search page. It supports manual entry, pasted submission-form text extraction, or multi-document automatic intake from uploaded `.txt`/`.pdf` files, tracks required documents to upload, saves intake status, previews inferred downstream checks, then creates a new submission folder and starter records only after underwriter confirmation.
- Full-window chat workspace with chat history, documents, file selection, Auto selection, document upload, and document preview.
- Guide editor beside the model badge. Guide items are sent as system-level instructions on each chat request.
- Notes tab for underwriter-supplied ground-truth context. Notes are sent with each request but are not saved into chat history.
- Details tab with submission summary, timeline, and an expandable underwriting system workbench.
- Submission Update editor for selected metadata cells such as status, industry, revenue, records, employees, technology profile, risk flags, and open questions.
- Clearance Review, Rating and Quote, and External Research surfaces inside the expanded underwriting system.
- Underwriting decision workflow gates for quote readiness, referral, quote approval, and bind readiness.
- Tasks tab with saved underwriting stages, scheduled tasks, a due-date calendar, red task markers, day filtering, due alert dots, and a permanent stage submit lock.
- Expandable Analytics tab with Quote, Bind, What If, and Portfolio sub-tabs, including scenario controls for recalculating probability and portfolio-level dashboard metrics.
- Demo logistic regression model artifacts for quote and bind probability.
- Demo claims system with claims on 30 of 50 companies, plus broker database records linked into the underwriting workbench.
- Local chat actions for broker/account/claims/evidence extraction and workspace navigation.
- Backend retrieval skills that decide from the prompt whether to pull documents, analytics/models, claims, broker profile data, the broker database table, notes, guides, tasks, stages, or underwriting-system context before GPT answers.
- Multi-step information-agent orchestration with planner, tool execution loop, confidence checks, retry expansion, and persisted agent traces.
- Formal agent tool registry with typed input/output contracts, required permissions, read/write classification, citation policy, MCP readiness metadata, and trace metadata.
- Dev Agent Traces view for reviewing persisted planner, tool, confidence, source, and model-response runs.
- Local authorization policy with users, roles, permissions, submission scopes, API middleware enforcement, and an access audit log.
- SQLite-backed local login with an HTTP-only session cookie. The seeded demo admin account is `admin` / `AU-Admin-2026!`.
- Permission-aware agent skills. The information agent filters selected skills before retrieval if the current user lacks the required permission.
- Business deck page at `/business.html` for the executive value story, architecture, local controls, readiness, and roadmap.
- Source citations are returned with retrieved context and shown under chatbot answers.
- Lightweight schema validation covers the main JSON-backed records written by the demo.
- Commercial cyber SOP guidance stored in JSON and used by underwriting-system recommendations and chat retrieval context.

## Business Use Case And Impact Model

This system is a commercial cyber underwriting copilot for submission intake, triage, evidence review, broker follow-up, workflow tracking, and decision support. The core business problem is that underwriters spend a large share of each submission cycle searching documents, reconciling broker emails, checking required evidence, reviewing claim history, applying SOP rules, and explaining model results. The platform brings those activities into one workspace and lets the underwriter ask for the specific data needed in the moment.

Primary users:

- Cyber underwriters who need faster account triage, evidence review, and quote readiness checks.
- Underwriting assistants who collect documents, maintain task status, and prepare broker follow-up.
- Underwriting managers who need consistent SOP application, auditability, and portfolio visibility.
- Broker-facing teams that need clear, targeted requests instead of generic missing-information emails.

High-value business workflows:

- New submission intake: upload multiple documents, extract draft fields, create a submission folder, and preserve source files.
- Evidence completeness review: compare the submission against required cyber documents and SOP metadata.
- Underwriter Q&A: retrieve only relevant documents, notes, guides, claims, broker records, models, tasks, stages, or SOP steps for each prompt.
- Broker follow-up: draft targeted questions tied to missing evidence, control uncertainty, claim issues, and SOP requirements.
- Quote and bind support: show probability outputs, waterfall drivers, What If scenarios, and supplemental cyber risk models.
- Claim-informed underwriting: link historical claim data to the submission and bring it into the underwriting workbench.
- Workflow control: maintain task calendars, stage locks, notes, guides, update history, and submission status.

Expected business impact:

- Lower underwriting touch time per submission by reducing document search, data extraction, and repetitive drafting.
- Faster quote turnaround through automatic intake, evidence checks, and task visibility.
- Better broker experience through precise follow-up questions and clearer missing-information requests.
- More consistent underwriting discipline through SOP-based retrieval and stage/task controls.
- Better risk selection by combining documents, claims, broker context, controls, and model explanations.
- Stronger audit trail because notes, guides, tasks, stages, chat history, source files, model artifacts, and SOP metadata are stored separately.

Illustrative impact calculation:

| Impact lever | Formula | Example assumption | Example annual value |
| --- | --- | --- | --- |
| Underwriting productivity | `annual submissions * hours saved per submission * loaded hourly cost` | `3,000 submissions * 0.75 hours * $95/hour` | `$213,750` |
| Rework reduction | `annual submissions * rework rate reduction * rework hours * loaded hourly cost` | `3,000 * 10% * 0.8 hours * $95/hour` | `$22,800` |
| Bind lift from faster, clearer follow-up | `annual submissions * quote rate * bind-rate lift * average premium * contribution margin` | `3,000 * 55% * 2% * $18,000 * 25%` | `$148,500` |
| Loss leakage reduction | `bound policies * average premium * loss-ratio improvement` | `550 bound policies * $18,000 * 1.0%` | `$99,000` |
| Total modeled annual value | `productivity + rework + margin lift + leakage reduction` | Sum of above | `$484,050` |

Example ROI formula:

```text
ROI = (annual value - annual platform cost) / annual platform cost
```

If annual platform cost were `$120,000`, the illustrative ROI would be:

```text
($484,050 - $120,000) / $120,000 = 303%
```

These numbers are planning assumptions, not measured production results. In a real pilot, the inputs should be replaced with observed baseline and post-launch metrics: average underwriting touch time, quote turnaround, submission-to-quote rate, quote-to-bind rate, rework rate, missing-information cycle count, average premium, contribution margin, and loss ratio movement by cohort.

Current demo limitations:

- Data is stored as JSON files and folders rather than a production database.
- Claims, broker, model, and portfolio records are dummy data for demonstration.
- Logistic regression and GLM artifacts are demo models, not approved production models.
- PDF/text extraction is intentionally simple and should be hardened for production OCR, scanned documents, and document classification.
- Final underwriting decisions should remain human-owned, with model outputs treated as decision support.

## Data Layout

- `data/submissions/<submission_id>/metadata.json` stores submission metadata, document metadata, key facts, timeline, risk flags, and open questions.
- `data/submissions/<submission_id>/...` stores the actual dummy underwriting documents.
- `data/metadata.json` supports search across submissions.
- `data/chat_history/<submission_id>/` stores chat history JSON files.
- `data/guide/<submission_id>.json` stores guide instructions.
- `data/note/<submission_id>.json` stores underwriter notes.
- `data/task/<submission_id>.json` stores scheduled tasks.
- `data/states/<submission_id>.json` stores saved underwriting stage checks.
- `data/decision_workflow/<submission_id>.json` stores optional underwriter gate decisions layered on top of computed quote/referral/approval/bind readiness gates.
- `data/claims/<submission_id>.json` stores dummy claim-system records linked to underwriting.
- `data/brokers/brokers.json` stores reusable broker firm, contact, relationship, and placement metrics.
- `data/underwriting/<submission_id>.json` stores editable underwriting workbench components and claim-review copy.
- `data/agent_skills/underwriting_assistant.json` stores local chat skill definitions for extraction and navigation.
- `backend/services/agent_tool_registry.py` stores the executable tool contract registry used by the centralized agent. `/api/agent-tools` exposes the registry for Dev review.
- `data/security/auth_policy.json` stores local demo users, roles, permissions, and submission scopes.
- `data/security/auth.db` stores local login users and sessions. It is ignored by Git and seeded automatically with the demo admin account.
- `data/audit/access_audit.jsonl` stores runtime API access audit rows. The folder is ignored by Git because audit rows are local runtime artifacts.
- `data/agent_traces/<submission_id>/` stores persisted chat-request traces for planner decisions, retrieval tool execution, confidence checks, retry expansion, and model-response outcomes. The folder is ignored by Git because traces are runtime audit artifacts.
- The portfolio queue, clearance review, rating/quote package, and external research checklist are computed from existing submissions, claims, broker data, evidence metadata, and model files. They are exposed through API routes rather than stored as separate JSON files.
- `data/document_requirements/cyber_required_documents.json` stores the required cyber document checklist used to compare missing vs received submission documents.
- `data/sop/cyber_underwriting_sop.json` stores the demo commercial cyber underwriting SOP used for next-action suggestions.
- `data/sop/metadata.json` stores searchable SOP step metadata used by the centralized information agent to select relevant SOP sections for each prompt.
- `data/intake_status/add_submission_status.json` stores the current Add Submission intake mode, overall status, and document upload checklist.
- `data/intake_uploads/` temporarily stages uploaded intake documents before a new submission id exists. The folder is ignored by Git and cleared for each staged file after the submission is created.
- `data/schema/` documents the local schema registry; the live schema catalog is available at `/api/schemas`.
- `model/quote_prob.json` stores the demo quote probability model.
- `model/bind_prob.json` stores the demo bind probability model.
- `model/cyber_attack_prob.json`, `model/ransomware_prob.json`, `model/data_breach_prob.json`, `model/business_interruption_prob.json`, and `model/claim_severity_prob.json` store supplemental demo GLMs.
- `model/industry_propensity.json` documents the calculated industry benchmark formula. The backend calculates current industry propensity history from `data/submissions` and `data/claims`.
- `model/feature_metadata.json` stores feature definitions, What If control types, and dataset min/max values.
- `tests/sample_submission/` contains sample TXT/PDF upload files for smoke-testing intake and submission uploads.

Each dummy cyber submission includes standardized underwriting documents such as cyber application, ransomware supplement, prior policy, loss runs, financials, IT/security controls, MFA/EDR/backups, incident response plan, vendor assessment, and compliance evidence.

The 50-company demo portfolio can be regenerated with `python3 scripts/expand_demo_portfolio.py`. The generator preserves existing guide/note/task/state files and creates missing context files for new submissions.

Uploaded `.txt` and `.pdf` files are saved into the selected submission folder. The backend extracts readable text, asks the configured GPT model to classify the document into the same metadata shape used by existing files, and falls back to keyword rules if the model is unavailable. The metadata prompt uses a JSON Schema output format so new files keep the same fields as existing underwriting documents.

Documents can also be deleted from the selected submission. Deletion removes the physical file and the matching document entry in `metadata.json`. After either upload or deletion, the UI asks whether to refresh the submission summary and timeline.

The Add Submission form now has a confirmation step before the final record is written. `POST /api/intake/review` previews the downstream intake validation, required evidence gaps, control baseline gaps, broker follow-up inputs, and analytics initialization policy. The preview is deterministic: it uses the entered intake fields, uploaded document metadata, SOP checklist rules, and stored demo model configuration. The final submission is created only when the underwriter chooses Move to Underwriting Agent.

After confirmation, the form creates the same demo data shape as existing submissions: `metadata.json`, optional `intake-form.txt`, staged uploaded intake documents copied into the new submission folder, empty claims, notes, guides, tasks, stage state, chat-history folder, underwriting starter record, saved intake-status record, and a search-index entry. Auto-population currently uses local extraction rules by default so it stays fast even when the API key is invalid; the backend intake service also has an LLM extraction path that can be enabled later.

New Submission is API-driven through `/api/intake/*` routes. The search page loads intake bootstrap data from `/api/intake/bootstrap`, saves checklist state through `/api/intake/status`, drafts from text through `/api/intake/draft`, reads uploaded intake files through `/api/intake/draft-file`, previews confirmation checks through `/api/intake/review`, and creates the final record through `/api/intake/submissions`.

The Dev console is API-driven through `/api/dev/*` routes. `/api/dev/catalog` aggregates the local stores that support the app, including submissions, brokers, claims, SOP, agent skills, models, notes, guides, tasks, stages, underwriting records, schemas, chat history, portfolio queue services, and trace metadata. The page now has separate views for data support, complete submission deletion, broker information, claim information, an agent-skills workflow visual, and agent traces. Deletion still uses `/api/dev/submissions` and `/api/dev/submissions/<submission_id>`. Recent traces are available through `/api/dev/agent-traces`.

## Validation And Tests

The backend uses `backend/services/schema_service.py` as a lightweight schema and validation layer. Write paths for submission metadata, uploaded document metadata, notes, guides, tasks, stages, and decision workflow gates validate records before saving.

Run the current test suite with:

```bash
.venv/bin/python -m unittest discover -s tests
```

Current tests cover schema validation, upload metadata creation, retrieval planning, chat action parsing, task saving, stage locking, analytics scoring, decision workflow gates, portfolio queue routes, clearance review, external research, rating/quote, and Dev trace routes.

## Chat Prompt Behavior

Selected document text is attached to the latest user message only for the active request. It is not saved into chat history. This keeps future turns from repeatedly replaying loaded document text.

Guide instructions are sent with every request as higher-priority operating guidance. Underwriter notes are also sent with every request as ground-truth submission context.

The chat endpoint also recognizes action requests for the selected submission and writes directly to the relevant JSON file:

- `add note: <note text>`
- `add guide: <guide instruction>`
- `add task: <task title> due YYYY-MM-DD`
- `show broker`
- `show broker table`
- `which broker has the highest bind ratio?`
- `compare brokers by data quality`
- `extract account summary`
- `show claims`
- `extract missing evidence`
- `what is the current status`
- `where are we on this submission`
- `update submission status to In Review`
- `open analytics`, `open quote`, `open bind`, `open what if`, `open tasks`, `open note`, or `open underwriting system`

Natural wording such as `Can you add a note for me? The note content should be "..."` is also supported. Task dates support `today`, `tomorrow`, `in N days`, and month-day-year wording such as `May 20, 2026`.

For normal questions, the backend runs a retrieval skill planner before calling GPT. It retrieves only the prompt-relevant workspace data, with account summary context added for broad account/detail questions or generic prompts:

- document/file/control questions pull selected or metadata-matched document text;
- model/analytics/probability questions pull quote, bind, supplemental GLM, and industry propensity results;
- claim/loss questions pull linked dummy claim-system records;
- linked-broker questions pull the current submission broker profile;
- broker-table questions pull all broker database rows from `data/brokers/brokers.json`;
- portfolio/queue/dashboard questions pull the computed submission work queue and portfolio metrics;
- clearance questions pull duplicate-scan, broker, effective-date, evidence, and claim clearance checks;
- rating/quote/premium questions pull the demo rating package, modifiers, premium indication, terms, and subjectivities;
- external-research questions pull the connector-ready research checklist and submission-derived research signals;
- workflow/task/note/guide/stage questions pull the relevant local JSON records;
- appetite/evidence/referral questions pull underwriting-system context.
- current-status questions pull metadata status, appetite, evidence readiness, claims, open tasks, stage progress, and stage lock state.
- SOP/procedure questions use `data/sop/metadata.json` to select relevant SOP steps, then pull the matching SOP goals and templates from `data/sop/cyber_underwriting_sop.json`.

This retrieved context is attached only to the current model request. It is not saved into chat history.

Every chat request with a selected submission now runs through the Centralized Underwriting Information Agent:

- `Multi-step planner`: chooses retrieval skills from the prompt and workspace state.
- `Tool execution loop`: runs local retrieval tools for documents, SOP, claims, broker, models, notes, guides, tasks, stages, and workflow state.
- `Confidence check`: scores whether the selected context has enough coverage, citations, document evidence, SOP matches, and model support.
- `Retry expansion`: if confidence is low, expands the retrieval plan with fallback context such as account summary, underwriting, SOP, document completeness, or analytics.
- `Trace persistence`: saves the request trace under `data/agent_traces/<submission_id>/` and returns a compact trace to the browser process panel.

Agent traces are available through `/api/submissions/<submission_id>/agent-traces` and `/api/submissions/<submission_id>/agent-traces/<trace_id>`.

The Details tab has a Timeline refresh button. Refresh calls the backend to regenerate a structured submission summary and timeline from current metadata and document excerpts. The model request uses a JSON Schema output format with `summary` and `timeline` fields, and the backend falls back to a deterministic local refresh when the model is unavailable.

## Analytics Models

The Analytics tab loads stored model artifacts from:

- `model/quote_prob.json`
- `model/bind_prob.json`

The backend exposes them at:

- `/api/models/quote_prob`
- `/api/models/bind_prob`

The quote and bind files currently contain demo logistic regression coefficients. The UI renders each model as a probability waterfall: average probability, each feature's marginal contribution as a percentage, and current probability. Quote and Bind also include supplemental modeling results backed by stored demo GLMs: cyber attack probability, ransomware probability, data breach probability, business interruption probability, and claim severity probability. Clicking one opens the same waterfall-style model explanation. Industry Propensity opens a benchmark bar chart calculated from the 50 dummy submissions and linked claim files: submission count, companies with claims, claim rate, and average claim severity by industry. Broker placement confidence and evidence confidence remain decision-support metrics. The `What If` sub-tab lets you switch between independent quote and bind scenarios, change feature values, and recalculate probability from the stored model coefficients. The `Portfolio` sub-tab summarizes the current account queue position, industry loss/readiness, and broker pipeline mix from `/api/portfolio/queue`. Numeric controls use dataset min/max values from `model/feature_metadata.json`, show the current submission value at its true position between min and max, and round scenario changes to practical increments while still allowing the dataset floor and cap.

## Underwriting System

The first underwriting-system slice is documented in `docs/underwriting-system-plan.md`. It currently combines submission metadata, broker relationship data, document evidence coverage, dummy claim history, risk flags, and model context into a structured underwriting workbench view. Chat-driven retrieval skills handle extraction, comparison, and navigation requests without showing prompt shortcuts inside the workbench.

The backend exposes:

- `/api/brokers`
- `/api/agent-skills`
- `/api/submissions/<submission_id>/claims`
- `/api/submissions/<submission_id>/underwriting`
- `/api/submissions/<submission_id>/clearance`
- `/api/submissions/<submission_id>/external-research`
- `/api/submissions/<submission_id>/rating-quote`

The underwriting system sits in Details and can be expanded so the workbench uses the full workspace width to the right of the left navigation panel. Analytics uses the same left-edge double-arrow expansion control.

## Backend Layout

- `backend/main.py` defines the FastAPI app, serves the frontend, and exposes API routes.
- `backend/api/routes.py` defines the FastAPI `APIRouter` for health, chat, intake, dev maintenance, submissions, documents, workflow, task, guide, note, model, SOP, broker, claim, and underwriting-system routes.
- `backend/config.py` defines project paths and environment variables.
- `backend/agents/underwriting_graph.py` is the central chat entrypoint. It now prefers the OpenAI Agents SDK runner and falls back to LangGraph or the local single-node Python graph if the SDK is unavailable.
- `backend/agents/openai_agents_sdk.py` builds the OpenAI Agent, attaches the approved local MCP server, and exposes read-side underwriting MCP tools to the model turn.
- `backend/services/submission_service.py` handles submission metadata, documents, and simple generated-PDF text extraction.
- `backend/services/chat_history_service.py` reads and writes chat history.
- `backend/services/guide_service.py` reads and writes guide JSON.
- `backend/services/note_service.py` reads and writes note JSON.
- `backend/services/task_service.py` reads and writes scheduled task JSON.
- `backend/services/stage_state_service.py` reads and writes underwriting stage state JSON.
- `backend/services/broker_service.py` reads broker database records and links them to submissions.
- `backend/services/agent_skill_service.py` reads local chat skill definitions.
- `backend/services/agent_orchestration_service.py` runs the multi-step planner, retrieval tool loop, confidence checks, retry expansion, and trace lifecycle.
- `backend/services/agent_trace_service.py` persists and reads per-submission agent traces.
- `backend/services/claim_service.py` reads dummy claim-system data.
- `backend/services/underwriting_service.py` assembles appetite, broker context, evidence readiness, claim signals, and recommended actions.
- `backend/services/insight_service.py` refreshes structured submission summary and timeline JSON.
- `backend/services/document_tools.py` contains reusable document metadata, selection, and reading tools.
- `backend/services/model_service.py` reads stored analytics models.
- `backend/services/portfolio_workbench_service.py` computes the portfolio queue, clearance review, external research checklist, and rating/quote package.
- `backend/services/openai_service.py` builds shared model instructions and remains the direct Responses API fallback path.

## MCP Tools

The central information agent now has an MCP client path for document retrieval. Approved MCP servers are registered in `data/mcp/servers.json`; the default registry points to `backend.mcp_server` through stdio:

```json
{
  "mcpServers": {
    "agentic-underwriting": {
      "command": ".venv/bin/python",
      "args": ["-m", "backend.mcp_server"],
      "cwd": ".",
      "transport": "stdio",
      "enabled": true,
      "trusted": true
    }
  }
}
```

At runtime, MCP is used in two places:

- `backend/agents/openai_agents_sdk.py` attaches the approved MCP server directly to the OpenAI Agent. The model can call read-side MCP tools natively during the chat turn.
- `backend/services/mcp_client_service.py` loads the same registry for deterministic backend actions and retrieval steps that run before the model call.

The document retrieval path in `backend/services/data_retrieval_service.py` calls MCP tools first:

```text
Auto document selection
-> MCP select_documents
-> MCP read_selected_documents
-> internal Python fallback if MCP is unavailable
```

The OpenAI Agent exposes only read-side MCP tools: `extract_metadata`, `select_documents`, and `read_selected_documents`. Deterministic write actions for notes, guides, and scheduled tasks still go through FastAPI permission checks; those backend actions call their approved MCP tools first, then fall back to direct local Python writes if the MCP transport is unavailable.

Run the FastMCP server:

```bash
npm run mcp
```

Available tools:

- `extract_metadata(submission_id)`: returns submission and file metadata without file text.
- `select_documents(submission_id, prompt, max_documents=6)`: selects relevant files from metadata.
- `read_selected_documents(submission_id, file_names)`: returns metadata and extracted text for chosen files.
- `add_underwriter_note(submission_id, text)`: adds a ground-truth underwriter note.
- `add_guide_instruction(submission_id, text)`: adds a guide instruction.
- `add_scheduled_task(submission_id, title, due_date)`: adds a scheduled task with a `YYYY-MM-DD` due date.

In the web app, turning on `Auto` uses the centralized agent's MCP-enabled document-selection path before each chat request and updates the selected file checkboxes. The central chat response then runs through the OpenAI Agents SDK with the same local MCP server attached, while notes, guides, and tasks continue to use the permission-aware MCP-first / local-fallback backend path.

## Useful API Routes

- `GET /health`
- `GET /docs`
- `GET /api/intake/bootstrap`
- `GET /api/intake/status`
- `PUT /api/intake/status`
- `POST /api/intake/draft`
- `POST /api/intake/draft-file`
- `POST /api/intake/review`
- `POST /api/intake/submissions`
- `GET /api/dev/catalog`
- `GET /api/dev/agent-traces`
- `GET /api/dev/submissions`
- `DELETE /api/dev/submissions/<submission_id>`
- `GET /api/submissions`
- `GET /api/search-metadata`
- `GET /api/portfolio/queue`
- `GET /api/brokers`
- `GET /api/agent-skills`
- `GET /api/submissions/<submission_id>`
- `PUT /api/submissions/<submission_id>/metadata-cells`
- `GET /api/submissions/<submission_id>/files/<file_name>`
- `POST /api/submissions/<submission_id>/files`
- `DELETE /api/submissions/<submission_id>/files/<file_name>`
- `POST /api/submissions/<submission_id>/insights/refresh`
- `GET /api/submissions/<submission_id>/chat-history`
- `POST /api/submissions/<submission_id>/chat-history`
- `GET /api/submissions/<submission_id>/guides`
- `PUT /api/submissions/<submission_id>/guides`
- `GET /api/submissions/<submission_id>/notes`
- `PUT /api/submissions/<submission_id>/notes`
- `GET /api/submissions/<submission_id>/claims`
- `GET /api/submissions/<submission_id>/underwriting`
- `GET /api/submissions/<submission_id>/clearance`
- `GET /api/submissions/<submission_id>/external-research`
- `GET /api/submissions/<submission_id>/rating-quote`
- `GET /api/submissions/<submission_id>/tasks`
- `PUT /api/submissions/<submission_id>/tasks`
- `GET /api/submissions/<submission_id>/states`
- `PUT /api/submissions/<submission_id>/states`
- `POST /api/submissions/<submission_id>/states/submit`
- `POST /api/submissions/<submission_id>/auto-select-documents`
- `GET /api/models/quote_prob`
- `GET /api/models/bind_prob`
- `GET /api/models/cyber_attack_prob`
- `GET /api/models/ransomware_prob`
- `GET /api/models/data_breach_prob`
- `GET /api/models/business_interruption_prob`
- `GET /api/models/claim_severity_prob`
- `GET /api/models/industry_propensity`
- `GET /api/models/feature_metadata`
