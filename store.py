import json
import uuid
from pathlib import Path


STORE_PATH = Path(__file__).with_name("cases.json")


def _load_cases():
    if not STORE_PATH.exists():
        return {}

    try:
        return json.loads(STORE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cases():
    STORE_PATH.write_text(json.dumps(cases, indent=2, sort_keys=True))


cases = _load_cases()


def normalize_location(location):
    return location.lower().strip()


def make_case_key(issue_type, location):
    return f"{issue_type}:{normalize_location(location)}"


def find_case(issue_type, location):
    return cases.get(make_case_key(issue_type, location))


def create_case(issue_type, location, urgency):
    key = make_case_key(issue_type, location)
    case_id = f"SR-{str(uuid.uuid4())[:4].upper()}"
    cases[key] = {
        "id": case_id,
        "issue_type": issue_type,
        "location": location,
        "urgency": urgency,
        "count": 1,
        "status": "open",
    }
    _save_cases()
    return cases[key]


def attach_to_case(key):
    cases[key]["count"] += 1
    if cases[key]["count"] >= 3:
        cases[key]["status"] = "escalated"
    _save_cases()
    return cases[key]
