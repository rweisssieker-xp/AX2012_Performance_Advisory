from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


def load_config(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def audit(config: dict, event: dict) -> None:
    path = Path(config.get("auditLog", "out/web-portal-audit.log"))
    path.parent.mkdir(parents=True, exist_ok=True)
    event["timestamp"] = datetime.now(timezone.utc).isoformat()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def html_response(role: str, dashboard_path: Path) -> bytes:
    html = dashboard_path.read_text(encoding="utf-8")
    banner = f"<div style='padding:10px 24px;background:#101828;color:white;font-family:Segoe UI'>AXPA Web Portal | Role: <b>{role}</b></div>"
    return html.replace("<body>", f"<body>{banner}", 1).encode("utf-8")


def make_handler(config: dict):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)
            token = qs.get("token", [""])[0] or self.headers.get("X-AXPA-Token", "")
            role = config.get("tokens", {}).get(token)
            audit(config, {"path": parsed.path, "client": self.client_address[0], "role": role or "", "authorized": bool(role)})
            if parsed.path not in {"/", "/dashboard"}:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not found")
                return
            if not role:
                self.send_response(401)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"Missing or invalid AXPA token")
                return
            body = html_response(role, Path(config["dashboard"]))
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a minimal local AXPA RBAC web portal.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--check", action="store_true", help="Validate config and exit without starting server.")
    args = parser.parse_args()
    config = load_config(args.config)
    dashboard = Path(config["dashboard"])
    if not dashboard.exists():
        raise SystemExit(f"Dashboard not found: {dashboard}")
    if args.check:
        print(json.dumps({"status": "ok", "host": config["host"], "port": config["port"], "tokens": len(config.get("tokens", {}))}, indent=2))
        return 0
    server = ThreadingHTTPServer((config["host"], int(config["port"])), make_handler(config))
    print(f"AXPA web portal listening on http://{config['host']}:{config['port']}/dashboard?token=viewer-token")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
