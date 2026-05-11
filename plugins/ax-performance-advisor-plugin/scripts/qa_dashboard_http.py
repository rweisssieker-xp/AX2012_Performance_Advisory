from __future__ import annotations

import argparse
import http.server
import json
import socket
import socketserver
import threading
import urllib.request
from pathlib import Path


def find_free_port(start: int) -> int:
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port found from {start}")


def run_http_check(root: Path, dashboard: Path, port: int, required: list[str]) -> dict:
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)

        def log_message(self, format: str, *args: object) -> None:
            return

    relative = dashboard.resolve().relative_to(root.resolve()).as_posix()
    url = f"http://127.0.0.1:{port}/{relative}"
    with socketserver.TCPServer(("127.0.0.1", port), Handler) as httpd:
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                body = response.read().decode("utf-8", errors="replace")
                status = response.status
        finally:
            httpd.shutdown()
            thread.join(timeout=5)
    checks = {text: text in body for text in required}
    return {
        "url": url,
        "status": status,
        "bytes": len(body.encode("utf-8")),
        "requiredChecks": checks,
        "ok": status == 200 and all(checks.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve an AXPA dashboard over local HTTP and verify required dashboard markers.")
    parser.add_argument("--dashboard", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--require", action="append", default=[])
    parser.add_argument("--output")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    dashboard = Path(args.dashboard).resolve()
    if not dashboard.exists():
        raise SystemExit(f"Dashboard not found: {dashboard}")
    if not dashboard.is_relative_to(root):
        raise SystemExit(f"Dashboard {dashboard} must be inside root {root}")
    required = args.require or ["AX Performance Advisor Dashboard", "Platform", "YOLO Wave USP Pack"]
    result = run_http_check(root, dashboard, find_free_port(args.port), required)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
