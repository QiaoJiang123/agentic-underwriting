import json
import sqlite3
from datetime import datetime, timezone

from backend.config import ANALYTICS_DB_PATH, ANALYTICS_DIR
from backend.services.broker_service import get_submission_broker
from backend.services.claim_service import get_claim_record
from backend.services.decision_workflow_service import get_decision_workflow_record
from backend.services.portfolio_workbench_service import get_portfolio_queue, get_rating_quote
from backend.services.submission_service import get_search_metadata, get_submission_detail
from backend.services.underwriting_service import get_underwriting_system_record


SUBMISSION_TABLE = "underwriting_submission_analytics"
CLAIM_TABLE = "claim_analytics"
LEGACY_TABLE = "underwriting_claim_analytics"

SUBMISSION_SCHEMA_SQL = f"""
CREATE TABLE IF NOT EXISTS {SUBMISSION_TABLE} (
    company_id TEXT PRIMARY KEY,
    submission_id TEXT UNIQUE NOT NULL,
    title TEXT,
    insured_name TEXT,
    submission_status TEXT,
    received_at TEXT,
    industry TEXT,
    industry_bucket TEXT,
    location TEXT,
    annual_revenue REAL,
    employee_count INTEGER,
    records_count INTEGER,
    requested_effective_date TEXT,
    requested_limit REAL,
    retention_requested TEXT,
    broker_id TEXT,
    broker_name TEXT,
    producer_name TEXT,
    account_manager_name TEXT,
    service_tier TEXT,
    broker_quote_ratio REAL,
    broker_bind_ratio REAL,
    broker_avg_response_hours REAL,
    broker_data_quality_score REAL,
    evidence_ratio REAL,
    missing_evidence_count INTEGER,
    missing_evidence TEXT,
    risk_signal_count INTEGER,
    queue_priority TEXT,
    queue_next_action TEXT,
    quote_readiness REAL,
    referral_reasons TEXT,
    appetite_status TEXT,
    recommended_authority TEXT,
    underwriting_actions TEXT,
    quote_readiness_status TEXT,
    referral_status TEXT,
    quote_approval_status TEXT,
    bind_readiness_status TEXT,
    indicated_premium REAL,
    premium_low REAL,
    premium_high REAL,
    recommended_limit REAL,
    recommended_retention TEXT,
    rating_status TEXT,
    authority_path TEXT,
    source_files_count INTEGER,
    updated_at TEXT
)
"""

CLAIM_SCHEMA_SQL = f"""
CREATE TABLE IF NOT EXISTS {CLAIM_TABLE} (
    CLM_CLMT_ID TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    submission_id TEXT NOT NULL,
    source_claim_id TEXT,
    claim_system TEXT,
    loss_date TEXT,
    reported_date TEXT,
    status TEXT,
    claim_type TEXT,
    coverage_area TEXT,
    severity TEXT,
    amount_paid REAL,
    amount_reserved REAL,
    incurred REAL,
    cause TEXT,
    description TEXT,
    recovery_status TEXT,
    updated_at TEXT,
    FOREIGN KEY(company_id) REFERENCES {SUBMISSION_TABLE}(company_id)
)
"""


def refresh_analytics_db():
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
    submission_rows, claim_rows = build_analytics_rows()

    with sqlite3.connect(ANALYTICS_DB_PATH) as connection:
        connection.execute(f"DROP TABLE IF EXISTS {LEGACY_TABLE}")
        connection.execute(f"DROP TABLE IF EXISTS {CLAIM_TABLE}")
        connection.execute(f"DROP TABLE IF EXISTS {SUBMISSION_TABLE}")
        connection.execute(SUBMISSION_SCHEMA_SQL)
        connection.execute(CLAIM_SCHEMA_SQL)
        connection.executemany(
            build_insert_sql(SUBMISSION_TABLE, submission_columns()),
            submission_rows,
        )
        connection.executemany(
            build_insert_sql(CLAIM_TABLE, claim_columns()),
            claim_rows,
        )
        connection.commit()

    return get_analytics_db_summary()


def get_analytics_db_summary(refresh=False):
    if refresh or not ANALYTICS_DB_PATH.exists():
        refresh_analytics_db()

    with connect() as connection:
        overview = fetch_one(
            connection,
            f"""
            SELECT
                (SELECT COUNT(*) FROM {SUBMISSION_TABLE}) AS submission_count,
                (SELECT COUNT(*) FROM {CLAIM_TABLE}) AS total_claims,
                (SELECT SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) FROM {CLAIM_TABLE}) AS open_claims,
                (SELECT COALESCE(SUM(incurred), 0) FROM {CLAIM_TABLE}) AS total_incurred,
                (SELECT AVG(quote_readiness) FROM {SUBMISSION_TABLE}) AS avg_quote_readiness,
                (SELECT AVG(indicated_premium) FROM {SUBMISSION_TABLE}) AS avg_indicated_premium
            """,
        )
        priority_rows = fetch_all(
            connection,
            f"""
            WITH claim_agg AS (
                SELECT company_id, COUNT(*) AS claim_count, COALESCE(SUM(incurred), 0) AS incurred
                FROM {CLAIM_TABLE}
                GROUP BY company_id
            )
            SELECT s.queue_priority, COUNT(DISTINCT s.company_id) AS submission_count,
                   COALESCE(SUM(c.claim_count), 0) AS total_claims,
                   COALESCE(SUM(c.incurred), 0) AS total_incurred,
                   AVG(s.quote_readiness) AS avg_quote_readiness
            FROM {SUBMISSION_TABLE} s
            LEFT JOIN claim_agg c ON c.company_id = s.company_id
            GROUP BY s.queue_priority
            ORDER BY submission_count DESC
            """,
        )
        broker_rows = fetch_all(
            connection,
            f"""
            WITH claim_agg AS (
                SELECT company_id, COUNT(*) AS claim_count, COALESCE(SUM(incurred), 0) AS incurred
                FROM {CLAIM_TABLE}
                GROUP BY company_id
            )
            SELECT s.broker_name, COUNT(DISTINCT s.company_id) AS submission_count,
                   COALESCE(SUM(c.claim_count), 0) AS total_claims,
                   COALESCE(SUM(c.incurred), 0) AS total_incurred,
                   AVG(s.quote_readiness) AS avg_quote_readiness
            FROM {SUBMISSION_TABLE} s
            LEFT JOIN claim_agg c ON c.company_id = s.company_id
            GROUP BY s.broker_name
            ORDER BY total_incurred DESC, submission_count DESC
            LIMIT 8
            """,
        )

    return {
        "database_path": str(ANALYTICS_DB_PATH),
        "table_names": [SUBMISSION_TABLE, CLAIM_TABLE],
        "join_key": "company_id",
        "generated_at": utc_now(),
        "row_count": {
            SUBMISSION_TABLE: int(overview.get("submission_count") or 0),
            CLAIM_TABLE: int(overview.get("total_claims") or 0),
        },
        "schemas": get_table_schemas(),
        "overview": overview,
        "priority_summary": priority_rows,
        "broker_summary": broker_rows,
    }


def get_table_schemas():
    if not ANALYTICS_DB_PATH.exists():
        return {}

    with connect() as connection:
        return {
            table_name: [dict(row) for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()]
            for table_name in [SUBMISSION_TABLE, CLAIM_TABLE]
        }


def get_analytics_db_context(submission_id, prompt):
    if not ANALYTICS_DB_PATH.exists():
        refresh_analytics_db()

    prompt_text = str(prompt or "").lower()
    with connect() as connection:
        current = fetch_one(
            connection,
            current_company_sql("WHERE s.submission_id = ?"),
            [submission_id],
        )
        overview = fetch_one(
            connection,
            f"""
            SELECT
                (SELECT COUNT(*) FROM {SUBMISSION_TABLE}) AS submissions,
                (SELECT COUNT(*) FROM {CLAIM_TABLE}) AS claims,
                (SELECT SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) FROM {CLAIM_TABLE}) AS open_claims,
                (SELECT COALESCE(SUM(incurred), 0) FROM {CLAIM_TABLE}) AS incurred,
                (SELECT AVG(quote_readiness) FROM {SUBMISSION_TABLE}) AS avg_readiness,
                (SELECT AVG(indicated_premium) FROM {SUBMISSION_TABLE}) AS avg_premium
            """,
        )
        priority_rows = fetch_all(
            connection,
            f"""
            WITH claim_agg AS (
                SELECT company_id, COUNT(*) AS claim_count, COALESCE(SUM(incurred), 0) AS incurred
                FROM {CLAIM_TABLE}
                GROUP BY company_id
            )
            SELECT s.queue_priority, COUNT(DISTINCT s.company_id) AS submissions,
                   COALESCE(SUM(c.claim_count), 0) AS claims,
                   COALESCE(SUM(c.incurred), 0) AS incurred,
                   AVG(s.quote_readiness) AS avg_readiness
            FROM {SUBMISSION_TABLE} s
            LEFT JOIN claim_agg c ON c.company_id = s.company_id
            GROUP BY s.queue_priority
            ORDER BY submissions DESC
            """,
        )
        broker_rows = fetch_all(
            connection,
            f"""
            WITH claim_agg AS (
                SELECT company_id, COUNT(*) AS claim_count,
                       SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) AS open_claims,
                       COALESCE(SUM(incurred), 0) AS incurred
                FROM {CLAIM_TABLE}
                GROUP BY company_id
            )
            SELECT s.broker_name, COUNT(DISTINCT s.company_id) AS submissions,
                   COALESCE(SUM(c.claim_count), 0) AS claims,
                   COALESCE(SUM(c.open_claims), 0) AS open_claims,
                   COALESCE(SUM(c.incurred), 0) AS incurred,
                   AVG(s.quote_readiness) AS avg_readiness,
                   SUM(CASE WHEN s.queue_priority = 'Referral' THEN 1 ELSE 0 END) AS referral_count,
                   SUM(CASE WHEN s.quote_approval_status = 'ready_for_approval' THEN 1 ELSE 0 END) AS quote_approval_ready
            FROM {SUBMISSION_TABLE} s
            LEFT JOIN claim_agg c ON c.company_id = s.company_id
            GROUP BY s.broker_name
            ORDER BY incurred DESC, submissions DESC
            LIMIT 8
            """,
        )
        industry_rows = fetch_all(
            connection,
            f"""
            WITH claim_agg AS (
                SELECT company_id, COUNT(*) AS claim_count, COALESCE(SUM(incurred), 0) AS incurred
                FROM {CLAIM_TABLE}
                GROUP BY company_id
            )
            SELECT s.industry_bucket, COUNT(DISTINCT s.company_id) AS submissions,
                   COALESCE(SUM(c.claim_count), 0) AS claims,
                   COALESCE(SUM(c.incurred), 0) AS incurred,
                   AVG(s.quote_readiness) AS avg_readiness,
                   SUM(CASE WHEN s.referral_status = 'required' THEN 1 ELSE 0 END) AS referral_required
            FROM {SUBMISSION_TABLE} s
            LEFT JOIN claim_agg c ON c.company_id = s.company_id
            GROUP BY s.industry_bucket
            ORDER BY incurred DESC, submissions DESC
            LIMIT 8
            """,
        )
        decision_rows = fetch_all(
            connection,
            f"""
            WITH claim_agg AS (
                SELECT company_id, COALESCE(SUM(incurred), 0) AS incurred
                FROM {CLAIM_TABLE}
                GROUP BY company_id
            )
            SELECT s.referral_status, s.quote_approval_status, s.bind_readiness_status,
                   COUNT(DISTINCT s.company_id) AS submissions,
                   COALESCE(SUM(c.incurred), 0) AS incurred
            FROM {SUBMISSION_TABLE} s
            LEFT JOIN claim_agg c ON c.company_id = s.company_id
            GROUP BY s.referral_status, s.quote_approval_status, s.bind_readiness_status
            ORDER BY submissions DESC
            LIMIT 8
            """,
        )
        company_rows = find_company_rows(connection, prompt_text, current)

    sections = [
        "Analytics SQL DB:",
        f"- SQLite path: {ANALYTICS_DB_PATH}",
        f"- Tables: {SUBMISSION_TABLE} and {CLAIM_TABLE}",
        f"- Merge skill: join both tables on company_id; use CLM_CLMT_ID for claim-level rows.",
        f"- Portfolio: {overview.get('submissions', 0)} submissions | {overview.get('claims', 0)} claims | {format_money(overview.get('incurred'))} incurred | avg quote readiness {format_percent(overview.get('avg_readiness'))}",
    ]

    if current:
        sections.extend(
            [
                "Current submission joined row:",
                (
                    f"- {current.get('submission_id')} / {current.get('company_id')}: {current.get('insured_name')} | "
                    f"broker {current.get('broker_name')} | priority {current.get('queue_priority')} | "
                    f"readiness {format_percent(current.get('quote_readiness'))} | claims {current.get('total_claims')} | "
                    f"incurred {format_money(current.get('total_incurred'))} | quote approval {current.get('quote_approval_status')} | "
                    f"bind readiness {current.get('bind_readiness_status')}"
                ),
            ]
        )

    sections.extend(["Priority statistics from joined tables:", *format_group_rows(priority_rows, "queue_priority")])
    sections.extend(["Broker statistics from joined tables:", *format_group_rows(broker_rows, "broker_name")])

    if wants_industry(prompt_text):
        sections.extend(["Industry statistics from joined tables:", *format_group_rows(industry_rows, "industry_bucket")])

    if wants_decision(prompt_text):
        sections.extend(["Decision workflow statistics from joined tables:", *format_decision_rows(decision_rows)])

    if company_rows:
        sections.extend(["Matched company rows from joined tables:", *format_company_rows(company_rows)])

    return {
        "context": "\n".join(sections),
        "sources": [
            {"skill": "analytics_db", "source": str(ANALYTICS_DB_PATH)},
            {"skill": "analytics_db", "source": f"sqlite://{SUBMISSION_TABLE}"},
            {"skill": "analytics_db", "source": f"sqlite://{CLAIM_TABLE}"},
            {"skill": "analytics_db", "source": f"join:{SUBMISSION_TABLE}.company_id={CLAIM_TABLE}.company_id"},
        ],
        "selection": {
            "table_names": [SUBMISSION_TABLE, CLAIM_TABLE],
            "join_key": "company_id",
            "claim_primary_key": "CLM_CLMT_ID",
            "row_count": {
                SUBMISSION_TABLE: int(overview.get("submissions") or 0),
                CLAIM_TABLE: int(overview.get("claims") or 0),
            },
            "database_path": str(ANALYTICS_DB_PATH),
        },
    }


def build_analytics_rows():
    queue = get_portfolio_queue().get("queue") or []
    queue_by_id = {row.get("id"): row for row in queue}
    submission_rows = []
    claim_rows = []
    for item in get_search_metadata().get("submissions", []):
        submission_id = item.get("id")
        if not submission_id:
            continue
        try:
            submission_row, submission_claim_rows = build_submission_and_claim_rows(
                submission_id,
                queue_by_id.get(submission_id, {}),
            )
            submission_rows.append(submission_row)
            claim_rows.extend(submission_claim_rows)
        except (FileNotFoundError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            continue
    return submission_rows, claim_rows


def build_submission_and_claim_rows(submission_id, queue_row):
    submission = get_submission_detail(submission_id)["submission"]
    applicant = submission.get("applicant") or {}
    coverage = submission.get("coverage") or {}
    broker = get_submission_broker(submission) or {}
    broker_metrics = broker.get("relationship_metrics") or {}
    broker_contact = broker.get("submission_contact") or submission.get("broker") or {}
    claims = get_claim_record(submission_id)
    claim_rows = claims.get("claims") or []
    system = get_underwriting_system_record(submission_id)
    appetite = system.get("appetite") or {}
    evidence = system.get("evidence_status") or []
    actions = system.get("recommended_actions") or []
    workflow = get_decision_workflow_record(submission_id)
    decisions = {gate.get("key"): gate for gate in workflow.get("gates") or []}
    rating = get_rating_quote(submission_id)
    premium_range = rating.get("premium_range") or {}
    requested_limit = max([parse_money(value) for value in (coverage.get("requested_limits") or {}).values()] or [0])
    missing_evidence = [item.get("label") for item in evidence if item.get("status") == "missing"]
    company_id = company_id_for_submission(submission_id)
    now = utc_now()

    submission_row = {
        "company_id": company_id,
        "submission_id": submission_id,
        "title": submission.get("title"),
        "insured_name": applicant.get("insured_name"),
        "submission_status": submission.get("status"),
        "received_at": submission.get("received_at"),
        "industry": applicant.get("industry"),
        "industry_bucket": applicant.get("industry_bucket") or applicant.get("industry_group") or queue_row.get("industry_bucket"),
        "location": applicant.get("location"),
        "annual_revenue": make_number(applicant.get("annual_revenue")),
        "employee_count": int(make_number(applicant.get("employee_count"))),
        "records_count": int(make_number(applicant.get("records_count"))),
        "requested_effective_date": coverage.get("requested_effective_date"),
        "requested_limit": requested_limit,
        "retention_requested": coverage.get("retention_requested"),
        "broker_id": broker.get("broker_id") or broker_contact.get("broker_id"),
        "broker_name": broker.get("firm_name") or broker_contact.get("firm_name"),
        "producer_name": broker_contact.get("producer_name") or ((broker.get("contacts") or {}).get("producer") or {}).get("name"),
        "account_manager_name": broker_contact.get("account_manager_name") or ((broker.get("contacts") or {}).get("account_manager") or {}).get("name"),
        "service_tier": broker.get("service_tier") or broker_contact.get("broker_priority"),
        "broker_quote_ratio": make_number(broker_metrics.get("quote_ratio_12m")),
        "broker_bind_ratio": make_number(broker_metrics.get("bind_ratio_12m")),
        "broker_avg_response_hours": make_number(broker_metrics.get("avg_response_hours")),
        "broker_data_quality_score": make_number(broker_metrics.get("data_quality_score")),
        "evidence_ratio": make_number(queue_row.get("evidence_ratio")),
        "missing_evidence_count": len(missing_evidence),
        "missing_evidence": json.dumps(missing_evidence),
        "risk_signal_count": int(make_number(queue_row.get("risk_signal_count"))),
        "queue_priority": queue_row.get("priority"),
        "queue_next_action": queue_row.get("next_action"),
        "quote_readiness": make_number(queue_row.get("quote_readiness")),
        "referral_reasons": json.dumps(queue_row.get("referral_reasons") or []),
        "appetite_status": appetite.get("status"),
        "recommended_authority": appetite.get("recommended_authority"),
        "underwriting_actions": json.dumps(actions),
        "quote_readiness_status": (decisions.get("quote_readiness") or {}).get("status"),
        "referral_status": (decisions.get("referral") or {}).get("status"),
        "quote_approval_status": (decisions.get("quote_approval") or {}).get("status"),
        "bind_readiness_status": (decisions.get("bind_readiness") or {}).get("status"),
        "indicated_premium": make_number(rating.get("indicated_premium")),
        "premium_low": make_number(premium_range.get("low")),
        "premium_high": make_number(premium_range.get("high")),
        "recommended_limit": make_number(rating.get("recommended_limit")),
        "recommended_retention": rating.get("recommended_retention"),
        "rating_status": rating.get("status"),
        "authority_path": rating.get("authority_path"),
        "source_files_count": len(submission.get("documents") or []),
        "updated_at": now,
    }

    claim_table_rows = [
        build_claim_row(company_id, submission_id, claims, claim, index, now)
        for index, claim in enumerate(claim_rows)
    ]

    return submission_row, claim_table_rows


def build_claim_row(company_id, submission_id, claim_record, claim, index, now):
    source_claim_id = str(claim.get("claim_id") or "").strip()
    claim_id = source_claim_id or f"{company_id}-CLM-{index + 1:03d}"
    return {
        "CLM_CLMT_ID": claim_id,
        "company_id": company_id,
        "submission_id": submission_id,
        "source_claim_id": source_claim_id,
        "claim_system": claim_record.get("claim_system"),
        "loss_date": claim.get("loss_date"),
        "reported_date": claim.get("reported_date"),
        "status": claim.get("status"),
        "claim_type": claim.get("claim_type"),
        "coverage_area": claim.get("coverage_area"),
        "severity": claim.get("severity"),
        "amount_paid": make_number(claim.get("amount_paid")),
        "amount_reserved": make_number(claim.get("amount_reserved")),
        "incurred": make_number(claim.get("amount_paid")) + make_number(claim.get("amount_reserved")),
        "cause": claim.get("cause"),
        "description": claim.get("description"),
        "recovery_status": claim.get("recovery_status"),
        "updated_at": now,
    }


def build_insert_sql(table_name, columns):
    placeholders = ", ".join(f":{column}" for column in columns)
    column_names = ", ".join(columns)
    return f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"


def submission_columns():
    return [
        "company_id",
        "submission_id",
        "title",
        "insured_name",
        "submission_status",
        "received_at",
        "industry",
        "industry_bucket",
        "location",
        "annual_revenue",
        "employee_count",
        "records_count",
        "requested_effective_date",
        "requested_limit",
        "retention_requested",
        "broker_id",
        "broker_name",
        "producer_name",
        "account_manager_name",
        "service_tier",
        "broker_quote_ratio",
        "broker_bind_ratio",
        "broker_avg_response_hours",
        "broker_data_quality_score",
        "evidence_ratio",
        "missing_evidence_count",
        "missing_evidence",
        "risk_signal_count",
        "queue_priority",
        "queue_next_action",
        "quote_readiness",
        "referral_reasons",
        "appetite_status",
        "recommended_authority",
        "underwriting_actions",
        "quote_readiness_status",
        "referral_status",
        "quote_approval_status",
        "bind_readiness_status",
        "indicated_premium",
        "premium_low",
        "premium_high",
        "recommended_limit",
        "recommended_retention",
        "rating_status",
        "authority_path",
        "source_files_count",
        "updated_at",
    ]


def claim_columns():
    return [
        "CLM_CLMT_ID",
        "company_id",
        "submission_id",
        "source_claim_id",
        "claim_system",
        "loss_date",
        "reported_date",
        "status",
        "claim_type",
        "coverage_area",
        "severity",
        "amount_paid",
        "amount_reserved",
        "incurred",
        "cause",
        "description",
        "recovery_status",
        "updated_at",
    ]


def current_company_sql(where_clause):
    return f"""
        SELECT s.*,
               COUNT(c.CLM_CLMT_ID) AS total_claims,
               SUM(CASE WHEN c.status = 'open' THEN 1 ELSE 0 END) AS open_claims,
               COALESCE(SUM(c.amount_paid), 0) AS total_paid,
               COALESCE(SUM(c.amount_reserved), 0) AS total_reserved,
               COALESCE(SUM(c.incurred), 0) AS total_incurred
        FROM {SUBMISSION_TABLE} s
        LEFT JOIN {CLAIM_TABLE} c ON c.company_id = s.company_id
        {where_clause}
        GROUP BY s.company_id
    """


def find_company_rows(connection, prompt_text, current):
    rows = []
    if current:
        rows.append(current)

    tokens = [
        token
        for token in re_like_tokens(prompt_text)
        if len(token) >= 4 and token not in {"claim", "claims", "broker", "underwriting", "company", "statistics"}
    ][:6]
    for token in tokens:
        rows.extend(
            fetch_all(
                connection,
                current_company_sql(
                    "WHERE LOWER(s.insured_name) LIKE ? OR LOWER(s.title) LIKE ? OR LOWER(s.broker_name) LIKE ?"
                )
                + " LIMIT 5",
                [f"%{token}%", f"%{token}%", f"%{token}%"],
            )
        )

    seen = set()
    unique = []
    for row in rows:
        if row.get("company_id") not in seen:
            unique.append(row)
            seen.add(row.get("company_id"))
    return unique[:6]


def connect():
    connection = sqlite3.connect(ANALYTICS_DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def fetch_one(connection, sql, params=None):
    row = connection.execute(sql, params or []).fetchone()
    return dict(row) if row else {}


def fetch_all(connection, sql, params=None):
    return [dict(row) for row in connection.execute(sql, params or []).fetchall()]


def format_group_rows(rows, label_key):
    if not rows:
        return ["- No rows."]
    formatted = []
    for row in rows:
        formatted.append(
            f"- {row.get(label_key) or 'Unknown'}: {int(row.get('submissions') or row.get('submission_count') or 0)} submissions | "
            f"{int(row.get('claims') or row.get('total_claims') or 0)} claims | "
            f"{format_money(row.get('incurred') or row.get('total_incurred'))} incurred | "
            f"avg readiness {format_percent(row.get('avg_readiness') or row.get('avg_quote_readiness'))}"
        )
    return formatted


def format_decision_rows(rows):
    if not rows:
        return ["- No decision rows."]
    return [
        (
            f"- Referral {row.get('referral_status')}; quote approval {row.get('quote_approval_status')}; "
            f"bind {row.get('bind_readiness_status')}: {int(row.get('submissions') or 0)} submissions | "
            f"{format_money(row.get('incurred'))} incurred"
        )
        for row in rows
    ]


def format_company_rows(rows):
    return [
        (
            f"- {row.get('submission_id')} / {row.get('company_id')}: {row.get('insured_name')} | {row.get('broker_name')} | "
            f"{row.get('queue_priority')} | claims {row.get('total_claims')} | incurred {format_money(row.get('total_incurred'))} | "
            f"referral {row.get('referral_status')} | quote approval {row.get('quote_approval_status')}"
        )
        for row in rows
    ]


def wants_industry(prompt_text):
    return any(term in prompt_text for term in ["industry", "industries", "sector", "benchmark"])


def wants_decision(prompt_text):
    return any(term in prompt_text for term in ["decision", "quote approval", "bind", "referral", "readiness", "authority"])


def re_like_tokens(prompt_text):
    return [token.strip() for token in str(prompt_text or "").replace("/", " ").replace("-", " ").split()]


def company_id_for_submission(submission_id):
    cleaned = str(submission_id or "").upper().replace("-", "_")
    return f"CMP_{cleaned}"


def parse_money(value):
    try:
        return float("".join(character for character in str(value or "") if character.isdigit() or character == ".") or 0)
    except (TypeError, ValueError):
        return 0.0


def make_number(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def format_money(value):
    return f"${make_number(value):,.0f}"


def format_percent(value):
    return f"{make_number(value):.1f}%"


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
