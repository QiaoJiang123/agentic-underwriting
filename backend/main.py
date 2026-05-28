import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.api.routes import is_langgraph_available, router
from backend.config import OPENAI_MODEL, PORT, PUBLIC_DIR
from backend.services.audit_service import record_access_audit
from backend.services.auth_service import authorize_request, init_auth_database


def create_app():
    init_auth_database()
    app = FastAPI(
        title="Agentic Underwriting API",
        version="0.2.0",
        description="Local FastAPI backend for the agentic commercial cyber underwriting demo.",
    )
    register_exception_handlers(app)
    app.middleware("http")(authorize_and_audit_request)
    app.middleware("http")(add_no_store_header)
    app.include_router(router)
    app.mount("/", StaticFiles(directory=PUBLIC_DIR, html=True), name="public")
    return app


def register_exception_handlers(app):
    app.add_exception_handler(ValueError, handle_value_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(FileNotFoundError, handle_file_not_found)
    app.add_exception_handler(Exception, handle_unexpected_error)


async def handle_value_error(_request, error):
    return JSONResponse(status_code=400, content={"error": str(error)})


async def handle_http_exception(_request, error):
    detail = error.detail
    if isinstance(detail, dict) and "error" in detail:
        return JSONResponse(status_code=error.status_code, content=detail)
    return JSONResponse(status_code=error.status_code, content={"error": str(detail)})


async def handle_file_not_found(_request, error):
    return JSONResponse(status_code=404, content={"error": str(error)})


async def handle_unexpected_error(_request, error):
    print(error)
    return JSONResponse(status_code=500, content={"error": "Unexpected server error"})


async def add_no_store_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    return response


async def authorize_and_audit_request(request: Request, call_next):
    if not request.url.path.startswith("/api/"):
        return await call_next(request)

    decision = authorize_request(request)
    context = decision.get("context", {})
    request.state.auth_context = context

    if not decision.get("allowed"):
        record_access_audit(make_audit_record(request, decision, 403, "denied"))
        return JSONResponse(
            status_code=403,
            content={
                "error": decision.get("reason", "Access denied."),
                "auth": {
                    "user_id": context.get("user_id"),
                    "role": context.get("role"),
                    "required_permission": decision.get("permission"),
                    "submission_id": decision.get("submission_id"),
                },
            },
        )

    response = await call_next(request)
    response.headers["X-AU-User"] = str(context.get("user_id") or "")
    response.headers["X-AU-Role"] = str(context.get("role") or "")
    record_access_audit(make_audit_record(request, decision, response.status_code, "allowed"))
    return response


def make_audit_record(request, decision, status_code, result):
    context = decision.get("context", {})
    return {
        "result": result,
        "status_code": status_code,
        "method": request.method,
        "path": request.url.path,
        "user_id": context.get("user_id"),
        "role": context.get("role"),
        "team": context.get("team"),
        "permission": decision.get("permission"),
        "submission_id": decision.get("submission_id"),
        "reason": decision.get("reason"),
    }


app = create_app()


def main():
    print(f"Agentic underwriting FastAPI backend is running at http://localhost:{PORT}")
    print(f"FastAPI docs: http://localhost:{PORT}/docs")
    print(f"Using model: {OPENAI_MODEL}")
    print(f"LangGraph Python available: {is_langgraph_available()}")
    uvicorn.run(app, host="0.0.0.0", port=PORT, reload=False)


if __name__ == "__main__":
    main()
