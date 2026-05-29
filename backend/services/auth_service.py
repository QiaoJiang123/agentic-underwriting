import json
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from hashlib import pbkdf2_hmac

from backend.config import AUTH_DB_PATH, AUTH_POLICY_PATH, SECURITY_DIR


SESSION_COOKIE_NAME = "au_session"
SESSION_HOURS = 12
PASSWORD_ITERATIONS = 120_000
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "AU-Admin-2026!"


ROUTE_RULES = [
    ("GET", r"^/api/auth/context$", "auth:read"),
    ("POST", r"^/api/auth/login$", "public"),
    ("POST", r"^/api/auth/logout$", "auth:read"),
    ("GET", r"^/api/submissions$", "submission:list"),
    ("POST", r"^/api/submissions$", "submission:create"),
    ("GET", r"^/api/search-metadata$", "submission:list"),
    ("GET", r"^/api/portfolio/queue$", "portfolio:read"),
    ("GET", r"^/api/analytics-db$", "analytics:read"),
    ("POST", r"^/api/analytics-db/refresh$", "analytics:read"),
    ("GET", r"^/api/intake/(bootstrap|status)$", "intake:read"),
    ("PUT", r"^/api/intake/status$", "intake:write"),
    ("POST", r"^/api/intake/(draft|draft-file|review|submissions)$", "intake:write"),
    ("GET", r"^/api/dev/(submissions|catalog|agent-traces)$", "dev:read"),
    ("POST", r"^/api/dev/intake-uploads/cleanup$", "dev:delete"),
    ("DELETE", r"^/api/dev/submissions/([^/]+)$", "dev:delete"),
    ("GET", r"^/api/brokers$", "broker:read"),
    ("GET", r"^/api/agent-skills$", "agent:read"),
    ("GET", r"^/api/agent-tools$", "agent:read"),
    ("GET", r"^/api/sop$", "sop:read"),
    ("GET", r"^/api/schemas$", "schema:read"),
    ("GET", r"^/api/intake-status$", "intake:read"),
    ("PUT", r"^/api/intake-status$", "intake:write"),
    ("GET", r"^/api/model-governance$", "model:read"),
    ("GET", r"^/api/models/([^/]+)(/governance)?$", "model:read"),
    ("POST", r"^/api/chat$", "chat:use"),
    ("GET", r"^/api/submissions/([^/]+)$", "submission:read"),
    ("DELETE", r"^/api/submissions/([^/]+)$", "submission:delete"),
    ("GET", r"^/api/submissions/([^/]+)/files/([^/]+)$", "submission:read"),
    ("POST", r"^/api/submissions/([^/]+)/(files|insights/refresh|chat-history|auto-select-documents|states/submit)$", "submission:write"),
    ("DELETE", r"^/api/submissions/([^/]+)/files/([^/]+)$", "submission:write"),
    ("DELETE", r"^/api/submissions/([^/]+)/chat-history/([^/]+)$", "submission:write"),
    ("GET", r"^/api/submissions/([^/]+)/(claims|underwriting|clearance|external-research|rating-quote|decision-workflow|decision-package|chat-history|agent-traces|guides|notes|tasks|states)$", "submission:read"),
    ("GET", r"^/api/submissions/([^/]+)/(chat-history|agent-traces)/([^/]+)$", "submission:read"),
    ("PUT", r"^/api/submissions/([^/]+)/(decision-workflow|metadata-cells|guides|notes|tasks|states)$", "submission:write"),
]


def authorize_request(request):
    context = resolve_auth_context(request)
    path = request.url.path
    method = request.method.upper()

    if method == "OPTIONS" or not path.startswith("/api/"):
        return allow(context, "public", None, None)

    permission, submission_id = resolve_required_permission(method, path)
    if permission == "public":
        return allow(context, permission, submission_id, "Public authentication route.")
    if not permission:
        permission = "api:access"

    if permission not in context["permissions"]:
        return deny(context, permission, submission_id, f"Missing permission {permission}.")

    if submission_id and not can_access_submission(context, submission_id):
        return deny(context, permission, submission_id, f"Submission {submission_id} is outside user scope.")

    return allow(context, permission, submission_id, None)


def resolve_auth_context(request):
    policy = load_auth_policy()
    session_user_id = resolve_session_user_id(request)
    user_id = (
        request.headers.get("x-au-user")
        or session_user_id
        or request.query_params.get("as_user")
        or policy.get("default_user_id")
        or "uw-demo"
    )
    users = {user.get("user_id"): user for user in policy.get("users", [])}
    user = users.get(user_id) or users.get(policy.get("default_user_id")) or {}
    role = user.get("role", "senior_underwriter")
    role_record = (policy.get("roles") or {}).get(role, {})
    permissions = sorted(set(role_record.get("permissions", [])))

    return {
        "user_id": user.get("user_id", user_id),
        "display_name": user.get("display_name", user_id),
        "role": role,
        "role_label": role_record.get("label", role),
        "team": user.get("team"),
        "submission_scope": user.get("submission_scope", []),
        "permissions": permissions,
        "auth_source": resolve_auth_source(request, session_user_id),
    }


def resolve_auth_source(request, session_user_id):
    if request.headers.get("x-au-user"):
        return "x-au-user header"
    if session_user_id:
        return "local login session"
    if request.query_params.get("as_user"):
        return "as_user query parameter"
    return "local default user"


def resolve_required_permission(method, path):
    for rule_method, pattern, permission in ROUTE_RULES:
        if rule_method != method:
            continue
        match = re.match(pattern, path)
        if match:
            return permission, first_submission_id(match.groups())
    return None, None


def first_submission_id(groups):
    for value in groups:
        if value and re.match(r"^[0-9]{3}-[a-z0-9-]+$", value):
            return value
    return None


def can_access_submission(context, submission_id):
    scope = context.get("submission_scope") or []
    return "*" in scope or submission_id in scope


def require_permission(context, permission, submission_id=None):
    if permission not in (context or {}).get("permissions", []):
        raise PermissionError(f"Missing permission {permission}.")
    if submission_id and not can_access_submission(context, submission_id):
        raise PermissionError(f"Submission {submission_id} is outside user scope.")
    return True


def skill_permissions_for_plan(plan):
    from backend.services.agent_tool_registry import tool_permissions_for_plan

    return tool_permissions_for_plan(plan)


def skill_required_permission(skill):
    from backend.services.agent_tool_registry import required_permission_for_skill

    return required_permission_for_skill(skill)


def allow(context, permission, submission_id, reason):
    return {
        "allowed": True,
        "context": context,
        "permission": permission,
        "submission_id": submission_id,
        "reason": reason or "Authorized.",
    }


def deny(context, permission, submission_id, reason):
    return {
        "allowed": False,
        "context": context,
        "permission": permission,
        "submission_id": submission_id,
        "reason": reason,
    }


@lru_cache(maxsize=1)
def load_auth_policy():
    if not AUTH_POLICY_PATH.exists():
        return {"default_user_id": "uw-demo", "roles": {}, "users": []}
    return json.loads(AUTH_POLICY_PATH.read_text(encoding="utf-8"))


def get_auth_policy_summary():
    policy = load_auth_policy()
    roles = policy.get("roles", {})
    return {
        "default_user_id": policy.get("default_user_id"),
        "roles": [
            {
                "role": role,
                "label": record.get("label", role),
                "permissions": record.get("permissions", []),
            }
            for role, record in roles.items()
        ],
        "users": [
            {
                "user_id": user.get("user_id"),
                "display_name": user.get("display_name"),
                "role": user.get("role"),
                "team": user.get("team"),
                "submission_scope": user.get("submission_scope", []),
            }
            for user in policy.get("users", [])
        ],
    }


def init_auth_database():
    SECURITY_DIR.mkdir(parents=True, exist_ok=True)
    with connect_auth_db() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS login_users (
                username TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS login_sessions (
                session_token TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
            """
        )
        connection.commit()
        seed_admin_user(connection)


def authenticate_login(username, password):
    init_auth_database()
    username = str(username or "").strip()
    password = str(password or "")
    if not username or not password:
        raise ValueError("Username and password are required.")

    with connect_auth_db() as connection:
        row = connection.execute(
            "SELECT username, user_id, password_hash, salt, is_active FROM login_users WHERE username = ?",
            [username],
        ).fetchone()
        if not row or not row["is_active"]:
            raise PermissionError("Invalid username or password.")
        expected = hash_password(password, row["salt"])
        if not secrets.compare_digest(expected, row["password_hash"]):
            raise PermissionError("Invalid username or password.")

        token = secrets.token_urlsafe(32)
        created_at = utc_now()
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)).isoformat().replace("+00:00", "Z")
        connection.execute(
            """
            INSERT INTO login_sessions (session_token, username, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [token, row["username"], row["user_id"], created_at, expires_at],
        )
        connection.commit()

    return {
        "session_token": token,
        "expires_at": expires_at,
        "auth": user_context_for_user_id(row["user_id"]),
    }


def logout_session(token):
    if not token:
        return {"logged_out": True}
    init_auth_database()
    with connect_auth_db() as connection:
        connection.execute("DELETE FROM login_sessions WHERE session_token = ?", [token])
        connection.commit()
    return {"logged_out": True}


def resolve_session_user_id(request):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    try:
        init_auth_database()
        with connect_auth_db() as connection:
            row = connection.execute(
                "SELECT user_id, expires_at FROM login_sessions WHERE session_token = ?",
                [token],
            ).fetchone()
            if not row:
                return None
            if parse_utc(row["expires_at"]) <= datetime.now(timezone.utc):
                connection.execute("DELETE FROM login_sessions WHERE session_token = ?", [token])
                connection.commit()
                return None
            return row["user_id"]
    except (sqlite3.Error, ValueError):
        return None


def user_context_for_user_id(user_id):
    policy = load_auth_policy()
    users = {user.get("user_id"): user for user in policy.get("users", [])}
    user = users.get(user_id) or {}
    role = user.get("role", "senior_underwriter")
    role_record = (policy.get("roles") or {}).get(role, {})
    return {
        "user_id": user.get("user_id", user_id),
        "display_name": user.get("display_name", user_id),
        "role": role,
        "role_label": role_record.get("label", role),
        "team": user.get("team"),
        "submission_scope": user.get("submission_scope", []),
        "permissions": sorted(set(role_record.get("permissions", []))),
        "auth_source": "local login session",
    }


def seed_admin_user(connection):
    salt = secrets.token_hex(16)
    connection.execute(
        """
        INSERT INTO login_users (username, user_id, password_hash, salt, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET
            user_id = excluded.user_id,
            password_hash = excluded.password_hash,
            salt = excluded.salt,
            is_active = excluded.is_active
        """,
        [
            DEFAULT_ADMIN_USERNAME,
            "admin",
            hash_password(DEFAULT_ADMIN_PASSWORD, salt),
            salt,
            1,
            utc_now(),
        ],
    )
    connection.commit()


def connect_auth_db():
    connection = sqlite3.connect(AUTH_DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def hash_password(password, salt):
    value = pbkdf2_hmac(
        "sha256",
        str(password).encode("utf-8"),
        str(salt).encode("utf-8"),
        PASSWORD_ITERATIONS,
    )
    return value.hex()


def parse_utc(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
