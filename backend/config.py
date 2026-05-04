from pathlib import Path
import os


ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DIR = ROOT / "public"
DATA_DIR = ROOT / "data" / "submissions"
CHAT_HISTORY_DIR = ROOT / "data" / "chat_history"
GUIDE_DIR = ROOT / "data" / "guide"
SEARCH_METADATA_PATH = ROOT / "data" / "metadata.json"

PORT = int(os.environ.get("PORT", "3000"))


def load_env(file_path):
    path = Path(file_path)
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]

        os.environ.setdefault(key, value)


def normalize_secret(value):
    if not value:
        return ""

    trimmed = str(value).strip()
    if (trimmed.startswith('"') and trimmed.endswith('"')) or (
        trimmed.startswith("'") and trimmed.endswith("'")
    ):
        return trimmed[1:-1].strip()

    return trimmed


load_env(ROOT / ".env")

OPENAI_API_KEY = normalize_secret(os.environ.get("OPENAI_API_KEY"))
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.4-nano")

