import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.util import find_spec
from pathlib import Path
from urllib.parse import unquote, urlparse

from backend.agents.underwriting_graph import run_underwriting_graph
from backend.config import OPENAI_API_KEY, OPENAI_MODEL, PORT, PUBLIC_DIR
from backend.services.chat_history_service import (
    get_chat_history_detail,
    list_chat_history,
    save_chat_history,
)
from backend.services.guide_service import get_guide_record, save_guide_record
from backend.services.openai_service import call_openai_responses
from backend.services.submission_service import (
    get_search_metadata,
    get_submission_detail,
    get_submission_file_path,
    list_submissions,
)


JSON_HEADERS = {"Content-Type": "application/json; charset=utf-8"}
TEXT_HEADERS = {"Content-Type": "text/plain; charset=utf-8"}


class UnderwritingRequestHandler(BaseHTTPRequestHandler):
    server_version = "AgenticUnderwritingPython/0.1"

    def do_GET(self):
        self.route_request("GET")

    def do_POST(self):
        self.route_request("POST")

    def do_PUT(self):
        self.route_request("PUT")

    def route_request(self, method):
        try:
            path = urlparse(self.path).path

            if method == "GET" and path == "/health":
                return self.send_json(
                    200,
                    {
                        "ok": True,
                        "model": OPENAI_MODEL,
                        "backend": "python",
                        "langgraph_available": is_langgraph_available(),
                    },
                )

            if method == "POST" and path == "/api/chat":
                return self.handle_chat()

            if method == "GET" and path == "/api/submissions":
                return self.send_json(200, {"submissions": list_submissions()})

            if method == "GET" and path == "/api/search-metadata":
                return self.send_json(200, get_search_metadata())

            if path.startswith("/api/submissions/"):
                return self.handle_submission_route(method, path)

            if method == "GET":
                return self.serve_static(path)

            return self.send_json(405, {"error": "Method not allowed"})
        except ValueError as error:
            return self.send_json(400, {"error": str(error)})
        except FileNotFoundError as error:
            return self.send_json(404, {"error": str(error)})
        except Exception as error:
            print(error)
            return self.send_json(500, {"error": "Unexpected server error"})

    def handle_submission_route(self, method, path):
        remainder = path.removeprefix("/api/submissions/")

        if "/files/" in remainder and method == "GET":
            submission_id, file_name = remainder.split("/files/", 1)
            return self.serve_submission_file(unquote(submission_id), unquote(file_name))

        if "/chat-history/" in remainder and method == "GET":
            submission_id, history_id = remainder.split("/chat-history/", 1)
            record = get_chat_history_detail(unquote(submission_id), unquote(history_id))
            return self.send_json(200, {"chat_history": record})

        if remainder.endswith("/chat-history"):
            submission_id = unquote(remainder.removesuffix("/chat-history"))
            if method == "GET":
                return self.send_json(200, {"chat_history": list_chat_history(submission_id)})
            if method == "POST":
                return self.send_json(200, {"chat_history": save_chat_history(submission_id, self.read_json())})

        if remainder.endswith("/guides"):
            submission_id = unquote(remainder.removesuffix("/guides"))
            if method == "GET":
                return self.send_json(200, {"guide": get_guide_record(submission_id)})
            if method == "PUT":
                body = self.read_json()
                return self.send_json(200, {"guide": save_guide_record(submission_id, body.get("guides", []))})

        if method == "GET":
            submission_id = unquote(remainder)
            return self.send_json(200, get_submission_detail(submission_id))

        return self.send_json(405, {"error": "Method not allowed"})

    def handle_chat(self):
        if not OPENAI_API_KEY or OPENAI_API_KEY == "replace_with_your_openai_api_key":
            return self.send_json(
                400,
                {
                    "error": "Missing OPENAI_API_KEY. Add your key to .env, then restart the server."
                },
            )

        body = self.read_json()
        messages = body.get("messages") if isinstance(body.get("messages"), list) else []
        guide_instructions = [
            str(guide).strip()
            for guide in body.get("guides", [])
            if str(guide or "").strip()
        ]

        if not messages:
            return self.send_json(400, {"error": "No messages were provided."})

        model_input = [
            {
                "role": "assistant" if message.get("role") == "assistant" else "user",
                "content": str(message.get("content", "")),
            }
            for message in messages
            if isinstance(message, dict)
        ]

        try:
            graph_result = run_underwriting_graph(
                messages=model_input,
                model=OPENAI_MODEL,
                api_key=OPENAI_API_KEY,
                guide_instructions=guide_instructions,
                call_openai=call_openai_responses,
            )
        except Exception as error:
            message = str(error) or "OpenAI request failed"
            if "incorrect api key" in message.lower():
                message = (
                    f"{message} The local server is using the key loaded at startup. "
                    "Replace OPENAI_API_KEY in .env with a newly generated key, then restart the server."
                )
            return self.send_json(502, {"error": message})

        return self.send_json(
            200,
            {
                "reply": graph_result.get("reply"),
                "model": OPENAI_MODEL,
                "id": graph_result.get("response_id"),
                "framework": "python-langgraph" if is_langgraph_available() else "python-graph-fallback",
            },
        )

    def serve_submission_file(self, submission_id, file_name):
        file_path = get_submission_file_path(submission_id, file_name)
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        data = Path(file_path).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'inline; filename="{file_path.name}"')
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def serve_static(self, path):
        url_path = "/index.html" if path == "/" else path
        decoded_path = unquote(url_path).lstrip("/")
        file_path = (PUBLIC_DIR / decoded_path).resolve()

        try:
            file_path.relative_to(PUBLIC_DIR.resolve())
        except ValueError:
            return self.send_text(403, "Forbidden")

        if not file_path.exists() or not file_path.is_file():
            return self.send_text(404, "Not found")

        data = file_path.read_bytes()
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        if file_path.suffix in {".html", ".css", ".js", ".json", ".txt"}:
            content_type = f"{content_type}; charset=utf-8"

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def read_json(self):
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        if content_length > 1_000_000:
            raise ValueError("Request body is too large.")

        raw_body = self.rfile.read(content_length) if content_length else b""
        if not raw_body:
            return {}

        try:
            return json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError("Invalid JSON body.") from error

    def send_json(self, status_code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        for key, value in JSON_HEADERS.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, status_code, text):
        body = str(text).encode("utf-8")
        self.send_response(status_code)
        for key, value in TEXT_HEADERS.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print("%s - %s" % (self.address_string(), format % args))


def is_langgraph_available():
    return find_spec("langgraph") is not None


def main():
    server = ThreadingHTTPServer(("", PORT), UnderwritingRequestHandler)
    print(f"Agentic underwriting Python backend is running at http://localhost:{PORT}")
    print(f"Using model: {OPENAI_MODEL}")
    print(f"LangGraph Python available: {is_langgraph_available()}")
    server.serve_forever()


if __name__ == "__main__":
    main()

