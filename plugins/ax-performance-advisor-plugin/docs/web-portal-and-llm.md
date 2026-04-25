# Web Portal And LLM Connector

## Local RBAC Web Portal

The web portal is a minimal local HTTP server for role-token protected dashboard access. It is intended for internal use or as a reference implementation before deploying behind a real reverse proxy/auth system.

Config check:

```powershell
python .\scripts\web_portal.py --config .\config\web-portal.example.json --check
```

Run:

```powershell
python .\scripts\web_portal.py --config .\config\web-portal.example.json
```

Open:

```text
http://127.0.0.1:18765/dashboard?token=viewer-token
```

## LLM Connector

The LLM connector prepares a request payload from the evidence-grounded context pack. It does not call an external model by default.

```powershell
python .\scripts\llm_connector.py `
  --config .\config\llm.example.json `
  --evidence .\evidence\IT-TEST-ERP4CU `
  --output .\out\llm-connector.json `
  --question "Was ist die wahrscheinlichste Ursache?"
```

Set endpoint/API-key/model environment variables only in an approved deployment.
