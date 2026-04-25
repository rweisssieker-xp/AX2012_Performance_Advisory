from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from axpa_core import analyze_evidence, write_json


def tokens(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[A-Za-z0-9_]{3,}", text)}


def build_index(evidence: str | Path) -> dict:
    findings = analyze_evidence(evidence)
    docs = []
    for finding in findings:
        text = json.dumps(finding, ensure_ascii=False)
        docs.append({"id": finding["id"], "title": finding["title"], "tokens": sorted(tokens(text)), "finding": finding})
    return {"docCount": len(docs), "docs": docs}


def answer(index: dict, question: str) -> dict:
    q = tokens(question)
    scored = []
    for doc in index["docs"]:
        overlap = len(q.intersection(doc["tokens"]))
        if overlap:
            scored.append((overlap, doc))
    scored.sort(key=lambda item: item[0], reverse=True)
    top = [doc for _, doc in scored[:5]]
    if not top:
        return {"question": question, "answer": "Keine passende Evidence gefunden.", "sources": []}
    lines = [f"{doc['id']}: {doc['title']} ({doc['finding'].get('severity')})" for doc in top]
    return {"question": question, "answer": "Passende Evidence:\n" + "\n".join(lines), "sources": [{"findingId": doc["id"], "title": doc["title"]} for doc in top]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Local evidence Q&A with source links. No external LLM required.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--question", default="")
    args = parser.parse_args()
    index = build_index(args.evidence)
    payload = {"index": {"docCount": index["docCount"]}, "sampleAnswer": answer(index, args.question) if args.question else None}
    write_json(args.output, payload)
    print(f"Wrote local RAG/Q&A index summary to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
