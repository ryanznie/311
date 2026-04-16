# main.py
import os

from subconscious import Subconscious

api_key = os.environ.get("SUBCONSCIOUS_API_KEY")
if not api_key:
    raise SystemExit(
        "SUBCONSCIOUS_API_KEY is not set. Copy .env.example to .env and populate it, "
        "or export the variable in your shell."
    )

client = Subconscious(api_key=api_key)

run = client.run(
    engine="tim-gpt",
    input={
        "instructions": """Use the Boston 311 MCP to query live city data.

Call the tool `ckan_aggregate_data` with these exact parameters:
- resource_id: "1a0b420d-99f1-4887-9851-990b2a5a6e17"
- filters: {"neighborhood": "Roxbury"}
- group_by: ["type"]
- metrics: {"count": "count(*)"}

Then return a ranked list of the top complaint types with their counts.""",
        "tools": [{"type": "mcp", "url": "https://data-mcp.boston.gov/mcp"}],
    },
    options={"await_completion": True},
)

answer = run.result.answer if hasattr(run, "result") and run.result and run.result.answer else None
if answer:
    print(answer)
else:
    # Fallback: print last reasoning step
    reasoning = run.result.reasoning if hasattr(run, "result") and run.result else []
    if reasoning:
        print(reasoning[-1].get("content", "") if isinstance(reasoning[-1], dict) else reasoning[-1])
    else:
        print("Status:", run.status)
        print("Result:", run.result)
