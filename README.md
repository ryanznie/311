# CivicCall MVP

VoiceRun voice agent for municipal service intake. A resident describes an issue, the agent extracts the issue type, location, and urgency with OpenAI, checks a local file-backed case store for duplicates, and either creates a new case or attaches the caller to an existing one.

## Files

- `handler.py`: VoiceRun event handler and report flow
- `store.py`: local JSON-backed case store
- `requirements.txt`: Python dependencies
- `.voicerun/agent.yaml`: VoiceRun agent metadata

## Behavior

1. Greets the caller with: `Thanks for calling CivicCall. Please describe the issue you'd like to report.`
2. Extracts:
   - `issue_type`: `sanitation`, `pothole`, `streetlight`, `flooding`, `graffiti`, or `other`
   - `location`: street address or intersection
   - `urgency`: `low`, `medium`, or `high`
3. If location is missing, asks once for the street address or nearest intersection
4. Checks the local case store for a duplicate case
5. Creates a new case or attaches the caller to the existing one
6. Escalates a case automatically once it has been reported 3 or more times

## Setup

```bash
uv tool install voicerun-cli
vr signin
vr validate
```

Create runtime variables that the handler reads:

```bash
vr create variable OPENAI_API_KEY sk-... --environment development --masked
vr create variable OPENAI_MODEL gpt-4.1-mini --environment development
vr create variable VOICE nova --environment development
```

Use `variable`, not `secret`, for runtime API keys in VoiceRun. The handler reads values from `context.variables`.

## Run

```bash
vr debug
vr deploy development
```

## Demo Flow

First caller:

- Caller: `There's trash piling up outside 21 Fleet Street.`
- Agent creates a case such as `SR-A3F1`
- Agent: `I've created a new service request. Your case number is SR-A3F1. Thank you for reporting.`

Second caller for the same issue:

- Agent: `This was already reported and is currently open. I've attached your call to case SR-A3F1.`

Third caller for the same issue:

- Agent: `This issue has been reported multiple times. I've added your report to case SR-A3F1 and escalated it to high priority.`

## Notes

- The case store persists to `cases.json`, so reports survive Python process restarts on the same machine.
- Duplicate matching is based on `issue_type + normalized location`.
- If the agent still cannot determine a location after one follow-up, it declines to file the report.
