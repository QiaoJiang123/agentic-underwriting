# Agentic Underwriting

A local chatbot wrapper for experimenting with GPT-powered underwriting workflows.

## Run locally

1. Add your OpenAI key to `.env`.

   ```bash
   OPENAI_API_KEY=your_key_here
   OPENAI_MODEL=gpt-5.4-nano
   ```

2. Start the local Python backend.

   ```bash
   python3 -m backend.main
   ```

   The `npm run dev` command also points to the same Python backend if you
   prefer to keep using that shortcut.

3. Open the app.

   ```text
   http://localhost:3000
   ```

The browser sends chat messages to the local Python backend at `/api/chat`.
The backend calls the OpenAI Responses API, so your API key stays out of
frontend code.

## Backend Layout

- `backend/main.py` serves the frontend and API routes.
- `backend/agents/underwriting_graph.py` runs the underwriting graph. If
  Python LangGraph is installed, it uses LangGraph; otherwise it falls back to
  the same single-node Python graph flow.
- `backend/services/submission_service.py` handles submission metadata,
  documents, and simple generated-PDF text extraction.
- `backend/services/guide_service.py` reads and writes `data/guide/*.json`.
- `backend/services/note_service.py` reads and writes `data/note/*.json`.
  Notes are underwriter-supplied ground-truth context sent with each model
  request, but they are not saved into chat history or appended to the visible
  user prompt.
- `backend/services/chat_history_service.py` reads and writes chat history.
- `backend/services/openai_service.py` calls the OpenAI Responses API.
- `backend/services/document_tools.py` contains the reusable document metadata,
  selection, and reading tools used by the MCP server and the Auto selector.

## MCP Tools

Install dependencies into the local virtual environment:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Run the FastMCP server:

```bash
npm run mcp
```

Available tools:

- `extract_metadata(submission_id)`: returns submission and file metadata without file text.
- `select_documents(submission_id, prompt, max_documents=6)`: selects relevant files from metadata.
- `read_selected_documents(submission_id, file_names)`: returns metadata and extracted text for chosen files.

In the web app, checking `Auto` calls the same document-selection logic before
each chat request and updates the selected file checkboxes.
