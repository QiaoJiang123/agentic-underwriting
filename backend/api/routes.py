import mimetypes
from importlib.util import find_spec

from fastapi import APIRouter, Body, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse

from backend.agents.underwriting_graph import run_underwriting_graph
from backend.config import OPENAI_API_KEY, OPENAI_MODEL
from backend.services.agent_orchestration_service import (
    finalize_agent_trace,
    persist_action_trace,
    run_information_agent,
)
from backend.services.agent_skill_service import get_agent_skills_record
from backend.services.agent_trace_service import get_agent_trace, list_agent_traces, list_all_agent_traces
from backend.services.agent_tool_registry import get_agent_tool_registry_record
from backend.services.analytics_db_service import get_analytics_db_summary, refresh_analytics_db
from backend.services.audit_service import read_recent_access_audit
from backend.services.auth_service import (
    SESSION_COOKIE_NAME,
    authenticate_login,
    get_auth_policy_summary,
    logout_session,
    require_permission,
)
from backend.services.broker_service import get_broker_database
from backend.services.claim_service import get_claim_record
from backend.services.chat_action_service import run_chat_action
from backend.services.chat_history_service import (
    delete_chat_history,
    get_chat_history_detail,
    list_chat_history,
    save_chat_history,
)
from backend.services.decision_workflow_service import (
    get_decision_workflow_record,
    save_decision_workflow_record,
)
from backend.services.decision_package_service import get_decision_package
from backend.services.dev_console_service import get_dev_console_catalog
from backend.services.document_tools import select_documents_for_prompt, select_documents_with_llm
from backend.services.guide_service import get_guide_record, save_guide_record
from backend.services.insight_service import refresh_submission_insights
from backend.services.intake_status_service import get_intake_status_record, save_intake_status_record
from backend.services.model_service import get_model
from backend.services.model_governance_service import get_model_governance
from backend.services.maintenance_service import cleanup_intake_uploads
from backend.services.note_service import get_note_record, save_note_record
from backend.services.openai_service import call_openai_responses
from backend.services.portfolio_workbench_service import (
    get_clearance_review,
    get_external_research,
    get_portfolio_queue,
    get_rating_quote,
)
from backend.services.schema_service import get_schema_catalog
from backend.services.sop_service import get_sop_metadata_record, get_sop_record
from backend.services.stage_state_service import (
    get_stage_state_record,
    save_stage_state_record,
    submit_stage_state_record,
)
from backend.services.submission_intake_service import (
    build_intake_review,
    create_submission_from_intake,
    draft_submission_from_application_file,
    draft_submission_from_text,
)
from backend.services.submission_service import (
    delete_submission_record,
    get_search_metadata,
    get_submission_detail,
    get_submission_file_path,
    list_submissions,
    update_submission_metadata_cells,
)
from backend.services.task_service import get_task_record, save_task_record
from backend.services.underwriting_service import get_underwriting_system_record
from backend.services.upload_service import delete_submission_file, upload_submission_file


router = APIRouter()


@router.get("/health")
async def health():
    return {
        "ok": True,
        "model": OPENAI_MODEL,
        "backend": "fastapi",
        "openai_agents_sdk_available": is_openai_agents_sdk_available(),
        "langgraph_available": is_langgraph_available(),
    }


@router.post("/api/chat")
async def chat(request: Request, body: dict = Body(default_factory=dict)):
    return build_chat_response(body, getattr(request.state, "auth_context", {}))


@router.get("/api/auth/context")
async def auth_context(request: Request):
    context = getattr(request.state, "auth_context", {})
    return {
        "auth": context,
        "policy": get_auth_policy_summary(),
        "recent_access": read_recent_access_audit(20) if "audit:read" in context.get("permissions", []) else [],
    }


@router.post("/api/auth/login")
async def login(response: Response, body: dict = Body(default_factory=dict)):
    try:
        result = authenticate_login(body.get("username"), body.get("password"))
    except (PermissionError, ValueError) as error:
        raise HTTPException(status_code=401, detail={"error": str(error)}) from error

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=result["session_token"],
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=12 * 60 * 60,
        path="/",
    )
    return {"login": {"ok": True, "expires_at": result["expires_at"], "auth": result["auth"]}}


@router.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    result = logout_session(request.cookies.get(SESSION_COOKIE_NAME))
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"logout": result}


@router.get("/api/submissions")
async def submissions():
    return {"submissions": list_submissions()}


@router.post("/api/submissions")
async def create_submission(body: dict = Body(default_factory=dict)):
    result = create_submission_from_intake(body)
    refresh_analytics_db()
    return {"submission": result}


@router.post("/api/submissions/draft")
async def draft_submission(body: dict = Body(default_factory=dict)):
    return build_submission_draft_response(body)


@router.post("/api/submissions/draft-file")
async def draft_submission_file(file: UploadFile = File(...)):
    return await build_application_form_response(file)


@router.get("/api/search-metadata")
async def search_metadata():
    return get_search_metadata()


@router.get("/api/portfolio/queue")
async def portfolio_queue():
    return {"portfolio": get_portfolio_queue()}


@router.get("/api/analytics-db")
async def analytics_db(refresh: bool = False):
    return {"analytics_db": get_analytics_db_summary(refresh=refresh)}


@router.post("/api/analytics-db/refresh")
async def refresh_analytics_database():
    return {"analytics_db": refresh_analytics_db()}


@router.get("/api/intake/bootstrap")
async def intake_bootstrap():
    return {
        "submissions": get_search_metadata().get("submissions", []),
        "brokers": get_broker_database().get("brokers", []),
        "intake_status": get_intake_status_record(),
    }


@router.get("/api/intake/status")
async def intake_status_v2():
    return {"intake_status": get_intake_status_record()}


@router.put("/api/intake/status")
async def save_intake_status_v2(body: dict = Body(default_factory=dict)):
    return {"intake_status": save_intake_status_record(body)}


@router.post("/api/intake/draft")
async def draft_intake_submission(body: dict = Body(default_factory=dict)):
    return build_submission_draft_response(body)


@router.post("/api/intake/draft-file")
async def draft_intake_submission_file(file: UploadFile = File(...)):
    return await build_application_form_response(file)


@router.post("/api/intake/review")
async def review_intake_submission(body: dict = Body(default_factory=dict)):
    return {"review": build_intake_review(body)}


@router.post("/api/intake/submissions")
async def create_intake_submission(body: dict = Body(default_factory=dict)):
    result = create_submission_from_intake(body)
    refresh_analytics_db()
    return {"submission": result}


@router.get("/api/dev/submissions")
async def dev_submissions():
    submissions = get_search_metadata().get("submissions", [])
    return {"submissions": submissions, "count": len(submissions)}


@router.get("/api/dev/catalog")
async def dev_catalog():
    return get_dev_console_catalog()


@router.get("/api/dev/agent-traces")
async def dev_agent_traces(limit: int = 75):
    return {"agent_traces": list_all_agent_traces(limit)}


@router.post("/api/dev/intake-uploads/cleanup")
async def cleanup_dev_intake_uploads(body: dict = Body(default_factory=dict)):
    return {
        "cleanup": cleanup_intake_uploads(
            max_age_hours=body.get("max_age_hours", 24),
            dry_run=body.get("dry_run", True) is not False,
        )
    }


@router.delete("/api/dev/submissions/{submission_id}")
async def delete_dev_submission(submission_id: str):
    result = delete_submission_record(submission_id)
    refresh_analytics_db()
    return {"delete": result}


@router.get("/api/brokers")
async def brokers():
    return get_broker_database()


@router.get("/api/agent-skills")
async def agent_skills():
    return get_agent_skills_record()


@router.get("/api/agent-tools")
async def agent_tools():
    return get_agent_tool_registry_record()


@router.get("/api/sop")
async def sop():
    return {"sop": get_sop_record(), "metadata": get_sop_metadata_record()}


@router.get("/api/schemas")
async def schemas():
    return {"schemas": get_schema_catalog()}


@router.get("/api/intake-status")
async def intake_status():
    return {"intake_status": get_intake_status_record()}


@router.put("/api/intake-status")
async def save_intake_status(body: dict = Body(default_factory=dict)):
    return {"intake_status": save_intake_status_record(body)}


@router.get("/api/model-governance")
async def model_governance_registry():
    return {"model_governance": get_model_governance()}


@router.get("/api/models/{model_name}/governance")
async def model_governance(model_name: str):
    return {"model_governance": get_model_governance(model_name)}


@router.get("/api/models/{model_name}")
async def model(model_name: str):
    return {"model": get_model(model_name)}


@router.post("/api/submissions/{submission_id}/files")
async def upload_file(submission_id: str, file: UploadFile = File(...)):
    file_bytes = await file.read()
    result = upload_submission_file(
        submission_id=submission_id,
        original_file_name=file.filename or "uploaded-document",
        file_bytes=file_bytes,
        api_key=OPENAI_API_KEY,
        model=OPENAI_MODEL,
    )
    refresh_analytics_db()
    return {"upload": result}


@router.get("/api/submissions/{submission_id}/files/{file_name}")
async def get_file(submission_id: str, file_name: str):
    file_path = get_submission_file_path(submission_id, file_name)
    return FileResponse(
        path=file_path,
        media_type=mimetypes.guess_type(file_path.name)[0] or "application/octet-stream",
        filename=file_path.name,
        content_disposition_type="inline",
        headers={"Cache-Control": "no-store"},
    )


@router.delete("/api/submissions/{submission_id}/files/{file_name}")
async def delete_file(submission_id: str, file_name: str):
    result = delete_submission_file(submission_id, file_name)
    refresh_analytics_db()
    return {"delete": result}


@router.post("/api/submissions/{submission_id}/insights/refresh")
async def refresh_insights(submission_id: str):
    result = refresh_submission_insights(submission_id, OPENAI_API_KEY, OPENAI_MODEL)
    return {"refresh": result}


@router.get("/api/submissions/{submission_id}/claims")
async def claims(submission_id: str):
    return {"claims": get_claim_record(submission_id)}


@router.get("/api/submissions/{submission_id}/underwriting")
async def underwriting(submission_id: str):
    return {"underwriting_system": get_underwriting_system_record(submission_id)}


@router.get("/api/submissions/{submission_id}/clearance")
async def clearance(submission_id: str):
    return {"clearance": get_clearance_review(submission_id)}


@router.get("/api/submissions/{submission_id}/external-research")
async def external_research(submission_id: str):
    return {"external_research": get_external_research(submission_id)}


@router.get("/api/submissions/{submission_id}/rating-quote")
async def rating_quote(submission_id: str):
    return {"rating_quote": get_rating_quote(submission_id)}


@router.get("/api/submissions/{submission_id}/decision-workflow")
async def decision_workflow(submission_id: str):
    return {"decision_workflow": get_decision_workflow_record(submission_id)}


@router.get("/api/submissions/{submission_id}/decision-package")
async def decision_package(submission_id: str, package_type: str = "review"):
    return {"decision_package": get_decision_package(submission_id, package_type)}


@router.put("/api/submissions/{submission_id}/decision-workflow")
async def save_decision_workflow(submission_id: str, body: dict = Body(default_factory=dict)):
    return {"decision_workflow": save_decision_workflow_record(submission_id, body.get("decisions", []))}


@router.put("/api/submissions/{submission_id}/metadata-cells")
async def metadata_cells(submission_id: str, body: dict = Body(default_factory=dict)):
    result = update_submission_metadata_cells(submission_id, body)
    refresh_analytics_db()
    return {"submission": result}


@router.get("/api/submissions/{submission_id}/chat-history")
async def chat_history(submission_id: str):
    return {"chat_history": list_chat_history(submission_id)}


@router.post("/api/submissions/{submission_id}/chat-history")
async def save_chat(submission_id: str, body: dict = Body(default_factory=dict)):
    return {"chat_history": save_chat_history(submission_id, body)}


@router.get("/api/submissions/{submission_id}/chat-history/{history_id}")
async def chat_history_detail(submission_id: str, history_id: str):
    return {"chat_history": get_chat_history_detail(submission_id, history_id)}


@router.delete("/api/submissions/{submission_id}/chat-history/{history_id}")
async def delete_chat(submission_id: str, history_id: str):
    return {"chat_history": delete_chat_history(submission_id, history_id)}


@router.get("/api/submissions/{submission_id}/agent-traces")
async def agent_traces(submission_id: str):
    return {"agent_traces": list_agent_traces(submission_id)}


@router.get("/api/submissions/{submission_id}/agent-traces/{trace_id}")
async def agent_trace_detail(submission_id: str, trace_id: str):
    return {"agent_trace": get_agent_trace(submission_id, trace_id)}


@router.get("/api/submissions/{submission_id}/guides")
async def guides(submission_id: str):
    return {"guide": get_guide_record(submission_id)}


@router.put("/api/submissions/{submission_id}/guides")
async def save_guides(submission_id: str, body: dict = Body(default_factory=dict)):
    return {"guide": save_guide_record(submission_id, body.get("guides", []))}


@router.get("/api/submissions/{submission_id}/notes")
async def notes(submission_id: str):
    return {"note": get_note_record(submission_id)}


@router.put("/api/submissions/{submission_id}/notes")
async def save_notes(submission_id: str, body: dict = Body(default_factory=dict)):
    return {"note": save_note_record(submission_id, body.get("notes", []))}


@router.get("/api/submissions/{submission_id}/tasks")
async def tasks(submission_id: str):
    return {"task": get_task_record(submission_id)}


@router.put("/api/submissions/{submission_id}/tasks")
async def save_tasks(submission_id: str, body: dict = Body(default_factory=dict)):
    return {"task": save_task_record(submission_id, body.get("tasks", []))}


@router.get("/api/submissions/{submission_id}/states")
async def states(submission_id: str):
    return {"state": get_stage_state_record(submission_id)}


@router.put("/api/submissions/{submission_id}/states")
async def save_states(submission_id: str, body: dict = Body(default_factory=dict)):
    return {"state": save_stage_state_record(submission_id, body.get("stages", []))}


@router.post("/api/submissions/{submission_id}/states/submit")
async def submit_states(submission_id: str, body: dict = Body(default_factory=dict)):
    return {"state": submit_stage_state_record(submission_id, body.get("stages", []))}


@router.post("/api/submissions/{submission_id}/auto-select-documents")
async def auto_select_documents(submission_id: str, body: dict = Body(default_factory=dict)):
    if body.get("use_llm") is False:
        document_selection = select_documents_for_prompt(
            submission_id=submission_id,
            prompt=str(body.get("prompt", "")),
            max_documents=int(body.get("max_documents", 6) or 6),
        )
    else:
        document_selection = select_documents_with_llm(
            submission_id=submission_id,
            prompt=str(body.get("prompt", "")),
            api_key=OPENAI_API_KEY,
            model=OPENAI_MODEL,
            max_documents=int(body.get("max_documents", 6) or 6),
        )
    return {"document_selection": document_selection}


@router.delete("/api/submissions/{submission_id}")
async def delete_submission(submission_id: str):
    result = delete_submission_record(submission_id)
    refresh_analytics_db()
    return {"delete": result}


@router.get("/api/submissions/{submission_id}")
async def submission_detail(submission_id: str):
    return get_submission_detail(submission_id)


def build_submission_draft_response(body):
    use_llm = body.get("use_llm") is True
    draft = draft_submission_from_text(
        str(body.get("intake_text", "")),
        OPENAI_API_KEY if use_llm else "",
        OPENAI_MODEL if use_llm else "",
    )
    return {"draft": draft}


async def build_application_form_response(file):
    file_bytes = await file.read()
    result = draft_submission_from_application_file(
        file_name=file.filename or "application-form",
        file_bytes=file_bytes,
        api_key="",
        model="",
    )
    return {"application_form": result}


def build_chat_response(body, auth_context=None):
    messages = body.get("messages") if isinstance(body.get("messages"), list) else []
    submission_id = str(body.get("submission_id", "")).strip()
    user_prompt = str(body.get("user_prompt", "")).strip()
    guide_instructions = [
        str(guide).strip()
        for guide in body.get("guides", [])
        if str(guide or "").strip()
    ]
    underwriter_notes = [
        str(note).strip()
        for note in body.get("underwriter_notes", [])
        if str(note or "").strip()
    ]
    selected_files = [
        str(file_name).strip()
        for file_name in body.get("selected_files", [])
        if str(file_name or "").strip()
    ] if isinstance(body.get("selected_files"), list) else []
    file_selection_mode = str(body.get("file_selection_mode") or "auto").strip()

    if not messages:
        raise HTTPException(status_code=400, detail={"error": "No messages were provided."})

    if submission_id and auth_context:
        try:
            require_permission(auth_context, "submission:read", submission_id)
        except PermissionError as error:
            raise HTTPException(status_code=403, detail={"error": str(error)}) from error

    if submission_id and user_prompt:
        action_result = run_chat_action(submission_id, user_prompt)
        if action_result:
            if chat_action_requires_write(action_result):
                try:
                    require_permission(auth_context, "submission:write", submission_id)
                except PermissionError as error:
                    raise HTTPException(status_code=403, detail={"error": str(error)}) from error
            agent_trace = persist_action_trace(submission_id, user_prompt, action_result)
            return {
                "reply": action_result["reply"],
                "model": "local-action",
                "id": None,
                "framework": "python-action",
                "actions": [action_result],
                "agent_trace": agent_trace,
            }

    if not OPENAI_API_KEY or OPENAI_API_KEY == "replace_with_your_openai_api_key":
        raise HTTPException(
            status_code=400,
            detail={"error": "Missing OPENAI_API_KEY. Add your key to .env, then restart the server."},
        )

    model_input = [
        {
            "role": "assistant" if message.get("role") == "assistant" else "user",
            "content": str(message.get("content", "")),
        }
        for message in messages
        if isinstance(message, dict)
    ]
    orchestration_result = (
        run_information_agent(
            submission_id=submission_id,
            prompt=user_prompt,
            selected_files=selected_files,
            file_selection_mode=file_selection_mode,
            max_documents=6,
            auth_context=auth_context,
            conversation_messages=model_input,
        )
        if submission_id and user_prompt
        else {"retrieval": {"plan": [], "context": "", "sources": [], "selection": {}}, "trace": None, "record": None}
    )
    retrieval_result = orchestration_result["retrieval"]
    append_context_to_latest_user_message(model_input, retrieval_result.get("context", ""))

    try:
        graph_result = run_underwriting_graph(
            messages=model_input,
            model=OPENAI_MODEL,
            api_key=OPENAI_API_KEY,
            guide_instructions=guide_instructions,
            underwriter_notes=underwriter_notes,
            call_openai=call_openai_responses,
        )
    except Exception as error:
        finalize_agent_trace(
            orchestration_result.get("record"),
            status="model_error",
            model=OPENAI_MODEL,
            error=error,
        )
        message = str(error) or "OpenAI request failed"
        if "incorrect api key" in message.lower():
            message = (
                f"{message} The local server is using the key loaded at startup. "
                "Replace OPENAI_API_KEY in .env with a newly generated key, then restart the server."
            )
        raise HTTPException(status_code=502, detail={"error": message}) from error

    agent_trace = finalize_agent_trace(
        orchestration_result.get("record"),
        status="completed",
        model=OPENAI_MODEL,
        response_id=graph_result.get("response_id"),
    )

    return {
        "reply": graph_result.get("reply"),
        "model": OPENAI_MODEL,
        "id": graph_result.get("response_id"),
        "framework": graph_result.get("framework")
        or ("python-langgraph" if is_langgraph_available() else "python-graph-fallback"),
        "agent_trace": agent_trace or orchestration_result.get("trace"),
        "retrieval": {
            "plan": retrieval_result.get("plan", []),
            "sources": retrieval_result.get("sources", []),
            "selection": retrieval_result.get("selection", {}),
        },
    }


def is_langgraph_available():
    return find_spec("langgraph") is not None


def is_openai_agents_sdk_available():
    return find_spec("agents") is not None


def append_context_to_latest_user_message(messages, context):
    context = str(context or "").strip()
    if not context:
        return

    for index in range(len(messages) - 1, -1, -1):
        if messages[index].get("role") == "user":
            messages[index]["content"] = "\n".join(
                [
                    str(messages[index].get("content", "")),
                    "",
                    context,
                ]
            )
            return


def chat_action_requires_write(action_result):
    action_type = str((action_result or {}).get("type") or "").lower()
    return action_type in {
        "note",
        "guide",
        "task",
        "update_submission",
        "stage",
        "stages",
        "workflow",
        "decision",
    }
