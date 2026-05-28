from dataclasses import dataclass, field


REGISTRY_VERSION = "0.1.0"
READ_TOOL = "read"
WRITE_TOOL = "write"
SUBMISSION_SCOPE = "submission"
GLOBAL_SCOPE = "global"
INTERNAL_BACKEND = "internal_python"
MCP_READY_BACKEND = "internal_python_mcp_ready"


@dataclass(frozen=True)
class AgentTool:
    skill: str
    label: str
    description: str
    required_permission: str
    access_scope: str = SUBMISSION_SCOPE
    tool_type: str = READ_TOOL
    backend: str = INTERNAL_BACKEND
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)
    citation_policy: str = "Return source path, record id, and field or document names where available."
    mcp_exposed: bool = False
    mcp_tool_name: str | None = None
    write_requires_confirmation: bool = False

    def to_contract(self, compact=False):
        contract = {
            "skill": self.skill,
            "label": self.label,
            "description": self.description,
            "required_permission": self.required_permission,
            "access_scope": self.access_scope,
            "tool_type": self.tool_type,
            "backend": self.backend,
            "citation_policy": self.citation_policy,
            "mcp_exposed": self.mcp_exposed,
            "mcp_tool_name": self.mcp_tool_name,
            "write_requires_confirmation": self.write_requires_confirmation,
        }
        if not compact:
            contract["input_schema"] = self.input_schema
            contract["output_schema"] = self.output_schema
        return contract


def submission_input_schema(extra=None):
    properties = {
        "submission_id": {"type": "string", "description": "Submission id such as 001-acme-foods."},
    }
    required = ["submission_id"]
    if extra:
        properties.update(extra.get("properties", {}))
        required.extend(extra.get("required", []))
    return {
        "type": "object",
        "required": required,
        "properties": properties,
        "additionalProperties": False,
    }


def global_input_schema(extra=None):
    properties = {}
    required = []
    if extra:
        properties.update(extra.get("properties", {}))
        required.extend(extra.get("required", []))
    return {
        "type": "object",
        "required": required,
        "properties": properties,
        "additionalProperties": False,
    }


def context_output_schema(section_name):
    return {
        "type": "object",
        "required": ["context", "sources"],
        "properties": {
            "context": {"type": "string", "description": section_name},
            "sources": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "skill": {"type": "string"},
                        "source": {"type": "string"},
                        "record_id": {"type": "string"},
                        "field": {"type": "string"},
                    },
                },
            },
        },
    }


def write_output_schema(record_name):
    return {
        "type": "object",
        "required": ["ok", record_name],
        "properties": {
            "ok": {"type": "boolean"},
            record_name: {"type": "object"},
            "sources": {"type": "array"},
        },
    }


TOOLS = [
    AgentTool(
        "account_summary",
        "Account Summary",
        "Read core submission metadata and key account facts.",
        "submission:read",
        input_schema=submission_input_schema(),
        output_schema=context_output_schema("Account summary context."),
    ),
    AgentTool(
        "status",
        "Submission Current Status",
        "Read metadata, claims, task, stage, and underwriting status for where the account stands.",
        "submission:read",
        input_schema=submission_input_schema(),
        output_schema=context_output_schema("Current status context."),
    ),
    AgentTool(
        "documents",
        "Relevant Documents",
        "Select and read submitted documents based on fixed selection or Auto metadata matching.",
        "submission:read",
        backend=MCP_READY_BACKEND,
        input_schema=submission_input_schema(
            {
                "properties": {
                    "prompt": {"type": "string"},
                    "selected_files": {"type": "array", "items": {"type": "string"}},
                    "file_selection_mode": {"type": "string", "enum": ["auto", "all", "none", "fixed"]},
                    "max_documents": {"type": "integer", "minimum": 1, "maximum": 12},
                },
                "required": ["prompt"],
            }
        ),
        output_schema=context_output_schema("Selected document text and metadata."),
        citation_policy="Return each selected file name and metadata category used by the answer.",
        mcp_exposed=True,
        mcp_tool_name="select_documents/read_selected_documents",
    ),
    AgentTool(
        "document_completeness",
        "Document Completeness",
        "Compare submitted documents against required commercial cyber evidence categories.",
        "submission:read",
        input_schema=submission_input_schema(),
        output_schema=context_output_schema("Missing and received evidence checklist."),
        citation_policy="Return requirement file path plus submitted document metadata source.",
    ),
    AgentTool(
        "underwriting",
        "Underwriting Workbench",
        "Read appetite, control baseline, broker, claim, and recommended action context.",
        "submission:read",
        input_schema=submission_input_schema(),
        output_schema=context_output_schema("Underwriting workbench context."),
    ),
    AgentTool(
        "decision_workflow",
        "Decision Workflow",
        "Read quote readiness, referral, quote approval, and bind readiness gates.",
        "submission:read",
        input_schema=submission_input_schema(),
        output_schema=context_output_schema("Decision workflow context."),
    ),
    AgentTool(
        "claims",
        "Claim History",
        "Read linked claim-system rows for the selected company.",
        "submission:read",
        input_schema=submission_input_schema(),
        output_schema=context_output_schema("Claim history context."),
        citation_policy="Return claim ids, claim record path, and claim-system update timestamp.",
    ),
    AgentTool(
        "broker",
        "Broker Profile",
        "Read the broker linked to the current submission.",
        "broker:read",
        access_scope=GLOBAL_SCOPE,
        input_schema=submission_input_schema(),
        output_schema=context_output_schema("Submission broker context."),
    ),
    AgentTool(
        "broker_table",
        "Broker Database Table",
        "Read broker database rows for cross-broker questions and statistics.",
        "broker:read",
        access_scope=GLOBAL_SCOPE,
        input_schema=global_input_schema({"properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}),
        output_schema=context_output_schema("Broker database table context."),
    ),
    AgentTool(
        "analytics",
        "Analytics Models",
        "Read quote, bind, supplemental GLM, and industry propensity model outputs.",
        "analytics:read",
        access_scope=GLOBAL_SCOPE,
        input_schema=submission_input_schema(),
        output_schema=context_output_schema("Analytics model context."),
    ),
    AgentTool(
        "portfolio",
        "Portfolio Queue",
        "Read portfolio queue and dashboard metrics.",
        "portfolio:read",
        access_scope=GLOBAL_SCOPE,
        input_schema=submission_input_schema(),
        output_schema=context_output_schema("Portfolio queue context."),
    ),
    AgentTool(
        "analytics_db",
        "Underwriting Claim Analytics DB",
        "Query the two-table SQLite analytics mart and join submissions to claims by company id.",
        "analytics:read",
        access_scope=GLOBAL_SCOPE,
        input_schema=submission_input_schema({"properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}),
        output_schema=context_output_schema("SQL analytics context."),
        citation_policy="Return table names, join key, SQL summary, and selected rows used.",
    ),
    AgentTool(
        "clearance",
        "Clearance Review",
        "Read duplicate scan, broker appointment, effective-date, evidence, and claim clearance checks.",
        "submission:read",
        input_schema=submission_input_schema(),
        output_schema=context_output_schema("Clearance review context."),
    ),
    AgentTool(
        "rating_quote",
        "Rating And Quote",
        "Read demo premium calculation, modifiers, coverage terms, retention, authority, and subjectivities.",
        "submission:read",
        input_schema=submission_input_schema(),
        output_schema=context_output_schema("Rating and quote context."),
    ),
    AgentTool(
        "external_research",
        "External Research Checklist",
        "Read connector-ready external research checks and submission-derived enrichment signals.",
        "submission:read",
        input_schema=submission_input_schema(),
        output_schema=context_output_schema("External research context."),
    ),
    AgentTool(
        "sop",
        "SOP Guidance",
        "Retrieve relevant commercial cyber SOP steps and broker follow-up templates.",
        "sop:read",
        access_scope=GLOBAL_SCOPE,
        input_schema=global_input_schema({"properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}),
        output_schema=context_output_schema("SOP guidance context."),
    ),
    AgentTool(
        "notes",
        "Underwriter Notes",
        "Read underwriter-supplied ground-truth notes for the submission.",
        "submission:read",
        input_schema=submission_input_schema(),
        output_schema=context_output_schema("Underwriter notes context."),
    ),
    AgentTool(
        "guides",
        "Prompt Guides",
        "Read submission-specific prompt guide instructions.",
        "submission:read",
        input_schema=submission_input_schema(),
        output_schema=context_output_schema("Prompt guide context."),
    ),
    AgentTool(
        "tasks",
        "Scheduled Tasks",
        "Read saved underwriting tasks and calendar due dates.",
        "submission:read",
        input_schema=submission_input_schema(),
        output_schema=context_output_schema("Scheduled task context."),
    ),
    AgentTool(
        "stages",
        "Underwriting Stages",
        "Read workflow stage checklist and locked stage state.",
        "submission:read",
        input_schema=submission_input_schema(),
        output_schema=context_output_schema("Stage state context."),
    ),
    AgentTool(
        "write_note",
        "Add Or Edit Note",
        "Write underwriter note records. Notes become ground-truth context for future turns.",
        "submission:write",
        tool_type=WRITE_TOOL,
        backend=MCP_READY_BACKEND,
        input_schema=submission_input_schema({"properties": {"text": {"type": "string"}}, "required": ["text"]}),
        output_schema=write_output_schema("note"),
        mcp_exposed=True,
        mcp_tool_name="add_underwriter_note",
        write_requires_confirmation=False,
    ),
    AgentTool(
        "write_guide",
        "Add Or Edit Guide",
        "Write guide instructions that are sent as system-level guidance on future turns.",
        "submission:write",
        tool_type=WRITE_TOOL,
        backend=MCP_READY_BACKEND,
        input_schema=submission_input_schema({"properties": {"text": {"type": "string"}}, "required": ["text"]}),
        output_schema=write_output_schema("guide"),
        mcp_exposed=True,
        mcp_tool_name="add_guide_instruction",
        write_requires_confirmation=False,
    ),
    AgentTool(
        "write_task",
        "Add Or Edit Task",
        "Write scheduled underwriting tasks.",
        "submission:write",
        tool_type=WRITE_TOOL,
        backend=MCP_READY_BACKEND,
        input_schema=submission_input_schema(
            {"properties": {"title": {"type": "string"}, "due_date": {"type": "string"}}, "required": ["title", "due_date"]}
        ),
        output_schema=write_output_schema("task"),
        mcp_exposed=True,
        mcp_tool_name="add_scheduled_task",
        write_requires_confirmation=False,
    ),
    AgentTool(
        "update_submission_metadata",
        "Update Submission Metadata",
        "Write editable metadata cells such as status, revenue, controls, flags, and open questions.",
        "submission:write",
        tool_type=WRITE_TOOL,
        input_schema=submission_input_schema({"properties": {"updates": {"type": "object"}}, "required": ["updates"]}),
        output_schema=write_output_schema("submission"),
        write_requires_confirmation=True,
    ),
    AgentTool(
        "submit_stages",
        "Submit Checked Stages",
        "Permanently lock checked underwriting stages.",
        "submission:write",
        tool_type=WRITE_TOOL,
        input_schema=submission_input_schema({"properties": {"stages": {"type": "array"}}, "required": ["stages"]}),
        output_schema=write_output_schema("stages"),
        write_requires_confirmation=True,
    ),
    AgentTool(
        "upload_document",
        "Upload Document",
        "Save an uploaded document, extract text, and write document metadata.",
        "submission:write",
        tool_type=WRITE_TOOL,
        input_schema=submission_input_schema({"properties": {"file_name": {"type": "string"}}, "required": ["file_name"]}),
        output_schema=write_output_schema("document"),
        write_requires_confirmation=True,
    ),
    AgentTool(
        "delete_document",
        "Delete Document",
        "Delete a submission file and remove matching document metadata.",
        "submission:write",
        tool_type=WRITE_TOOL,
        input_schema=submission_input_schema({"properties": {"file_name": {"type": "string"}}, "required": ["file_name"]}),
        output_schema=write_output_schema("delete"),
        write_requires_confirmation=True,
    ),
]

TOOL_BY_SKILL = {tool.skill: tool for tool in TOOLS}
ACTION_TOOL_MAP = {
    "note": "write_note",
    "guide": "write_guide",
    "task": "write_task",
    "metadata_update": "update_submission_metadata",
    "update_submission_metadata": "update_submission_metadata",
    "submit_stages": "submit_stages",
    "upload_document": "upload_document",
    "delete_document": "delete_document",
}


def get_agent_tool_registry_record():
    tools = list_agent_tools()
    return {
        "version": REGISTRY_VERSION,
        "description": "Typed permission-aware tool contracts for the centralized underwriting information agent.",
        "contract_fields": [
            "skill",
            "label",
            "description",
            "required_permission",
            "access_scope",
            "tool_type",
            "backend",
            "input_schema",
            "output_schema",
            "citation_policy",
            "mcp_exposed",
            "mcp_tool_name",
            "write_requires_confirmation",
        ],
        "tools": tools,
        "summary": summarize_tools(tools),
    }


def list_agent_tools(compact=False):
    return [tool.to_contract(compact=compact) for tool in TOOLS]


def get_agent_tool(skill, compact=False):
    tool = TOOL_BY_SKILL.get(skill)
    if not tool:
        return None
    return tool.to_contract(compact=compact)


def get_action_tool(action_type, compact=False):
    return get_agent_tool(ACTION_TOOL_MAP.get(action_type, action_type), compact=compact)


def tool_contracts_for_plan(plan, compact=True):
    return [contract for contract in (get_agent_tool(skill, compact=compact) for skill in plan or []) if contract]


def tool_permissions_for_plan(plan):
    return {skill: required_permission_for_skill(skill) for skill in plan or []}


def required_permission_for_skill(skill):
    tool = TOOL_BY_SKILL.get(skill)
    return tool.required_permission if tool else "api:access"


def scoped_submission_for_skill(skill, submission_id):
    tool = TOOL_BY_SKILL.get(skill)
    if not tool:
        return submission_id if required_permission_for_skill(skill).startswith("submission:") else None
    return submission_id if tool.access_scope == SUBMISSION_SCOPE else None


def summarize_tools(tools):
    return {
        "tool_count": len(tools),
        "read_tool_count": sum(1 for tool in tools if tool.get("tool_type") == READ_TOOL),
        "write_tool_count": sum(1 for tool in tools if tool.get("tool_type") == WRITE_TOOL),
        "mcp_ready_count": sum(1 for tool in tools if tool.get("mcp_exposed")),
        "permission_count": len({tool.get("required_permission") for tool in tools}),
    }
