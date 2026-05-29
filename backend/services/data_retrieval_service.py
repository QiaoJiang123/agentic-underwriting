import math
import re

from backend.services.analytics_db_service import get_analytics_db_context
from backend.services.agent_tool_registry import (
    scoped_submission_for_skill,
    tool_contracts_for_plan,
    tool_permissions_for_plan,
)
from backend.services.auth_service import require_permission
from backend.services.broker_service import get_submission_broker, list_brokers
from backend.services.claim_service import get_claim_record
from backend.services.decision_workflow_service import get_decision_workflow_record
from backend.services.decision_package_service import get_decision_package
from backend.services.document_completeness_service import get_document_completeness_record
from backend.services.document_tools import read_documents, select_documents_for_prompt
from backend.services.guide_service import get_guide_record
from backend.services.mcp_client_service import call_mcp_tool
from backend.services.model_service import get_model
from backend.services.model_governance_service import get_model_governance
from backend.services.note_service import get_note_record
from backend.services.portfolio_workbench_service import (
    get_clearance_review,
    get_external_research,
    get_portfolio_queue,
    get_rating_quote,
)
from backend.services.sop_service import select_relevant_sop_steps
from backend.services.stage_state_service import get_stage_state_record
from backend.services.submission_service import get_submission_detail
from backend.services.task_service import get_task_record
from backend.services.underwriting_service import get_underwriting_system_record


SUPPLEMENTAL_MODEL_NAMES = [
    "cyber_attack_prob",
    "ransomware_prob",
    "data_breach_prob",
    "business_interruption_prob",
    "claim_severity_prob",
]

MODEL_LABELS = {
    "quote_prob": "Quote Probability",
    "bind_prob": "Bind Probability",
    "cyber_attack_prob": "Cyber Attack Probability",
    "ransomware_prob": "Ransomware Probability",
    "data_breach_prob": "Data Breach Probability",
    "business_interruption_prob": "Business Interruption Probability",
    "claim_severity_prob": "Claim Severity Probability",
}


CENTRAL_INFORMATION_AGENT = "centralized_underwriting_information_agent"


def build_data_retrieval_context(
    submission_id,
    prompt,
    selected_files=None,
    file_selection_mode="auto",
    max_documents=6,
    plan_override=None,
    auth_context=None,
    conversation_messages=None,
):
    if not submission_id or not prompt:
        return {"plan": [], "context": "", "sources": [], "selection": make_selection_record([], file_selection_mode)}

    selected_files = selected_files if isinstance(selected_files, list) else []
    prompt_text = normalize_text(prompt)
    plan = (
        dedupe(plan_override)
        if isinstance(plan_override, list)
        else select_information_for_prompt(prompt_text, conversation_messages=conversation_messages)
    )
    plan, denied_skills, skill_permissions = authorize_skill_plan(plan, auth_context, submission_id)
    sources = []
    sections = []
    selection_record = make_selection_record(plan, file_selection_mode)
    selection_record["skill_permissions"] = skill_permissions
    selection_record["denied_skills"] = denied_skills
    selection_record["tool_contracts"] = tool_contracts_for_plan(plan, compact=True)

    submission = get_submission_detail(submission_id)["submission"]

    if "account_summary" in plan:
        sections.append(render_account_summary(submission))
        sources.append({"skill": "account_summary", "source": f"data/submissions/{submission_id}/metadata.json"})

    if "status" in plan:
        system = get_underwriting_system_record(submission_id)
        claims = get_claim_record(submission_id)
        tasks = get_task_record(submission_id)
        stages = get_stage_state_record(submission_id)
        sections.append(render_submission_status_context(submission, system, claims, tasks, stages))
        sources.extend(
            [
                {"skill": "status", "source": f"data/submissions/{submission_id}/metadata.json"},
                {"skill": "status", "source": f"data/underwriting/{submission_id}.json"},
                {"skill": "status", "source": f"data/claims/{submission_id}.json"},
                {"skill": "status", "source": f"data/task/{submission_id}.json"},
                {"skill": "status", "source": f"data/states/{submission_id}.json"},
            ]
        )

    if "documents" in plan:
        document_context, document_sources, document_selection = retrieve_document_context(
            submission_id=submission_id,
            prompt=prompt,
            selected_files=selected_files,
            file_selection_mode=file_selection_mode,
            max_documents=max_documents,
            conversation_messages=conversation_messages,
        )
        selection_record["document_selection"] = document_selection
        if document_context:
            sections.append(document_context)
            sources.extend(document_sources)

    if "document_completeness" in plan:
        completeness = get_document_completeness_record(submission_id)
        selection_record["document_completeness"] = {
            "required_count": completeness.get("required_count", 0),
            "received_count": completeness.get("received_count", 0),
            "missing_count": completeness.get("missing_count", 0),
        }
        sections.append(render_document_completeness_context(completeness))
        sources.extend(
            [
                {"skill": "document_completeness", "source": completeness.get("requirement_path") or "data/document_requirements/cyber_required_documents.json"},
                {"skill": "document_completeness", "source": f"data/submissions/{submission_id}/metadata.json"},
            ]
        )

    if "underwriting" in plan:
        system = get_underwriting_system_record(submission_id)
        sections.append(render_underwriting_context(system))
        sources.append({"skill": "underwriting", "source": f"data/underwriting/{submission_id}.json"})
        sources.append({"skill": "underwriting", "source": "data/sop/cyber_underwriting_sop.json"})

    if "decision_workflow" in plan:
        workflow = get_decision_workflow_record(submission_id)
        sections.append(render_decision_workflow_context(workflow))
        sources.append({"skill": "decision_workflow", "source": f"data/decision_workflow/{submission_id}.json"})
        sources.append({"skill": "decision_workflow", "source": f"/api/submissions/{submission_id}/decision-workflow"})

    if "decision_package" in plan:
        package = get_decision_package(submission_id, resolve_package_type(prompt_text))
        sections.append(render_decision_package_context(package))
        sources.extend(
            {"skill": "decision_package", "source": item.get("source")}
            for item in package.get("citations", [])
            if item.get("source")
        )

    if "claims" in plan:
        claims = get_claim_record(submission_id)
        sections.append(render_claim_context(claims))
        sources.append({"skill": "claims", "source": f"data/claims/{submission_id}.json"})

    if "broker" in plan:
        broker = get_submission_broker(submission)
        sections.append(render_broker_context(broker))
        sources.append({"skill": "broker", "source": "data/brokers/brokers.json"})

    if "broker_table" in plan:
        sections.append(render_broker_table_context(prompt_text))
        sources.append({"skill": "broker_table", "source": "data/brokers/brokers.json"})

    if "analytics" in plan:
        analytics_context, analytics_sources = render_analytics_context(submission_id, submission)
        sections.append(analytics_context)
        sources.extend(analytics_sources)

    if "model_governance" in plan:
        governance = get_model_governance()
        sections.append(render_model_governance_context(governance))
        sources.append({"skill": "model_governance", "source": "model/governance.json"})

    if "portfolio" in plan:
        portfolio = get_portfolio_queue()
        sections.append(render_portfolio_context(portfolio, submission_id))
        sources.append({"skill": "portfolio", "source": "/api/portfolio/queue"})

    if "analytics_db" in plan:
        analytics_db = get_analytics_db_context(submission_id, prompt_text)
        sections.append(analytics_db.get("context", ""))
        sources.extend(analytics_db.get("sources", []))
        selection_record["analytics_db"] = analytics_db.get("selection", {})

    if "clearance" in plan:
        clearance = get_clearance_review(submission_id)
        sections.append(render_clearance_context(clearance))
        sources.append({"skill": "clearance", "source": f"/api/submissions/{submission_id}/clearance"})

    if "rating_quote" in plan:
        rating_quote = get_rating_quote(submission_id)
        sections.append(render_rating_quote_context(rating_quote))
        sources.append({"skill": "rating_quote", "source": f"/api/submissions/{submission_id}/rating-quote"})

    if "external_research" in plan:
        external_research = get_external_research(submission_id)
        sections.append(render_external_research_context(external_research))
        sources.append({"skill": "external_research", "source": f"/api/submissions/{submission_id}/external-research"})

    if "sop" in plan:
        sop_selection = select_relevant_sop_steps(prompt_text)
        selection_record["sop_selection"] = sop_selection
        sections.append(render_sop_context(sop_selection))
        sources.append({"skill": "sop", "source": "data/sop/metadata.json"})
        sources.extend(
            [
                {"skill": "sop", "source": f"data/sop/cyber_underwriting_sop.json#{step.get('step_id')}"}
                for step in sop_selection.get("selected_steps", [])
            ]
        )

    if "notes" in plan:
        notes = get_note_record(submission_id)
        sections.append(render_notes_context(notes))
        sources.append({"skill": "notes", "source": f"data/note/{submission_id}.json"})

    if "guides" in plan:
        guides = get_guide_record(submission_id)
        sections.append(render_guides_context(guides))
        sources.append({"skill": "guides", "source": f"data/guide/{submission_id}.json"})

    if "tasks" in plan:
        tasks = get_task_record(submission_id)
        sections.append(render_tasks_context(tasks))
        sources.append({"skill": "tasks", "source": f"data/task/{submission_id}.json"})

    if "stages" in plan:
        stages = get_stage_state_record(submission_id)
        sections.append(render_stages_context(stages))
        sources.append({"skill": "stages", "source": f"data/states/{submission_id}.json"})

    context = ""
    if sections:
        context = "\n\n".join(
            [
                "Retrieved underwriting data context. Use this as source data for the current answer. Do not mention a source unless it is relevant to the answer.",
                f"Retrieval skills used: {', '.join(plan)}.",
                render_denied_skill_context(denied_skills),
                *sections,
            ]
        )

    return {
        "plan": plan,
        "context": context,
        "sources": sources,
        "selection": {
            **selection_record,
            "source_count": len(sources),
            "selected_sources": summarize_selected_sources(sources),
        },
    }


def select_information_for_prompt(prompt_text, conversation_messages=None):
    planning_prompt = build_planning_prompt(normalize_text(prompt_text), conversation_messages)
    return plan_retrieval(normalize_text(planning_prompt))


def build_planning_prompt(prompt_text, conversation_messages=None):
    if not should_use_history_for_planning(prompt_text):
        return prompt_text

    history_context = format_recent_chat_context(conversation_messages, prompt_text, max_messages=6)
    if not history_context:
        return prompt_text

    return "\n".join(
        [
            "Current underwriter prompt:",
            str(prompt_text or "").strip(),
            "",
            "Recent chat context for resolving references:",
            history_context,
        ]
    )


def should_use_history_for_planning(prompt_text):
    normalized = normalize_text(prompt_text)
    if not normalized:
        return False

    reference_terms = [
        "that",
        "those",
        "these",
        "them",
        "same",
        "above",
        "previous",
        "earlier",
        "continue",
        "what about",
        "how about",
        "tell me more",
        "show more",
        "explain more",
    ]
    words = normalized.split()
    if has_any(normalized, reference_terms):
        return True

    current_plan = plan_retrieval(normalized)
    specific_skills = [skill for skill in current_plan if skill != "account_summary"]
    return not specific_skills and len(words) <= 8


def build_document_selection_prompt(prompt, conversation_messages=None):
    history_context = format_recent_chat_context(conversation_messages, prompt, max_messages=8)
    if not history_context:
        return str(prompt or "")

    return "\n".join(
        [
            "Current underwriter prompt:",
            str(prompt or "").strip(),
            "",
            "Recent chat context for document selection only:",
            history_context,
        ]
    )


def format_recent_chat_context(conversation_messages, current_prompt, max_messages=8, max_chars_per_message=420):
    if not isinstance(conversation_messages, list):
        return ""

    current_normalized = normalize_text(current_prompt)
    lines = []
    for message in conversation_messages:
        if not isinstance(message, dict):
            continue
        role = "assistant" if message.get("role") == "assistant" else "user"
        content = re.sub(r"\s+", " ", str(message.get("content") or "")).strip()
        if not content:
            continue
        if role == "user" and normalize_text(content) == current_normalized:
            continue
        if len(content) > max_chars_per_message:
            content = f"{content[:max_chars_per_message].rstrip()}..."
        lines.append(f"- {role}: {content}")

    return "\n".join(lines[-max_messages:])


def make_selection_record(plan, file_selection_mode):
    return {
        "agent": CENTRAL_INFORMATION_AGENT,
        "tool_registry_version": "0.1.0",
        "mode": "auto" if file_selection_mode == "auto" else "fixed",
        "file_selection_mode": file_selection_mode,
        "selected_skills": plan,
        "tool_contracts": tool_contracts_for_plan(plan, compact=True),
        "document_selection": None,
        "document_completeness": None,
        "sop_selection": None,
        "skill_permissions": {},
        "denied_skills": [],
    }


def authorize_skill_plan(plan, auth_context, submission_id):
    permission_map = tool_permissions_for_plan(plan)
    if not auth_context:
        return plan, [], permission_map

    authorized = []
    denied = []
    for skill in plan:
        permission = permission_map.get(skill, "api:access")
        scoped_submission = scoped_submission_for_skill(skill, submission_id)
        try:
            require_permission(auth_context, permission, scoped_submission)
            authorized.append(skill)
        except PermissionError as error:
            denied.append({"skill": skill, "required_permission": permission, "reason": str(error)})
    return authorized, denied, permission_map


def render_denied_skill_context(denied_skills):
    if not denied_skills:
        return "Authorization filter: all selected skills were permitted for this user."
    lines = ["Authorization filter: some selected skills were not available to this user."]
    for item in denied_skills:
        lines.append(
            f"- {item.get('skill')}: requires {item.get('required_permission')} | {item.get('reason')}"
        )
    return "\n".join(lines)


def summarize_selected_sources(sources):
    grouped = {}
    for source in sources:
        skill = source.get("skill") if isinstance(source, dict) else None
        if not skill:
            continue
        grouped.setdefault(skill, 0)
        grouped[skill] += 1
    return grouped


def plan_retrieval(prompt_text):
    skills = []

    if has_status_intent(prompt_text):
        skills.extend(["status", "underwriting", "tasks", "stages"])

    if has_document_completeness_intent(prompt_text):
        skills.append("document_completeness")

    if has_any(
        prompt_text,
        [
            "document",
            "documents",
            "documnt",
            "documnts",
            "file",
            "application",
            "supplemental",
            "ransomware",
            "mfa",
            "edr",
            "backup",
            "policy",
            "loss run",
            "financial",
            "revenue",
            "vendor",
            "compliance",
            "soc",
            "hipaa",
            "pci",
            "incident response",
            "control",
            "evidence",
            "questionnaire",
            "what does",
            "based on the file",
        ],
    ):
        skills.append("documents")

    if has_any(prompt_text, ["claim", "claims", "loss", "losses", "loss run", "severity", "incurred", "paid", "reserve"]):
        skills.append("claims")

    if has_any(prompt_text, ["broker", "producer", "account manager", "submission channel", "market", "relationship"]):
        skills.append("broker")
        if wants_broker_table(prompt_text):
            skills.append("broker_table")

    if has_any(
        prompt_text,
        [
            "analytics",
            "model",
            "probability",
            "quote",
            "quote readiness",
            "bind",
            "bind readiness",
            "score",
            "waterfall",
            "driver",
            "feature",
            "coefficient",
            "cyber attack",
            "ransomware probability",
            "breach",
            "business interruption",
            "industry propensity",
            "propensity",
            "benchmark",
            "portfolio",
            "queue",
            "pipeline",
        ],
    ):
        skills.append("analytics")

    if has_any(prompt_text, ["portfolio", "queue", "pipeline", "book view", "dashboard"]):
        skills.append("portfolio")

    if has_any(
        prompt_text,
        [
            "statistics",
            "statistic",
            "stats",
            "aggregate",
            "average",
            "avg",
            "total incurred",
            "by broker",
            "by company",
            "by industry",
            "sql",
            "database",
            "analytics db",
            "analytic db",
            "how many claims",
            "associated underwriting decisions",
            "claim statistics",
            "claim stats",
        ],
    ):
        skills.append("analytics_db")

    if has_any(prompt_text, ["clearance", "clear this account", "duplicate", "duplicate scan", "conflict", "compliance check"]):
        skills.append("clearance")

    if has_any(prompt_text, ["rating", "rate this", "premium", "quote package", "indicated premium", "terms", "subjectivity", "subjectivities"]):
        skills.append("rating_quote")

    if has_any(prompt_text, ["external research", "research", "sanctions", "security rating", "breach news", "business registry", "domain security"]):
        skills.append("external_research")

    if has_underwriting_intent(prompt_text):
        skills.append("underwriting")

    if has_decision_workflow_intent(prompt_text):
        skills.append("decision_workflow")

    if has_decision_package_intent(prompt_text):
        skills.extend(["decision_package", "decision_workflow"])

    if has_model_governance_intent(prompt_text):
        skills.append("model_governance")

    if has_sop_intent(prompt_text):
        skills.append("sop")
        if sop_needs_submission_context(prompt_text):
            skills.append("underwriting")

    if has_any(prompt_text, ["note", "notes", "ground truth"]):
        skills.append("notes")

    if has_any(prompt_text, ["guide", "guidance", "instruction", "system prompt"]):
        skills.append("guides")

    if has_task_intent(prompt_text):
        skills.append("tasks")

    if has_stage_intent(prompt_text):
        skills.append("stages")

    if should_include_account_summary(prompt_text, skills):
        skills.insert(0, "account_summary")

    return dedupe(skills)


def has_underwriting_intent(prompt_text):
    return has_any(
        prompt_text,
        [
            "appetite",
            "underwriting system",
            "underwriting workbench",
            "underwriting assessment",
            "underwriting recommendation",
            "risk flag",
            "risk flags",
            "recommended action",
            "authority",
            "referral",
            "missing evidence",
            "missing information",
            "what is missing",
            "evidence gap",
        ],
    )


def has_document_completeness_intent(prompt_text):
    document_terms = [
        "document",
        "documents",
        "documnt",
        "documnts",
        "doc",
        "docs",
        "file",
        "files",
        "evidence",
        "filing",
        "filings",
    ]
    completeness_terms = [
        "missing",
        "required",
        "requirement",
        "checklist",
        "provided",
        "submitted",
        "received",
        "available",
        "outstanding",
        "gap",
        "gaps",
        "complete",
        "completeness",
    ]
    return has_any(prompt_text, document_terms) and has_any(prompt_text, completeness_terms)


def has_decision_workflow_intent(prompt_text):
    return has_any(
        prompt_text,
        [
            "quote readiness",
            "ready to quote",
            "quote approval",
            "approve quote",
            "referral",
            "refer",
            "senior approval",
            "authority approval",
            "bind readiness",
            "ready to bind",
            "bind approval",
            "decision workflow",
            "workflow gate",
        ],
    )


def has_decision_package_intent(prompt_text):
    return has_any(
        prompt_text,
        [
            "decision package",
            "quote package",
            "referral package",
            "bind package",
            "approval package",
            "export package",
            "underwriting package",
            "package for review",
        ],
    )


def has_model_governance_intent(prompt_text):
    return has_any(
        prompt_text,
        [
            "model governance",
            "model approval",
            "approved model",
            "model validation",
            "validation report",
            "model limitation",
            "model limitations",
            "override reason",
            "override policy",
            "model monitoring",
            "model owner",
            "demo model",
        ],
    )


def resolve_package_type(prompt_text):
    if has_any(prompt_text, ["referral package", "refer", "referral"]):
        return "referral"
    if has_any(prompt_text, ["bind package", "bind readiness", "ready to bind"]):
        return "bind"
    if has_any(prompt_text, ["quote package", "quote readiness", "ready to quote"]):
        return "quote"
    return "review"


def has_sop_intent(prompt_text):
    return has_any(
        prompt_text,
        [
            "sop",
            "procedure",
            "standard operating",
            "operating procedure",
            "what should i do next",
            "next step",
            "next action",
            "broker follow up",
            "broker follow-up",
            "draft broker",
            "missing evidence",
            "missing information",
            "what is missing",
            "evidence gap",
            "required evidence",
            "subjectivity",
            "subjectivities",
            "quote release",
            "ready to quote",
            "referral trigger",
            "authority trigger",
        ],
    )


def sop_needs_submission_context(prompt_text):
    return has_any(
        prompt_text,
        [
            "what should i do next",
            "next step",
            "next action",
            "broker follow up",
            "broker follow-up",
            "draft broker",
            "missing evidence",
            "missing information",
            "what is missing",
            "evidence gap",
            "quote release",
            "ready to quote",
            "referral trigger",
            "authority trigger",
        ],
    )


def has_task_intent(prompt_text):
    return has_any(prompt_text, ["task", "tasks", "calendar", "due", "todo", "to do", "reminder"])


def has_stage_intent(prompt_text):
    return has_any(prompt_text, ["stage", "stages", "workflow", "checklist", "current stage", "next stage"])


def has_status_intent(prompt_text):
    if has_task_intent(prompt_text) and not has_any(
        prompt_text,
        [
            "submission status",
            "overall status",
            "account status",
            "where are we",
            "current workflow",
            "where is this submission",
        ],
    ):
        return False

    return has_any(
        prompt_text,
        [
            "current status",
            "submission status",
            "status update",
            "where are we",
            "what is the status",
            "overall status",
            "account status",
            "current position",
            "current workflow",
            "where is this submission",
            "changed recently",
            "update history",
            "submission updates",
            "recent updates",
        ],
    )


def should_include_account_summary(prompt_text, selected_skills):
    if not selected_skills:
        return True

    return has_any(
        prompt_text,
        [
            "account",
            "account summary",
            "applicant",
            "insured",
            "company",
            "company summary",
            "submission details",
            "key information",
            "overview",
            "who is",
        ],
    )


def render_submission_status_context(submission, system, claims, tasks, stages):
    appetite = system.get("appetite") or {}
    evidence = system.get("evidence_status") or []
    available_evidence = len([item for item in evidence if item.get("status") == "available"])
    claim_snapshot = claims.get("aggregate") or {}
    task_items = tasks.get("tasks") or []
    open_tasks = [item for item in task_items if item.get("status") != "done"]
    stage_items = stages.get("stages") or []
    checked_stages = [item for item in stage_items if item.get("checked")]
    current_stage = next((item for item in stage_items if item.get("isCurrent")), None)
    if not current_stage and stage_items:
        current_stage = next((item for item in stage_items if not item.get("checked")), stage_items[-1])

    return "\n".join(
        [
            "Current Submission Status:",
            f"- Metadata status: {submission.get('status', 'TBD')}",
            f"- Appetite: {appetite.get('status', 'TBD')} | {appetite.get('rationale', 'TBD')}",
            f"- Evidence readiness: {available_evidence}/{len(evidence)} required categories available",
            f"- Claims: {claim_snapshot.get('total_claims', 0)} total, {claim_snapshot.get('open_claims', 0)} open, {format_currency(claim_snapshot.get('total_incurred'))} incurred",
            f"- Workflow progress: {len(checked_stages)}/{len(stage_items)} stages checked; current/next stage: {(current_stage or {}).get('label', 'TBD')}",
            f"- Stage lock: {'submitted / locked stages exist' if stages.get('submitted_at') else 'not submitted'}",
            f"- Open scheduled tasks: {len(open_tasks)}",
            "Open tasks:",
            *[f"  - {item.get('due_date', 'TBD')}: {item.get('title', '')}" for item in open_tasks[:5]],
        ]
    )


def retrieve_document_context(
    submission_id,
    prompt,
    selected_files,
    file_selection_mode,
    max_documents,
    conversation_messages=None,
):
    if file_selection_mode == "none":
        selected = []
        selection_source = "no_files_selected"
        selection = {
            "source": selection_source,
            "selected_files": selected,
            "mode": file_selection_mode,
            "reason": "User fixed document selection to no files.",
        }
    elif file_selection_mode in {"all", "manual"}:
        selected = selected_files
        selection_source = "all_files_selected" if file_selection_mode == "all" else "manual_file_selection"
        selection = {
            "source": selection_source,
            "selected_files": selected,
            "mode": file_selection_mode,
            "reason": "User fixed document selection; centralized agent did not override it.",
        }
    else:
        selection_prompt = build_document_selection_prompt(prompt, conversation_messages)
        history_context_used = bool(format_recent_chat_context(conversation_messages, prompt, max_messages=8))
        try:
            selection = call_mcp_tool(
                "select_documents",
                {
                    "submission_id": submission_id,
                    "prompt": selection_prompt,
                    "max_documents": max_documents,
                },
            )
            selection["transport"] = "mcp"
            selection["mcp_server"] = "agentic-underwriting"
            selection["mcp_tool"] = "select_documents"
        except Exception as error:
            selection = select_documents_for_prompt(
                submission_id=submission_id,
                prompt=selection_prompt,
                max_documents=max_documents,
            )
            selection["transport"] = "internal_python_fallback"
            selection["mcp_error"] = str(error)
        selected = selection.get("selected_files", [])
        selection_source = selection.get("source", "metadata_rules")
        if selection.get("transport") == "mcp":
            selection_source = f"mcp:{selection_source}"
        selection["mode"] = "auto"
        selection["conversation_context_used"] = history_context_used
        selection["reason"] = (
            "Centralized information agent selected documents from submission metadata using the current prompt and recent chat history."
            if history_context_used
            else "Centralized information agent selected documents from submission metadata."
        )

    if not selected:
        return "", [], selection

    document_record = read_documents_with_agent_tool(submission_id, selected, selection)
    documents = document_record.get("documents", [])
    if not documents:
        selection["selected_files"] = []
        return "", [], selection

    selection["selected_files"] = [document.get("file_name", "") for document in documents if document.get("file_name")]

    sections = [f"Document retrieval source: {selection_source}."]
    sources = []
    for document in documents:
        file_name = document.get("file_name", "")
        sources.append({"skill": "documents", "source": f"data/submissions/{submission_id}/{file_name}"})
        sections.extend(
            [
                f"--- Document: {file_name} ---",
                f"Type: {document.get('file_type', 'TBD')}",
                f"Categories: {', '.join(document.get('major_categories') or []) or document.get('category', 'TBD')}",
                f"Description: {document.get('description', 'TBD')}",
                "Content:",
                document.get("content") or "[Document content is not available as text.]",
            ]
        )

    return "\n".join(sections), sources, selection


def read_documents_with_agent_tool(submission_id, selected_files, selection):
    try:
        document_record = call_mcp_tool(
            "read_selected_documents",
            {
                "submission_id": submission_id,
                "file_names": selected_files,
            },
        )
        selection["document_read_transport"] = "mcp"
        selection["document_read_tool"] = "read_selected_documents"
        selection["mcp_server"] = selection.get("mcp_server", "agentic-underwriting")
        return document_record
    except Exception as error:
        selection["document_read_transport"] = "internal_python_fallback"
        selection["document_read_mcp_error"] = str(error)
        return read_documents(submission_id, selected_files)


def render_document_completeness_context(record):
    required_status = record.get("required_status") or []
    submitted_documents = record.get("submitted_documents") or []
    missing = record.get("missing_required_documents") or []
    extras = record.get("extra_documents") or []
    lines = [
        "Document Completeness Review:",
        f"- Required document source: {record.get('requirement_source', 'Stored cyber requirement map')}",
        f"- Required categories: {record.get('required_count', len(required_status))}",
        f"- Received required categories: {record.get('received_count', 0)}/{record.get('required_count', len(required_status))}",
        f"- Missing required categories: {record.get('missing_count', len(missing))}",
        f"- Submitted files in metadata: {record.get('submitted_count', len(submitted_documents))}",
        "Required vs submitted:",
    ]

    for item in required_status:
        files = ", ".join(item.get("source_files") or [])
        status = "Received" if item.get("status") == "received" else "Missing"
        lines.append(f"- {status}: {item.get('label', item.get('key', 'Required document'))}" + (f" | files: {files}" if files else ""))

    lines.append("Submitted document metadata:")
    if submitted_documents:
        for document in submitted_documents:
            matched_labels = [
                item.get("label", item.get("key", "Required document"))
                for item in required_status
                if item.get("key") in (document.get("matched_required_keys") or [])
            ]
            lines.append(
                f"- {document.get('file_name', 'document')} | type: {document.get('file_type') or 'TBD'} | "
                f"matched required categories: {', '.join(matched_labels) if matched_labels else 'none'} | "
                f"description: {document.get('description') or 'TBD'}"
            )
    else:
        lines.append("- No submitted document metadata is attached.")

    if missing:
        lines.extend(
            [
                "Answering instruction:",
                "Directly answer document-missing questions from the Missing rows above. Do not say the document names are unavailable; they are listed in this completeness review.",
            ]
        )
    else:
        lines.extend(
            [
                "Answering instruction:",
                "All required document categories are satisfied by submitted metadata. Mention any extra/unmapped files only if useful.",
            ]
        )

    if extras:
        lines.append("Extra or unmapped submitted files:")
        lines.extend(f"- {document.get('file_name', 'document')}: {document.get('description') or 'TBD'}" for document in extras)

    return "\n".join(lines)


def render_account_summary(submission):
    applicant = submission.get("applicant", {})
    coverage = submission.get("coverage", {})
    risk_flags = submission.get("risk_flags") or []
    open_questions = submission.get("open_questions") or []
    timeline = submission.get("timeline") or []
    documents = submission.get("documents") or []
    return "\n".join(
        [
            "Account Summary:",
            f"- Submission: {submission.get('id')} | {submission.get('title')} | Status: {submission.get('status', 'TBD')}",
            f"- Insured: {applicant.get('insured_name', 'TBD')}",
            f"- Industry: {applicant.get('industry', 'TBD')} | Benchmark bucket: {applicant.get('industry_bucket') or applicant.get('industry_group') or 'TBD'}",
            f"- Location: {applicant.get('location', 'TBD')} | Revenue: {format_currency(applicant.get('annual_revenue'))} | Employees: {applicant.get('employee_count', 'TBD')} | Records: {format_int(applicant.get('records_count'))}",
            f"- Technology profile: {applicant.get('technology_profile', 'TBD')}",
            f"- Coverage requested: {', '.join(coverage.get('lines_requested') or []) or 'TBD'}",
            f"- Effective date: {coverage.get('requested_effective_date', 'TBD')} | Retention: {coverage.get('retention_requested', 'TBD')}",
            f"- Requested limits: {format_limits(coverage.get('requested_limits') or {})}",
            f"- Documents available: {len(documents)}",
            f"- Risk flags: {', '.join(risk_flags) if risk_flags else 'None listed'}",
            f"- Open questions: {', '.join(open_questions[:5]) if open_questions else 'None listed'}",
            "Recent timeline:",
            *[f"- {item.get('date', 'TBD')}: {item.get('event', 'Event')} - {item.get('description', '')}" for item in timeline[-5:]],
        ]
    )


def render_underwriting_context(system):
    appetite = system.get("appetite") or {}
    evidence = system.get("evidence_status") or []
    signals = system.get("signals") or []
    actions = system.get("recommended_actions") or []
    sop_guidance = system.get("sop_guidance") or {}
    sop_suggestions = sop_guidance.get("suggestions") or []
    missing = [item for item in evidence if item.get("status") == "missing"]
    available = [item for item in evidence if item.get("status") == "available"]
    return "\n".join(
        [
            "Underwriting System:",
            f"- SOP: {sop_guidance.get('name', 'Commercial Cyber Underwriting SOP')} v{sop_guidance.get('version', 'TBD')}",
            f"- Appetite: {appetite.get('status', 'TBD')} | Authority: {appetite.get('recommended_authority', 'TBD')}",
            f"- Appetite rationale: {appetite.get('rationale', 'TBD')}",
            f"- Evidence: {len(available)}/{len(evidence)} required categories available.",
            f"- Missing evidence: {', '.join(item.get('label', 'Evidence') for item in missing) if missing else 'None'}",
            "SOP suggestions:",
            *[
                f"- {suggestion.get('step_label', 'SOP')}: {suggestion.get('recommendation', '')} ({suggestion.get('rationale', '')})"
                for suggestion in sop_suggestions[:6]
            ],
            "Signals:",
            *[f"- {signal.get('label', 'Signal')}: {signal.get('severity', 'TBD')} - {signal.get('detail', '')}" for signal in signals],
            "Recommended actions:",
            *[f"- {action}" for action in actions],
        ]
    )


def render_decision_workflow_context(workflow):
    gates = workflow.get("gates") or []
    lines = [
        "Underwriting Decision Workflow:",
        f"- Policy: {(workflow.get('decision_policy') or {}).get('name', 'commercial_cyber_demo_decision_workflow')}",
    ]
    for gate in gates:
        blockers = ", ".join(gate.get("blockers") or []) or "None"
        actions = "; ".join(gate.get("required_actions") or [])
        lines.extend(
            [
                f"- {gate.get('label', gate.get('key', 'Gate'))}: {gate.get('status', 'TBD')} | score {format_percent(gate.get('score'))}",
                f"  Rationale: {gate.get('rationale', '')}",
                f"  Blockers: {blockers}",
                f"  Required actions: {actions}",
            ]
        )
    return "\n".join(lines)


def render_decision_package_context(package):
    account = package.get("account") or {}
    evidence = package.get("evidence") or {}
    claims = (package.get("claims") or {}).get("aggregate") or {}
    rating = package.get("rating_quote") or {}
    workflow = package.get("workflow") or {}
    governance = package.get("model_governance") or {}
    controls = package.get("underwriter_controls") or []
    gate_lines = []
    for gate in workflow.get("gates", []):
        gate_lines.append(
            f"- {gate.get('label', gate.get('key', 'Gate'))}: {gate.get('status', 'TBD')} | score {format_percent(gate.get('score'))}"
        )
    model_lines = []
    for model in governance.get("models", [])[:8]:
        model_lines.append(
            f"- {model.get('display_name', model.get('model_name'))}: {model.get('approval_status', 'TBD')} | {model.get('version', 'TBD')} | use {model.get('allowed_use', 'decision support')}"
        )
    return "\n".join(
        [
            "Underwriting Decision Package:",
            f"- Package type: {package.get('package_type', 'review')} | Generated: {package.get('generated_at', 'TBD')}",
            f"- Account: {account.get('insured_name', 'TBD')} | {account.get('industry', 'TBD')} | Status: {account.get('status', 'TBD')}",
            f"- Evidence readiness: {evidence.get('received_count', 0)}/{evidence.get('required_count', 0)} | Missing: {evidence.get('missing_count', 0)}",
            f"- Claims: {claims.get('total_claims', 0)} total | {claims.get('open_claims', 0)} open | incurred {format_currency(claims.get('total_incurred'))}",
            f"- Rating: {rating.get('status', 'TBD')} | Premium {format_currency(rating.get('indicated_premium'))} | Quote readiness {format_percent(make_number(rating.get('quote_readiness')) / 100)}",
            "Workflow gates:",
            *(gate_lines or ["- No workflow gates available."]),
            "Model governance:",
            *(model_lines or ["- No model governance records available."]),
            "Underwriter controls:",
            *[f"- {control}" for control in controls],
        ]
    )


def render_model_governance_context(governance):
    default_policy = governance.get("default_policy") or {}
    models = governance.get("models") or {}
    lines = [
        "Model Governance:",
        f"- Registry: {governance.get('source', 'model/governance.json')} | Version: {governance.get('registry_version', 'TBD')}",
        f"- Default approval status: {default_policy.get('approval_status', 'TBD')}",
        f"- Decision owner: {default_policy.get('decision_owner', 'human_underwriter')} | Allowed use: {default_policy.get('allowed_use', 'decision_support_only')}",
        f"- Override reason required: {default_policy.get('override_required_reason', True)}",
        "Model records:",
    ]
    for model in models.values():
        lines.extend(
            [
                f"- {model.get('display_name', model.get('model_name'))}: {model.get('approval_status', 'TBD')} | {model.get('model_family', 'TBD')} | {model.get('version', 'TBD')}",
                f"  Intended use: {model.get('intended_use', 'Decision support only.')}",
                f"  Monitoring: {', '.join(model.get('monitoring_metrics') or []) or 'TBD'}",
            ]
        )
    return "\n".join(lines)


def render_sop_context(selection):
    selected_steps = selection.get("selected_steps") or []
    if not selected_steps:
        return "\n".join(
            [
                "Selected SOP Guidance:",
                f"- SOP: {selection.get('name', 'Commercial Cyber Underwriting SOP')} v{selection.get('version', 'TBD')}",
                "- No SOP step matched the prompt metadata.",
            ]
        )

    lines = [
        "Selected SOP Guidance:",
        f"- SOP: {selection.get('name', 'Commercial Cyber Underwriting SOP')} v{selection.get('version', 'TBD')}",
        f"- Metadata source: {selection.get('metadata_source', 'data/sop/metadata.json')}",
        "Relevant SOP steps:",
    ]
    for step in selected_steps:
        reasons = "; ".join(step.get("reasons") or [])
        related_data = ", ".join(step.get("related_data") or [])
        lines.extend(
            [
                f"- {step.get('label', 'SOP step')} ({step.get('priority', 'medium')} priority)",
                f"  Goal: {step.get('goal', '')}",
                f"  Suggested use: {step.get('suggestion_template', '')}",
                f"  Related data: {related_data or 'Not specified'}",
                f"  Selection reason: {reasons or 'Selected by SOP metadata.'}",
            ]
        )
    return "\n".join(lines)


def render_claim_context(record):
    aggregate = record.get("aggregate") or {}
    claims = record.get("claims") or []
    return "\n".join(
        [
            "Claim System:",
            f"- Claim system: {record.get('claim_system', 'dummy_claims_core')} | Updated: {record.get('updated_at') or 'TBD'}",
            f"- Total claims: {aggregate.get('total_claims', 0)} | Open: {aggregate.get('open_claims', 0)} | Incurred: {format_currency(aggregate.get('total_incurred'))}",
            f"- Latest loss date: {aggregate.get('latest_loss_date') or 'TBD'}",
            "Claims:",
            *[
                f"- {claim.get('claim_id')}: {claim.get('loss_date')} | {format_label(claim.get('claim_type'))} | {format_label(claim.get('status'))} | {format_label(claim.get('severity'))} | paid {format_currency(claim.get('amount_paid'))}, reserve {format_currency(claim.get('amount_reserved'))} | {claim.get('description') or claim.get('cause') or ''}"
                for claim in claims
            ],
        ]
    )


def render_broker_context(broker):
    if not broker:
        return "Broker Context:\n- No broker profile is linked to this submission."

    contact = broker.get("submission_contact") or {}
    metrics = broker.get("relationship_metrics") or {}
    contacts = broker.get("contacts") or {}
    producer = contacts.get("producer") or {}
    account_manager = contacts.get("account_manager") or {}
    return "\n".join(
        [
            "Broker Context:",
            f"- Firm: {broker.get('firm_name', 'TBD')} | Type: {broker.get('broker_type', 'TBD')} | Tier: {broker.get('service_tier', 'TBD')} | Region: {broker.get('primary_region', 'TBD')}",
            f"- Producer: {contact.get('producer_name') or producer.get('name', 'TBD')} | {contact.get('producer_email') or producer.get('email', 'TBD')}",
            f"- Account manager: {contact.get('account_manager_name') or account_manager.get('name', 'TBD')} | {contact.get('account_manager_email') or account_manager.get('email', 'TBD')}",
            f"- Quote ratio: {format_percent(metrics.get('quote_ratio_12m'))} | Bind ratio: {format_percent(metrics.get('bind_ratio_12m'))} | Data quality: {metrics.get('data_quality_score', 'TBD')}/100 | Avg response: {metrics.get('avg_response_hours', 'TBD')} hours",
            f"- Market focus: {', '.join(broker.get('market_focus') or []) or 'TBD'}",
            f"- Placement notes: {broker.get('placement_notes', 'TBD')}",
            f"- Submission note: {contact.get('broker_notes', 'TBD')}",
        ]
    )


def render_broker_table_context(prompt_text):
    brokers = list_brokers()
    if not brokers:
        return "Broker Database Table:\n- No broker records found."

    metric_key, metric_label, ascending = resolve_broker_table_metric(prompt_text)
    ranked = sorted(
        brokers,
        key=lambda broker: broker_metric_value(broker, metric_key),
        reverse=not ascending,
    )

    return "\n".join(
        [
            "Broker Database Table:",
            f"- Source: data/brokers/brokers.json | Rows: {len(brokers)}",
            f"- Sorted for this prompt by: {metric_label} ({'lower is better' if ascending else 'higher is better'})",
            "Broker rows:",
            *[render_broker_table_row(broker, metric_key, metric_label) for broker in ranked],
        ]
    )


def render_broker_table_row(broker, metric_key, metric_label):
    metrics = broker.get("relationship_metrics") or {}
    contacts = broker.get("contacts") or {}
    producer = contacts.get("producer") or {}
    account_manager = contacts.get("account_manager") or {}
    return (
        f"- {broker.get('broker_id', 'broker')}: {broker.get('firm_name', 'TBD')} | "
        f"{broker.get('broker_type', 'TBD')} | Tier {broker.get('service_tier', 'TBD')} | "
        f"Region {broker.get('primary_region', 'TBD')} | "
        f"{metric_label}: {format_broker_metric(metric_key, metrics.get(metric_key))} | "
        f"Quote {format_percent(metrics.get('quote_ratio_12m'))} | "
        f"Bind {format_percent(metrics.get('bind_ratio_12m'))} | "
        f"Data quality {metrics.get('data_quality_score', 'TBD')}/100 | "
        f"Avg response {metrics.get('avg_response_hours', 'TBD')}h | "
        f"YTD submissions {metrics.get('submissions_ytd', 'TBD')} | "
        f"Producer {producer.get('name', 'TBD')} <{producer.get('email', 'TBD')}> | "
        f"Account manager {account_manager.get('name', 'TBD')} <{account_manager.get('email', 'TBD')}> | "
        f"Focus: {', '.join(broker.get('market_focus') or []) or 'TBD'} | "
        f"Preferences: {', '.join(broker.get('communication_preferences') or []) or 'TBD'} | "
        f"Notes: {broker.get('placement_notes', 'TBD')}"
    )


def render_analytics_context(submission_id, submission):
    system = get_underwriting_system_record(submission_id)
    feature_lookup = build_feature_lookup(submission, system)
    model_names = ["quote_prob", "bind_prob", *SUPPLEMENTAL_MODEL_NAMES]
    model_lines = ["Analytics and Model Context:"]
    sources = []

    for model_name in model_names:
        model = get_model(model_name)
        scored = score_model(model, feature_lookup)
        model_lines.append(render_scored_model(model_name, scored))
        sources.append({"skill": "analytics", "source": f"model/{model_name}.json"})

    industry_model = get_model("industry_propensity")
    model_lines.append(render_industry_benchmark(industry_model, feature_lookup.get("industry_propensity", {})))
    sources.append({"skill": "analytics", "source": "model/industry_propensity.json + data/claims/*.json"})
    return "\n\n".join(model_lines), sources


def render_scored_model(model_name, scored):
    drivers = sorted(scored["steps"], key=lambda item: abs(item["logit_contribution"]), reverse=True)
    top_drivers = drivers[:5]
    return "\n".join(
        [
            f"{MODEL_LABELS.get(model_name, model_name)}:",
            f"- Average probability: {format_percent(scored['average_probability'])} | Current probability: {format_percent(scored['probability'])}",
            "- Top drivers:",
            *[
                f"  - {driver['label']}: {driver['display_value']} | contribution {driver['logit_contribution']:+.3f} logit"
                for driver in top_drivers
            ],
        ]
    )


def render_industry_benchmark(model, industry_feature):
    history = model.get("industry_history") or []
    current_bucket = industry_feature.get("display_value", "TBD")
    current = next((item for item in history if item.get("industry") == current_bucket), {})
    lines = [
        "Industry Propensity Benchmark:",
        f"- Current bucket: {current_bucket}",
        f"- Current score: {format_percent(current.get('score')) if current else 'TBD'} | Submissions: {current.get('submission_count', 'TBD')} | Companies with claims: {current.get('claim_company_count', 'TBD')} | Avg severity: {format_currency(current.get('average_claim_severity'))}",
        f"- Portfolio count: {model.get('portfolio', {}).get('submission_count', 'TBD')} submissions | {model.get('portfolio', {}).get('claim_company_count', 'TBD')} companies with claims",
        "- Industry rows:",
    ]
    for item in history:
        lines.append(
            f"  - {item.get('industry')}: score {format_percent(item.get('score'))}, {item.get('submission_count')} submissions, {item.get('claim_company_count')} with claims, claim rate {format_percent(item.get('attack_frequency'))}, avg severity {format_currency(item.get('average_claim_severity'))}"
        )
    return "\n".join(lines)


def render_portfolio_context(portfolio, submission_id):
    overview = portfolio.get("overview") or {}
    queue = portfolio.get("queue") or []
    dashboard = portfolio.get("dashboard") or {}
    current = next((row for row in queue if row.get("id") == submission_id), {})
    industry_rows = (dashboard.get("industry_mix") or [])[:8]
    return "\n".join(
        [
            "Portfolio Queue And Dashboard:",
            f"- Portfolio submissions: {overview.get('submission_count', 0)} | Ready: {overview.get('ready_count', 0)} | Review: {overview.get('review_count', 0)} | Referral: {overview.get('referral_count', 0)}",
            f"- Average quote readiness: {format_percent(make_number(overview.get('avg_quote_readiness')) / 100)} | Open claims: {overview.get('open_claims', 0)} | Incurred: {format_currency(overview.get('total_incurred'))}",
            f"- Current account queue status: {current.get('priority', 'TBD')} | quote readiness {format_percent(make_number(current.get('quote_readiness')) / 100)} | next action: {current.get('next_action', 'TBD')}",
            "Industry dashboard rows:",
            *[
                f"- {row.get('industry')}: {row.get('submission_count')} submissions | claims {row.get('claim_count')} | avg readiness {format_percent(make_number(row.get('avg_readiness')) / 100)} | incurred {format_currency(row.get('total_incurred'))}"
                for row in industry_rows
            ],
        ]
    )


def render_clearance_context(clearance):
    checks = clearance.get("checks") or []
    matches = clearance.get("possible_matches") or []
    return "\n".join(
        [
            "Clearance Review:",
            f"- Status: {format_label(clearance.get('status'))}",
            f"- Summary: {clearance.get('summary', 'TBD')}",
            "Checks:",
            *[f"- {check.get('label')}: {format_label(check.get('status'))} | {check.get('detail')}" for check in checks],
            "Possible matches:",
            *[
                f"- {match.get('id')}: {match.get('insured_name') or match.get('title')} | {match.get('status')} | similarity {match.get('similarity')}"
                for match in matches
            ],
        ]
    )


def render_rating_quote_context(rating_quote):
    modifiers = rating_quote.get("modifiers") or []
    terms = rating_quote.get("coverage_terms") or []
    subjectivities = rating_quote.get("subjectivities") or []
    premium_range = rating_quote.get("premium_range") or {}
    calculation = rating_quote.get("calculation") or {}
    inputs = calculation.get("inputs") or {}
    return "\n".join(
        [
            "Rating And Quote Package:",
            f"- Engine: {rating_quote.get('rating_engine', 'demo')} | Status: {format_label(rating_quote.get('status'))}",
            f"- Authority path: {rating_quote.get('authority_path', 'Underwriter delegated review')}",
            f"- Quote readiness: {format_percent(make_number(rating_quote.get('quote_readiness')) / 100)}",
            f"- Indicated premium: {format_currency(rating_quote.get('indicated_premium'))} | Range: {format_currency(premium_range.get('low'))} to {format_currency(premium_range.get('high'))}",
            f"- Requested limit: {format_currency(rating_quote.get('requested_limit'))} | Recommended limit: {format_currency(rating_quote.get('recommended_limit'))}",
            f"- Requested retention: {rating_quote.get('requested_retention')} | Recommended retention: {rating_quote.get('recommended_retention')}",
            f"- Pricing formula: {calculation.get('formula', 'Demo factor formula not available')}",
            f"- Base premium: {format_currency(calculation.get('base_premium'))} | Modifier product: {calculation.get('modifier_product', 'TBD')} | Range factors: {calculation.get('range_low_factor', 'TBD')} to {calculation.get('range_high_factor', 'TBD')}",
            f"- Exposure inputs: revenue {format_currency(inputs.get('annual_revenue'))}, records {int(make_number(inputs.get('records_count'))):,}, evidence ratio {format_percent(make_number(inputs.get('evidence_ratio')))}",
            "Rating modifiers:",
            *[f"- {item.get('label')}: factor {item.get('factor')} | {item.get('rationale')}" for item in modifiers],
            "Coverage terms:",
            *[f"- {item.get('coverage')}: {format_currency(item.get('limit'))} | {item.get('condition')}" for item in terms],
            "Subjectivities:",
            *([f"- {item}" for item in subjectivities] if subjectivities else ["- None generated."]),
        ]
    )


def render_external_research_context(external_research):
    profile = external_research.get("profile") or {}
    tasks = external_research.get("research_tasks") or []
    signals = external_research.get("signals_from_submission") or []
    return "\n".join(
        [
            "External Research:",
            f"- Status: {external_research.get('research_status', 'TBD')} | Note: {external_research.get('research_note', '')}",
            f"- Insured: {profile.get('insured_name', 'TBD')} | Industry: {profile.get('industry_bucket') or profile.get('industry', 'TBD')} | Location: {profile.get('location', 'TBD')}",
            "Submission-derived signals:",
            *[f"- {signal}" for signal in signals],
            "Research checklist:",
            *[f"- {item.get('label')}: {format_label(item.get('status'))} | {item.get('detail')}" for item in tasks],
        ]
    )


def render_notes_context(record):
    notes = record.get("notes") or []
    return "\n".join(["Underwriter Notes:", *[f"- {item.get('text', '')}" for item in notes]]) if notes else "Underwriter Notes:\n- No notes saved."


def render_guides_context(record):
    guides = record.get("guides") or []
    return "\n".join(["Guide Instructions:", *[f"- {item.get('text', '')}" for item in guides]]) if guides else "Guide Instructions:\n- No guide instructions saved."


def render_tasks_context(record):
    tasks = record.get("tasks") or []
    return "\n".join(
        ["Scheduled Tasks:", *[f"- {item.get('due_date', 'TBD')} | {format_label(item.get('status'))}: {item.get('title', '')}" for item in tasks]]
    ) if tasks else "Scheduled Tasks:\n- No tasks saved."


def render_stages_context(record):
    stages = record.get("stages") or []
    return "\n".join(
        [
            "Underwriting Stages:",
            f"- Submitted at: {record.get('submitted_at') or 'Not submitted'}",
            *[f"- {'Checked' if item.get('checked') else 'Open'} | {'Locked' if item.get('locked') else 'Editable'}: {item.get('label', item.get('key', 'Stage'))}" for item in stages],
        ]
    ) if stages else "Underwriting Stages:\n- No stage state saved."


def build_feature_lookup(submission, system):
    applicant = submission.get("applicant", {})
    coverage = submission.get("coverage", {})
    controls = submission.get("security_controls", {})
    risk_flags = submission.get("risk_flags") or []
    open_questions = submission.get("open_questions") or []
    claims = system.get("claim_snapshot") or {}
    broker = system.get("broker") or {}
    broker_metrics = broker.get("relationship_metrics") or {}
    evidence = system.get("evidence_status") or []
    revenue = make_number(applicant.get("annual_revenue"))
    records_count = make_number(applicant.get("records_count"))
    requested_limits = [parse_money(value) for value in (coverage.get("requested_limits") or {}).values()]
    requested_limits = [value for value in requested_limits if value > 0]
    max_limit = max(requested_limits) if requested_limits else 0
    mfa_text = normalize_text(controls.get("mfa"))
    edr_text = normalize_text(controls.get("edr"))
    backup_text = normalize_text(controls.get("backup"))
    patching_text = normalize_text(controls.get("patching"))
    training_text = normalize_text(controls.get("security_training"))
    tech_text = normalize_text(applicant.get("technology_profile"))
    industry_bucket = applicant.get("industry_bucket") or applicant.get("industry_group") or resolve_industry_bucket(applicant.get("industry", ""), applicant.get("technology_profile", ""))
    industry_score = get_industry_score(industry_bucket)
    available_evidence = len([item for item in evidence if item.get("status") == "available"])
    evidence_ratio = available_evidence / len(evidence) if evidence else 0.75
    total_incurred = make_number(claims.get("total_incurred"))
    open_claims = make_number(claims.get("open_claims"))
    broker_quality = clamp(make_number(broker_metrics.get("data_quality_score") or 70) / 100, 0, 1)
    broker_response_quality = clamp(1 - make_number(broker_metrics.get("avg_response_hours") or 18) / 48, 0, 1)
    operational_dependency = 0.78 if re.search(r"edi|portal|payment|reservation|warehouse|telematics|property management|ot|remote access|api", tech_text) else 0.32
    risk_flag_load = clamp(len(risk_flags) / 5, 0, 1)
    has_claim_signal = total_incurred > 0 or any(re.search(r"claim|loss|ransom", str(flag), re.I) for flag in risk_flags)
    vendor_dependency = 0.7 if re.search(r"edi|portal|vendor|third party|api", tech_text) or any(re.search(r"third-party|vendor|provider", str(question), re.I) for question in open_questions) else 0.35

    return {
        "revenue_scale": make_feature("Revenue Scale", normalize(revenue, 5_000_000, 500_000_000), format_currency(revenue), revenue),
        "records_exposure": make_feature("Records Exposure", normalize(records_count, 10_000, 1_000_000), format_int(records_count), records_count),
        "mfa_maturity": make_feature("MFA Maturity", 0.45 if "partial" in mfa_text or "pending" in mfa_text else 0.82 if mfa_text else 0.2, controls.get("mfa") or "TBD"),
        "edr_coverage": make_feature("EDR Coverage", 0.84 if "crowdstrike" in edr_text or "deployed" in edr_text else 0.58 if edr_text else 0.25, controls.get("edr") or "TBD"),
        "backup_resilience": make_feature("Backup Resilience", 0.78 if "restore" in backup_text or "immutable" in backup_text else 0.64 if "daily" in backup_text else 0.3, controls.get("backup") or "TBD"),
        "patch_discipline": make_feature("Patch Discipline", 0.76 if "7" in patching_text or "14" in patching_text or "15" in patching_text else 0.58 if "30" in patching_text else 0.48 if patching_text else 0.3, controls.get("patching") or "TBD"),
        "security_training": make_feature("Security Training", 0.72 if "phishing" in training_text else 0.56 if training_text else 0.28, controls.get("security_training") or "TBD"),
        "prior_claims": make_feature("Prior Claims Signal", 0.72 if has_claim_signal else 0.28, "Elevated" if has_claim_signal else "Low / clean"),
        "vendor_dependency": make_feature("Vendor Dependency", vendor_dependency, "Material third-party dependency" if vendor_dependency >= 0.7 else "Limited dependency"),
        "limit_fit": make_feature("Requested Limit Fit", clamp(1 - abs(max_limit / revenue - 0.1) * 2, 0.18, 0.86) if max_limit and revenue else 0.5, f"{format_currency(max_limit)} max requested" if max_limit else "TBD", max_limit),
        "industry_propensity": make_feature("Industry Propensity", industry_score, industry_bucket),
        "risk_flag_load": make_feature("Risk Flag Load", risk_flag_load, f"{len(risk_flags)} flags"),
        "operational_dependency": make_feature("Operational Dependency", operational_dependency, "High dependency" if operational_dependency >= 0.7 else "Lower dependency"),
        "claim_load": make_feature("Historical Claim Load", clamp(total_incurred / 125000, 0, 1), format_currency(total_incurred)),
        "open_claim_signal": make_feature("Open Claim Signal", 0.82 if open_claims else 0.2, f"{int(open_claims)} open" if open_claims else "None open"),
        "evidence_ratio": make_feature("Evidence Confidence", evidence_ratio, f"{available_evidence}/{len(evidence)} available" if evidence else "Evidence TBD"),
        "broker_quality": make_feature("Broker Data Quality", broker_quality, f"{round(broker_quality * 100)}/100"),
        "broker_response_quality": make_feature("Broker Response Quality", broker_response_quality, f"{round(broker_response_quality * 100)}% response score"),
    }


def score_model(model, feature_lookup):
    average_probability = clamp(make_number(model.get("average_probability") or 0.5), 0.01, 0.99)
    base_logit = logit(average_probability)
    steps = []
    for model_feature in model.get("features") or []:
        key = model_feature.get("key")
        feature = feature_lookup.get(key) or make_feature(model_feature.get("label") or key, make_number(model_feature.get("baseline_value") or 0.5), "TBD")
        baseline = make_number(model_feature.get("baseline_value") if model_feature.get("baseline_value") is not None else 0.5)
        coefficient = make_number(model_feature.get("coefficient"))
        contribution = coefficient * (make_number(feature.get("value")) - baseline)
        steps.append(
            {
                "key": key,
                "label": model_feature.get("label") or feature.get("label") or key,
                "display_value": feature.get("display_value", "TBD"),
                "logit_contribution": contribution,
            }
        )
    final_logit = base_logit + sum(step["logit_contribution"] for step in steps)
    return {
        "average_probability": average_probability,
        "probability": sigmoid(final_logit),
        "steps": steps,
    }


def get_industry_score(bucket):
    model = get_model("industry_propensity")
    for item in model.get("industry_history") or []:
        if item.get("industry") == bucket:
            return make_number(item.get("score"))
    return 0.5


def resolve_industry_bucket(industry, technology):
    combined = normalize_text(f"{industry} {technology}")
    if re.search(r"fintech|payment|wallet|merchant", combined):
        return "Fintech / Payments"
    if re.search(r"saas|software|api|technology", combined):
        return "SaaS / Software"
    if re.search(r"health|senior|pharmacy|dental|clinic|patient|hipaa", combined):
        return "Healthcare / Pharmacy"
    if re.search(r"university|college|school|education|student", combined):
        return "Education"
    if re.search(r"manufacturing|industrial|robotics|ot|fabrication", combined):
        return "Manufacturing / OT"
    if re.search(r"food|logistics|freight|warehouse|cold chain", combined):
        return "Food Distribution / Logistics"
    if re.search(r"hospitality|hotel|retail|restaurant|cafe|ecommerce", combined):
        return "Hospitality / Retail"
    if re.search(r"marina|recreation|sailing|yacht", combined):
        return "Marina / Recreation"
    if re.search(r"construction|contracting|siteworks|builders", combined):
        return "Construction"
    return "Professional Services"


def make_feature(label, value, display_value, raw_value=None):
    feature = {"label": label, "value": clamp(make_number(value), 0, 1), "display_value": str(display_value)}
    if raw_value is not None:
        feature["raw_value"] = raw_value
    return feature


def has_any(text, terms):
    return any(term in text for term in terms)


def wants_broker_table(prompt_text):
    if not has_any(prompt_text, ["broker", "producer", "account manager", "market", "relationship"]):
        return False

    return has_any(
        prompt_text,
        [
            "broker table",
            "broker database",
            "broker db",
            "broker list",
            "all broker",
            "all brokers",
            "compare broker",
            "compare brokers",
            "rank broker",
            "rank brokers",
            "ranking",
            "which broker",
            "best broker",
            "worst broker",
            "top broker",
            "highest",
            "lowest",
            "quote ratio",
            "bind ratio",
            "data quality",
            "response",
            "fastest",
            "slowest",
            "market focus",
            "service tier",
            "strategic",
            "wholesale",
            "retail",
            "submissions ytd",
        ],
    )


def resolve_broker_table_metric(prompt_text):
    if has_any(prompt_text, ["bind", "bound"]):
        return "bind_ratio_12m", "Bind ratio", False
    if has_any(prompt_text, ["quote", "quoted"]):
        return "quote_ratio_12m", "Quote ratio", False
    if has_any(prompt_text, ["response", "fastest", "slowest", "turnaround"]):
        return "avg_response_hours", "Average response hours", True
    if has_any(prompt_text, ["submission", "submissions", "volume", "pipeline"]):
        return "submissions_ytd", "YTD submissions", False
    if has_any(prompt_text, ["years", "tenure", "relationship age"]):
        return "years_active", "Years active", False
    return "data_quality_score", "Data quality score", False


def broker_metric_value(broker, metric_key):
    metrics = broker.get("relationship_metrics") or {}
    return make_number(metrics.get(metric_key))


def format_broker_metric(metric_key, value):
    if metric_key in {"quote_ratio_12m", "bind_ratio_12m"}:
        return format_percent(value)
    if metric_key == "avg_response_hours":
        return f"{format_int(value)}h"
    if metric_key == "data_quality_score":
        return f"{format_int(value)}/100"
    return format_int(value)


def dedupe(values):
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def normalize_text(value):
    return re.sub(r"\s+", " ", str(value or "").replace("_", " ").replace("-", " ")).strip().lower()


def normalize(value, minimum, maximum):
    number = make_number(value)
    return clamp((number - minimum) / (maximum - minimum), 0, 1)


def parse_money(value):
    if isinstance(value, (int, float)):
        return float(value)
    return make_number(re.sub(r"[^0-9.]", "", str(value or "")))


def make_number(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def logit(probability):
    probability = clamp(probability, 0.0001, 0.9999)
    return math.log(probability / (1 - probability))


def sigmoid(value):
    return 1 / (1 + math.exp(-value))


def format_currency(value):
    return f"${make_number(value):,.0f}"


def format_percent(value):
    return f"{make_number(value) * 100:.0f}%"


def format_int(value):
    return f"{make_number(value):,.0f}" if value not in (None, "") else "TBD"


def format_limits(limits):
    if not limits:
        return "TBD"
    return ", ".join(f"{format_label(key)}: {value}" for key, value in limits.items())


def format_label(value):
    return " ".join(word.capitalize() for word in str(value or "TBD").replace("_", " ").replace("-", " ").split())
