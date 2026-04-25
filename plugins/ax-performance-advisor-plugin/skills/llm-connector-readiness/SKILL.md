---
name: llm-connector-readiness
description: Prepare and validate LLM connector payloads for AXPA evidence-grounded Q&A without exposing secrets or making unapproved external calls.
---

# LLM Connector Readiness

Use `scripts/llm_connector.py` with `config/llm.example.json`. The connector produces request previews and readiness status; it does not call an external model by default.
