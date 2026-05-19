import json

from backend.config import BROKER_DB_PATH


def get_broker_database():
    if not BROKER_DB_PATH.exists():
        return {"brokers": []}

    return json.loads(BROKER_DB_PATH.read_text(encoding="utf-8"))


def list_brokers():
    return get_broker_database().get("brokers", [])


def get_broker(broker_id):
    if not broker_id:
        return None

    return next(
        (broker for broker in list_brokers() if broker.get("broker_id") == broker_id),
        None,
    )


def get_submission_broker(submission):
    submission_broker = submission.get("broker") or {}
    broker = get_broker(submission_broker.get("broker_id"))

    if not broker:
        return submission_broker or None

    return {
        **broker,
        "submission_contact": submission_broker,
    }
