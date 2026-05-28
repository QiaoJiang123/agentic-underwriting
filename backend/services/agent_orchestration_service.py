from datetime import datetime, timezone

from backend.services.agent_trace_service import new_trace_id, save_agent_trace
from backend.services.agent_tool_registry import (
    get_action_tool,
    get_agent_tool,
    tool_contracts_for_plan,
    tool_permissions_for_plan,
)
from backend.services.auth_service import require_permission
from backend.services.data_retrieval_service import (
    CENTRAL_INFORMATION_AGENT,
    build_data_retrieval_context,
    dedupe,
    select_information_for_prompt,
)


MIN_CONFIDENCE = 0.72
MAX_ATTEMPTS = 2


def run_information_agent(
    submission_id,
    prompt,
    selected_files=None,
    file_selection_mode="auto",
    max_documents=6,
    auth_context=None,
    conversation_messages=None,
):
    trace = make_base_trace(submission_id, prompt)
    if auth_context:
        require_permission(auth_context, "submission:read", submission_id)
        trace["auth_context"] = {
            "user_id": auth_context.get("user_id"),
            "role": auth_context.get("role"),
            "team": auth_context.get("team"),
        }
    selected_files = selected_files if isinstance(selected_files, list) else []
    initial_plan = select_information_for_prompt(
        str(prompt or ""),
        conversation_messages=conversation_messages,
    )
    add_trace_step(
        trace,
        "planner",
        "Multi-step planner",
        f"Selected {format_skill_list(initial_plan)} from the prompt and workspace state.",
        data={
            "selected_skills": initial_plan,
            "file_selection_mode": file_selection_mode,
            "skill_permissions": tool_permissions_for_plan(initial_plan),
            "tool_contracts": tool_contracts_for_plan(initial_plan, compact=True),
        },
    )

    retrieval_result = {"plan": [], "context": "", "sources": [], "selection": {}}
    current_plan = initial_plan
    final_check = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        retrieval_result = build_data_retrieval_context(
            submission_id=submission_id,
            prompt=prompt,
            selected_files=selected_files,
            file_selection_mode=file_selection_mode,
            max_documents=max_documents,
            plan_override=current_plan,
            auth_context=auth_context,
            conversation_messages=conversation_messages,
        )
        tool_steps = build_tool_execution_steps(retrieval_result, current_plan)
        trace.setdefault("tool_executions", []).extend(tool_steps)
        add_trace_step(
            trace,
            "tool_execution",
            "Tool execution loop",
            summarize_tool_steps(tool_steps),
            data={"attempt": attempt, "tools": tool_steps},
        )

        final_check = evaluate_retrieval_confidence(retrieval_result, current_plan, file_selection_mode)
        trace.setdefault("confidence_checks", []).append(final_check)
        add_trace_step(
            trace,
            "confidence",
            "Confidence check",
            f"{final_check['label']} confidence ({round(final_check['score'] * 100)}%). {final_check['summary']}",
            data=final_check,
        )

        if final_check["score"] >= MIN_CONFIDENCE:
            break

        retry_plan = expand_plan_for_retry(current_plan, prompt, final_check)
        if attempt >= MAX_ATTEMPTS or retry_plan == current_plan:
            break

        add_trace_step(
            trace,
            "retry",
            "Retry expansion",
            f"Expanded plan from {format_skill_list(current_plan)} to {format_skill_list(retry_plan)}.",
            data={"from": current_plan, "to": retry_plan, "reason": final_check.get("issues", [])},
        )
        current_plan = retry_plan

    trace["status"] = "context_ready"
    trace["attempt_count"] = len(trace.get("confidence_checks", []))
    trace["confidence"] = final_check or {"score": 0, "label": "low", "summary": "No confidence check was run.", "issues": []}
    trace["selected_skills"] = retrieval_result.get("plan", [])
    trace["source_count"] = len(retrieval_result.get("sources", []))
    trace["selected_sources"] = retrieval_result.get("selection", {}).get("selected_sources", {})

    add_trace_step(
        trace,
        "trace",
        "Agent trace persistence",
        f"Saved trace {trace['trace_id']} for audit and debugging.",
        data={"trace_id": trace["trace_id"]},
    )
    save_agent_trace(trace)

    selection = retrieval_result.setdefault("selection", {})
    selection["trace_id"] = trace["trace_id"]
    selection["attempt_count"] = trace["attempt_count"]
    selection["confidence"] = trace["confidence"]

    return {
        "retrieval": retrieval_result,
        "trace": summarize_trace_for_response(trace),
        "record": trace,
    }


def persist_action_trace(submission_id, prompt, action_result):
    trace = make_base_trace(submission_id, prompt)
    action_type = action_result.get("type", "action") if isinstance(action_result, dict) else "action"
    action_tool = get_action_tool(action_type, compact=True)
    add_trace_step(
        trace,
        "planner",
        "Multi-step planner",
        f"Detected a direct workspace action: {format_skill(action_type)}.",
        data={"action_type": action_type, "tool_contract": action_tool},
    )
    add_trace_step(
        trace,
        "tool_execution",
        "Tool execution loop",
        f"Executed local action tool for {format_skill(action_type)}.",
        data={"action": action_result},
    )
    trace["confidence"] = {
        "score": 1,
        "label": "high",
        "summary": "The prompt matched a deterministic local workspace action.",
        "issues": [],
    }
    trace["attempt_count"] = 1
    trace["status"] = "action_completed"
    add_trace_step(
        trace,
        "confidence",
        "Confidence check",
        "High confidence (100%). Deterministic action completed.",
        data=trace["confidence"],
    )
    add_trace_step(
        trace,
        "trace",
        "Agent trace persistence",
        f"Saved trace {trace['trace_id']} for audit and debugging.",
        data={"trace_id": trace["trace_id"]},
    )
    save_agent_trace(trace)
    return summarize_trace_for_response(trace)


def finalize_agent_trace(trace, status, model=None, response_id=None, error=None):
    if not trace:
        return None

    trace["status"] = status
    trace["model"] = model
    trace["response_id"] = response_id
    if error:
        trace["error"] = str(error)
        add_trace_step(
            trace,
            "model",
            "Model response",
            str(error),
            status="error",
            data={"model": model},
        )
    else:
        add_trace_step(
            trace,
            "model",
            "Model response",
            f"Completed response with {model or 'configured model'}.",
            data={"model": model, "response_id": response_id},
        )
    save_agent_trace(trace)
    return summarize_trace_for_response(trace)


def make_base_trace(submission_id, prompt):
    now = utc_now()
    return {
        "trace_id": new_trace_id(),
        "submission_id": submission_id,
        "agent": CENTRAL_INFORMATION_AGENT,
        "status": "started",
        "created_at": now,
        "updated_at": now,
        "prompt_preview": str(prompt or "").strip()[:280],
        "steps": [],
        "tool_executions": [],
        "confidence_checks": [],
    }


def add_trace_step(trace, phase, title, detail, status="done", data=None):
    step = {
        "phase": phase,
        "title": title,
        "status": status,
        "detail": detail,
        "created_at": utc_now(),
    }
    if data is not None:
        step["data"] = data
    trace.setdefault("steps", []).append(step)
    return step


def build_tool_execution_steps(retrieval_result, plan):
    sources = retrieval_result.get("sources", [])
    selection = retrieval_result.get("selection", {})
    selected_sources = selection.get("selected_sources", {})
    steps = []
    for skill in plan:
        tool_contract = get_agent_tool(skill, compact=True) or {}
        source_count = selected_sources.get(skill, 0)
        detail = f"Read {source_count} source(s)." if source_count else "No source records were returned."
        if skill == "documents":
            files = ((selection.get("document_selection") or {}).get("selected_files") or [])
            if files:
                detail = f"Selected and read {len(files)} document(s): {', '.join(files[:4])}{', +' + str(len(files) - 4) + ' more' if len(files) > 4 else ''}."
        if skill == "document_completeness":
            completeness = selection.get("document_completeness") or {}
            if completeness:
                detail = (
                    f"Compared {completeness.get('required_count', 0)} required categories; "
                    f"{completeness.get('missing_count', 0)} missing."
                )
        steps.append(
            {
                "skill": skill,
                "tool_label": tool_contract.get("label", format_skill(skill)),
                "tool_type": tool_contract.get("tool_type", "read"),
                "required_permission": tool_contract.get("required_permission", "api:access"),
                "access_scope": tool_contract.get("access_scope", "submission"),
                "backend": tool_contract.get("backend", "internal_python"),
                "mcp_exposed": bool(tool_contract.get("mcp_exposed")),
                "citation_policy": tool_contract.get("citation_policy"),
                "status": "done" if source_count or skill in {"documents", "document_completeness"} else "empty",
                "source_count": source_count,
                "detail": detail,
            }
        )
    return steps


def summarize_tool_steps(tool_steps):
    if not tool_steps:
        return "No retrieval tools were needed."
    completed = [step for step in tool_steps if step.get("status") == "done"]
    empty = [step for step in tool_steps if step.get("status") == "empty"]
    parts = [f"Ran {len(tool_steps)} tool(s)"]
    if completed:
        parts.append(f"{len(completed)} returned data")
    if empty:
        parts.append(f"{len(empty)} returned no records")
    return "; ".join(parts) + "."


def evaluate_retrieval_confidence(retrieval_result, plan, file_selection_mode):
    sources = retrieval_result.get("sources", [])
    context = retrieval_result.get("context", "")
    selection = retrieval_result.get("selection", {})
    issues = []
    score = 0.45

    if plan:
        score += 0.15
    else:
        issues.append("No specialized retrieval skill matched the prompt.")

    if sources:
        score += min(0.2, len(sources) * 0.025)
    elif plan:
        issues.append("Selected skills returned no cited sources.")

    if len(context) > 300:
        score += 0.1
    elif plan:
        issues.append("Retrieved context is short.")

    document_selection = selection.get("document_selection") or {}
    selected_documents = document_selection.get("selected_files") or []
    if "documents" in plan:
        if selected_documents:
            score += 0.1
        elif file_selection_mode == "none":
            score += 0.05
        else:
            issues.append("Document skill selected but no document text was read.")

    if "document_completeness" in plan and selection.get("document_completeness"):
        score += 0.1

    if "analytics" in plan and any(source.get("source", "").startswith("model/") for source in sources):
        score += 0.08

    if "analytics_db" in plan and selection.get("analytics_db"):
        score += 0.12

    if "sop" in plan:
        sop_steps = ((selection.get("sop_selection") or {}).get("selected_steps") or [])
        if sop_steps:
            score += 0.06
        else:
            issues.append("SOP skill selected but no SOP step matched strongly.")

    score = max(0, min(score, 0.98))
    label = "high" if score >= 0.82 else "medium" if score >= MIN_CONFIDENCE else "low"
    summary = "Context is sufficient for this answer." if score >= MIN_CONFIDENCE else "Context may be incomplete; retry expansion is considered."
    return {
        "score": round(score, 3),
        "label": label,
        "threshold": MIN_CONFIDENCE,
        "summary": summary,
        "issues": issues,
    }


def expand_plan_for_retry(plan, prompt, confidence_check):
    expanded = list(plan)
    prompt_text = str(prompt or "").lower()
    issues = " ".join(confidence_check.get("issues") or []).lower()

    if "account_summary" not in expanded:
        expanded.insert(0, "account_summary")

    if any(term in prompt_text for term in ["missing", "required", "evidence", "document", "documnt", "file"]):
        expanded.extend(["document_completeness", "documents", "underwriting", "sop"])

    if any(term in prompt_text for term in ["quote", "bind", "model", "probability", "analytics"]):
        expanded.extend(["analytics", "underwriting"])

    if "no cited sources" in issues or "context is short" in issues:
        expanded.extend(["underwriting", "sop"])

    return dedupe(expanded)


def summarize_trace_for_response(trace):
    return {
        "trace_id": trace.get("trace_id"),
        "agent": trace.get("agent"),
        "status": trace.get("status"),
        "attempt_count": trace.get("attempt_count", 0),
        "confidence": trace.get("confidence", {}),
        "selected_skills": trace.get("selected_skills", []),
        "source_count": trace.get("source_count", 0),
        "steps": [
            {
                "phase": step.get("phase"),
                "title": step.get("title"),
                "status": step.get("status"),
                "detail": step.get("detail"),
            }
            for step in trace.get("steps", [])
        ],
    }


def format_skill_list(skills):
    return ", ".join(format_skill(skill) for skill in skills) if skills else "no specialized skills"


def format_skill(value):
    return str(value or "data").replace("_", " ").title()


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
