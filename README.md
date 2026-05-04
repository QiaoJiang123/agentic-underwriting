# Agentic Underwriting

A local chatbot wrapper for experimenting with GPT-powered underwriting workflows.

## Run locally

1. Add your OpenAI key to `.env`.

   ```bash
   OPENAI_API_KEY=your_key_here
   OPENAI_MODEL=gpt-5.4-nano
   ```

2. Start the local server.

   ```bash
   npm run dev
   ```

3. Open the app.

   ```text
   http://localhost:3000
   ```

The browser sends chat messages to the local Node server at `/api/chat`. The
server calls the OpenAI Responses API, so your API key stays out of frontend
code.
