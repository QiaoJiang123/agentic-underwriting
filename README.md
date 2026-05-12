# Agentic Underwriting

A local agentic underwriting workspace for cyber submissions. The app combines a Python backend, a full-window underwriting chat UI, submission document handling, guide/note context, Auto document selection, and demo quote/bind analytics models.

## Run Locally

1. Add your OpenAI key and model to `.env`.

   ```bash
   OPENAI_API_KEY=your_key_here
   OPENAI_MODEL=gpt-5.4-nano
   ```

2. Install Python dependencies if you want MCP support.

   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

3. Start the local backend.

   ```bash
   python3 -m backend.main
   ```

   `npm run dev` and `npm start` point to the same Python backend.

4. Open the app.

   ```text
   http://localhost:3000
   ```

The browser sends chat requests to `/api/chat`. The backend calls the OpenAI Responses API, so the API key stays out of frontend code.

## What Is Built

- Search page for choosing a submission.
- Full-window chat workspace with chat history, documents, file selection, Auto selection, document upload, and document preview.
- Guide editor beside the model badge. Guide items are sent as system-level instructions on each chat request.
- Notes tab for underwriter-supplied ground-truth context. Notes are sent with each request but are not saved into chat history.
- Details tab with submission summary and timeline.
- Tasks tab with saved underwriting stages, scheduled tasks, a due-date calendar, red task markers, day filtering, due alert dots, and a permanent stage submit lock.
- Analytics tab with Quote, Bind, and What If sub-tabs, including scenario controls for recalculating probability.
- Demo logistic regression model artifacts for quote and bind probability.

## Data Layout

- `data/submissions/<submission_id>/metadata.json` stores submission metadata, document metadata, key facts, timeline, risk flags, and open questions.
- `data/submissions/<submission_id>/...` stores the actual dummy underwriting documents.
- `data/metadata.json` supports search across submissions.
- `data/chat_history/<submission_id>/` stores chat history JSON files.
- `data/guide/<submission_id>.json` stores guide instructions.
- `data/note/<submission_id>.json` stores underwriter notes.
- `data/task/<submission_id>.json` stores scheduled tasks.
- `data/states/<submission_id>.json` stores saved underwriting stage checks.
- `model/quote_prob.json` stores the demo quote probability model.
- `model/bind_prob.json` stores the demo bind probability model.
- `model/feature_metadata.json` stores feature definitions, What If control types, and dataset min/max values.

Each dummy cyber submission includes standardized underwriting documents such as cyber application, ransomware supplement, prior policy, loss runs, financials, IT/security controls, MFA/EDR/backups, incident response plan, vendor assessment, and compliance evidence.

Uploaded `.txt` and `.pdf` files are saved into the selected submission folder. The backend extracts readable text, asks the configured GPT model to classify the document into the same metadata shape used by existing files, and falls back to keyword rules if the model is unavailable. The metadata prompt uses a JSON Schema output format so new files keep the same fields as existing underwriting documents.

Documents can also be deleted from the selected submission. Deletion removes the physical file and the matching document entry in `metadata.json`. After either upload or deletion, the UI asks whether to refresh the submission summary and timeline.

## Chat Prompt Behavior

Selected document text is attached to the latest user message only for the active request. It is not saved into chat history. This keeps future turns from repeatedly replaying loaded document text.

Guide instructions are sent with every request as higher-priority operating guidance. Underwriter notes are also sent with every request as ground-truth submission context.

The chat endpoint also recognizes action requests for the selected submission and writes directly to the relevant JSON file:

- `add note: <note text>`
- `add guide: <guide instruction>`
- `add task: <task title> due YYYY-MM-DD`

Natural wording such as `Can you add a note for me? The note content should be "..."` is also supported. Task dates support `today`, `tomorrow`, `in N days`, and month-day-year wording such as `May 20, 2026`.

The Details tab has a Timeline refresh button. Refresh calls the backend to regenerate a structured submission summary and timeline from current metadata and document excerpts. The model request uses a JSON Schema output format with `summary` and `timeline` fields, and the backend falls back to a deterministic local refresh when the model is unavailable.

## Analytics Models

The Analytics tab loads stored model artifacts from:

- `model/quote_prob.json`
- `model/bind_prob.json`

The backend exposes them at:

- `/api/models/quote_prob`
- `/api/models/bind_prob`

The quote and bind files currently contain demo logistic regression coefficients. The UI renders each model as a probability waterfall: average probability, each feature's marginal contribution as a percentage, and current probability. The `What If` sub-tab lets you switch between independent quote and bind scenarios, change feature values, and recalculate probability from the stored model coefficients. Numeric controls use dataset min/max values from `model/feature_metadata.json`, show the current submission value at its true position between min and max, and round scenario changes to practical increments while still allowing the dataset floor and cap.

## Backend Layout

- `backend/main.py` serves the frontend and API routes.
- `backend/config.py` defines project paths and environment variables.
- `backend/agents/underwriting_graph.py` runs the underwriting graph. If Python LangGraph is installed, it uses LangGraph; otherwise it falls back to the same single-node Python graph flow.
- `backend/services/submission_service.py` handles submission metadata, documents, and simple generated-PDF text extraction.
- `backend/services/chat_history_service.py` reads and writes chat history.
- `backend/services/guide_service.py` reads and writes guide JSON.
- `backend/services/note_service.py` reads and writes note JSON.
- `backend/services/task_service.py` reads and writes scheduled task JSON.
- `backend/services/stage_state_service.py` reads and writes underwriting stage state JSON.
- `backend/services/insight_service.py` refreshes structured submission summary and timeline JSON.
- `backend/services/document_tools.py` contains reusable document metadata, selection, and reading tools.
- `backend/services/model_service.py` reads stored analytics models.
- `backend/services/openai_service.py` calls the OpenAI Responses API.

## MCP Tools

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

In the web app, turning on `Auto` uses the same document-selection logic before each chat request and updates the selected file checkboxes.

## Useful API Routes

- `GET /health`
- `GET /api/submissions`
- `GET /api/search-metadata`
- `GET /api/submissions/<submission_id>`
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
- `GET /api/submissions/<submission_id>/tasks`
- `PUT /api/submissions/<submission_id>/tasks`
- `GET /api/submissions/<submission_id>/states`
- `PUT /api/submissions/<submission_id>/states`
- `POST /api/submissions/<submission_id>/states/submit`
- `POST /api/submissions/<submission_id>/auto-select-documents`
- `GET /api/models/quote_prob`
- `GET /api/models/bind_prob`
- `GET /api/models/feature_metadata`
