import json

from primfunctions.context import Context
from primfunctions.events import Event, StartEvent, TextEvent, TextToSpeechEvent
from voicerun_completions import generate_chat_completion

import store


GREETING = "Thanks for calling CivicCall. Please describe the issue you'd like to report."
ASK_LOCATION = "Can you give me the street address or nearest intersection?"
MISSING_LOCATION_RESPONSE = (
    "I still need the street address or nearest intersection to file this report. "
    "Please call back when you have that location."
)
EXTRACTION_PROMPT = (
    "Extract the following from this complaint and return only JSON: "
    "issue_type (sanitation / pothole / streetlight / flooding / graffiti / other), "
    "location (street address or intersection), urgency (low / medium / high). "
    "If a field is missing, set it to null."
)
EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "issue_type": {
            "type": ["string", "null"],
            "enum": ["sanitation", "pothole", "streetlight", "flooding", "graffiti", "other", None],
        },
        "location": {"type": ["string", "null"]},
        "urgency": {"type": ["string", "null"], "enum": ["low", "medium", "high", None]},
    },
    "required": ["issue_type", "location", "urgency"],
    "additionalProperties": False,
}


async def extract_complaint_details(transcript: str, context: Context) -> dict:
    response = await generate_chat_completion(
        {
            "provider": "openai",
            "api_key": context.variables.get("OPENAI_API_KEY"),
            "model": context.variables.get("OPENAI_MODEL", "gpt-4.1-mini"),
            "messages": [
                {"role": "system", "content": EXTRACTION_PROMPT},
                {"role": "user", "content": transcript},
            ],
            "response_schema": EXTRACTION_SCHEMA,
            "temperature": 0,
        }
    )

    try:
        parsed = json.loads(response.message.content or "{}")
    except json.JSONDecodeError:
        parsed = {}

    return {
        "issue_type": parsed.get("issue_type") or "other",
        "location": normalize_optional_text(parsed.get("location")),
        "urgency": parsed.get("urgency") or "medium",
    }


def normalize_optional_text(value):
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def merge_follow_up_details(initial_details: dict, follow_up_details: dict) -> dict:
    return {
        "issue_type": follow_up_details.get("issue_type") or initial_details.get("issue_type") or "other",
        "location": follow_up_details.get("location") or initial_details.get("location"),
        "urgency": follow_up_details.get("urgency") or initial_details.get("urgency") or "medium",
    }


def build_case_response(case: dict, duplicated: bool) -> str:
    if not duplicated:
        return (
            "I've created a new service request. "
            f"Your case number is {case['id']}. Thank you for reporting."
        )

    if case["status"] == "escalated":
        return (
            "This issue has been reported multiple times. "
            f"I've added your report to case {case['id']} and escalated it to high priority."
        )

    return (
        f"This was already reported and is currently {case['status']}. "
        f"I've attached your call to case {case['id']}."
    )


async def process_report(details: dict, context: Context):
    key = store.make_case_key(details["issue_type"], details["location"])
    existing_case = store.find_case(details["issue_type"], details["location"])

    if existing_case:
        case = store.attach_to_case(key)
        yield TextToSpeechEvent(text=build_case_response(case, duplicated=True), voice=current_voice(context))
        return

    case = store.create_case(details["issue_type"], details["location"], details["urgency"])
    yield TextToSpeechEvent(text=build_case_response(case, duplicated=False), voice=current_voice(context))


def current_voice(context: Context) -> str:
    return context.variables.get("VOICE", "nova")


async def handler(event: Event, context: Context):
    if isinstance(event, StartEvent):
        context.set_data("awaiting_location_follow_up", False)
        context.set_data("pending_details", None)
        yield TextToSpeechEvent(text=GREETING, voice=current_voice(context))
        return

    if not isinstance(event, TextEvent):
        return

    transcript = (event.data or {}).get("text", "").strip()
    if not transcript:
        yield TextToSpeechEvent(text="I didn't catch that. Please describe the issue again.", voice=current_voice(context))
        return

    awaiting_location = context.get_data("awaiting_location_follow_up", False)

    if awaiting_location:
        pending_details = context.get_data("pending_details", {}) or {}
        follow_up_details = await extract_complaint_details(transcript, context)
        details = merge_follow_up_details(pending_details, follow_up_details)
        context.set_data("awaiting_location_follow_up", False)
        context.set_data("pending_details", None)

        if not details["location"]:
            yield TextToSpeechEvent(text=MISSING_LOCATION_RESPONSE, voice=current_voice(context))
            return

        async for response in process_report(details, context):
            yield response
        return

    details = await extract_complaint_details(transcript, context)

    if not details["location"]:
        context.set_data("awaiting_location_follow_up", True)
        context.set_data("pending_details", details)
        yield TextToSpeechEvent(text=ASK_LOCATION, voice=current_voice(context))
        return

    async for response in process_report(details, context):
        yield response
