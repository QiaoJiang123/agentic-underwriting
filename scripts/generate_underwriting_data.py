import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import UNDERWRITING_DIR
from backend.services.submission_service import list_submissions
from backend.services.underwriting_service import get_underwriting_system_record


def main():
    UNDERWRITING_DIR.mkdir(parents=True, exist_ok=True)
    updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    for submission in list_submissions():
        submission_id = submission["id"]
        system = get_underwriting_system_record(submission_id)
        record = {
            "submission_id": submission_id,
            "updated_at": updated_at,
            "source": "demo_underwriting_workbench",
            "maintenance_note": (
                "Edit components or claim_review here to customize the Underwriting System "
                "page for this submission. Evidence, signals, appetite, and claim rows are "
                "still calculated by the Python backend from submission metadata and claims data."
            ),
            "components": system["components"],
            "claim_review": system["claim_review"],
        }
        output_path = UNDERWRITING_DIR / f"{submission_id}.json"
        output_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {output_path.relative_to(UNDERWRITING_DIR.parent.parent)}")


if __name__ == "__main__":
    main()
