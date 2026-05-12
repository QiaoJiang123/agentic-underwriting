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
- Full-window chat workspace with chat history, documents, file selection, Auto selection, and document preview.
- Guide editor beside the model badge. Guide items are sent as system-level instructions on each chat request.
- Notes tab for underwriter-supplied ground-truth context. Notes are sent with each request but are not saved into chat history.
- Details tab with submission summary and timeline.
- Tasks tab with underwriting stages, scheduled tasks, due-date calendar, and due alert dots.
- Analytics tab with Quote, Bind, and What If sub-tabs, including scenario controls for recalculating probability.
- Demo logistic regression model artifacts for quote and bind probability.

## Data Layout

- `data/submissions/<submission_id>/metadata.json` stores submission metadata, document metadata, key facts, timeline, risk flags, and open questions.
- `data/submissions/<submission_id>/...` stores the actual dummy underwriting documents.
- `data/metadata.json` supports search across submissions.
- `data/chat_history/<submission_id>/` stores chat history JSON files.
- `data/guide/<submission_id>.json` stores guide instructions.
- `data/note/<submission_id>.json` stores underwriter notes.
- `data/follow_up/<submission_id>.json` stores scheduled tasks.
- `model/quote_prob.json` stores the demo quote probability model.
- `model/bind_prob.json` stores the demo bind probability model.

Each dummy cyber submission includes standardized underwriting documents such as cyber application, ransomware supplement, prior policy, loss runs, financials, IT/security controls, MFA/EDR/backups, incident response plan, vendor assessment, and compliance evidence.

## Chat Prompt Behavior

Selected document text is attached to the latest user message only for the active request. It is not saved into chat history. This keeps future turns from repeatedly replaying loaded document text.

Guide instructions are sent with every request as higher-priority operating guidance. Underwriter notes are also sent with every request as ground-truth submission context.

## Analytics Models

The Analytics tab loads stored model artifacts from:

- `model/quote_prob.json`
- `model/bind_prob.json`

The backend exposes them at:

- `/api/models/quote_prob`
- `/api/models/bind_prob`

Both files currently contain demo logistic regression coefficients. The UI renders each model as a probability waterfall: average probability, each feature's marginal contribution as a percentage, and current probability. The `What If` sub-tab lets you switch between quote and bind scenarios, change feature values, and recalculate probability from the stored model coefficients.

## Backend Layout

- `backend/main.py` serves the frontend and API routes.
- `backend/config.py` defines project paths and environment variables.
- `backend/agents/underwriting_graph.py` runs the underwriting graph. If Python LangGraph is installed, it uses LangGraph; otherwise it falls back to the same single-node Python graph flow.
- `backend/services/submission_service.py` handles submission metadata, documents, and simple generated-PDF text extraction.
- `backend/services/chat_history_service.py` reads and writes chat history.
- `backend/services/guide_service.py` reads and writes guide JSON.
- `backend/services/note_service.py` reads and writes note JSON.
- `backend/services/follow_up_service.py` reads and writes scheduled task JSON.
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

In the web app, turning on `Auto` uses the same document-selection logic before each chat request and updates the selected file checkboxes.

## Useful API Routes

- `GET /health`
- `GET /api/submissions`
- `GET /api/search-metadata`
- `GET /api/submissions/<submission_id>`
- `GET /api/submissions/<submission_id>/files/<file_name>`
- `GET /api/submissions/<submission_id>/chat-history`
- `POST /api/submissions/<submission_id>/chat-history`
- `GET /api/submissions/<submission_id>/guides`
- `PUT /api/submissions/<submission_id>/guides`
- `GET /api/submissions/<submission_id>/notes`
- `PUT /api/submissions/<submission_id>/notes`
- `GET /api/submissions/<submission_id>/follow-ups`
- `PUT /api/submissions/<submission_id>/follow-ups`
- `POST /api/submissions/<submission_id>/auto-select-documents`
- `GET /api/models/quote_prob`
- `GET /api/models/bind_prob`
