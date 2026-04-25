import argparse
import html
import re
from pathlib import Path

from axpa_core import build_report


def markdown_to_simple_html(markdown: str) -> str:
    lines = []
    for raw in markdown.splitlines():
        text = html.escape(raw)
        if text.startswith("# "):
            lines.append(f"<h1>{text[2:]}</h1>")
        elif text.startswith("## "):
            lines.append(f"<h2>{text[3:]}</h2>")
        elif text.startswith("### "):
            lines.append(f"<h3>{text[4:]}</h3>")
        elif text.startswith("- "):
            lines.append(f"<li>{text[2:]}</li>")
        elif text.strip() == "":
            lines.append("")
        else:
            lines.append(f"<p>{text}</p>")
    body = "\n".join(lines)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>AX Performance Advisor Report</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 32px; color: #111827; }}
    h1, h2, h3 {{ color: #0f172a; }}
    li {{ margin: 4px 0; }}
    code {{ background: #f3f4f6; padding: 1px 4px; }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an HTML AXPA report.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    html_report = markdown_to_simple_html(build_report(args.evidence))
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(html_report, encoding="utf-8")
    print(f"Wrote HTML report to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
