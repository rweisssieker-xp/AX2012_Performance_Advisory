from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ai_ki_extensions import generate_ai_ki_extensions
from axpa_core import write_json


def readiness(config: dict) -> dict:
    endpoint = os.getenv(config.get("endpointEnv", "AXPA_LLM_ENDPOINT"), "")
    key = os.getenv(config.get("apiKeyEnv", "AXPA_LLM_API_KEY"), "")
    model = os.getenv(config.get("modelEnv", "AXPA_LLM_MODEL"), config.get("defaultModel", ""))
    return {
        "ready": bool(endpoint and key and model),
        "endpointConfigured": bool(endpoint),
        "apiKeyConfigured": bool(key),
        "model": model,
        "mode": "ready" if endpoint and key and model else "dry-run",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare LLM connector payloads for AXPA evidence Q&A.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--question", default="Warum ist AX langsam?")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    state = readiness(config)
    pack = generate_ai_ki_extensions(args.evidence)
    payload = {
        "readiness": state,
        "question": args.question,
        "requestPreview": {
            "model": state["model"],
            "messages": [
                {"role": "system", "content": pack["llmContextPack"]["systemPrompt"]},
                {"role": "user", "content": args.question},
            ],
            "contextFindingCount": len(pack["llmContextPack"]["contextFindings"]),
        },
        "note": "No external LLM call is made by this connector unless a deployment-specific sender is configured.",
    }
    write_json(args.output, payload)
    print(f"Wrote LLM connector payload to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
