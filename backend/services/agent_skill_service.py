import json

from backend.config import AGENT_SKILLS_PATH


def get_agent_skills_record():
    if not AGENT_SKILLS_PATH.exists():
        return {"skills": []}

    return json.loads(AGENT_SKILLS_PATH.read_text(encoding="utf-8"))


def list_agent_skills():
    return get_agent_skills_record().get("skills", [])
