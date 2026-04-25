import argparse
import json
from pathlib import Path

from axpa_core import analyze_evidence, module_health_scores, summarize_root_causes


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an interactive local HTML dashboard.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    findings = analyze_evidence(args.evidence)
    scores = module_health_scores(findings)
    causes = summarize_root_causes(findings)
    payload = json.dumps({"findings": findings, "scores": scores, "causes": causes})
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>AXPA Dashboard</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:24px;color:#111827}} .grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}
.card{{border:1px solid #d1d5db;padding:12px;border-radius:6px}} table{{border-collapse:collapse;width:100%;margin-top:16px}} td,th{{border-bottom:1px solid #e5e7eb;padding:6px;text-align:left}} input,select{{padding:6px;margin-right:8px}}
</style></head><body>
<h1>AX Performance Advisor Dashboard</h1>
<div class="grid" id="cards"></div>
<p><input id="q" placeholder="Filter findings"><select id="sev"><option value="">All severities</option><option>high</option><option>medium</option><option>low</option></select></p>
<table><thead><tr><th>ID</th><th>Severity</th><th>Module</th><th>Title</th><th>Playbook</th></tr></thead><tbody id="rows"></tbody></table>
<script>
const data={payload};
function render(){{
  const q=document.getElementById('q').value.toLowerCase(), sev=document.getElementById('sev').value;
  const rows=data.findings.filter(f=>(!sev||f.severity===sev)&&JSON.stringify(f).toLowerCase().includes(q));
  document.getElementById('cards').innerHTML=[
    ['Findings', data.findings.length],
    ['High/Critical', data.findings.filter(f=>['high','critical'].includes(f.severity)).length],
    ['Root causes', data.causes.length]
  ].map(c=>`<div class="card"><b>${{c[0]}}</b><br><span style="font-size:28px">${{c[1]}}</span></div>`).join('');
  document.getElementById('rows').innerHTML=rows.slice(0,200).map(f=>`<tr><td>${{f.id}}</td><td>${{f.severity}}</td><td>${{f.axContext.module}}</td><td>${{f.title}}</td><td>${{f.recommendation.playbook}}</td></tr>`).join('');
}}
document.getElementById('q').oninput=render; document.getElementById('sev').onchange=render; render();
</script></body></html>"""
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(html, encoding="utf-8")
    print(f"Wrote dashboard to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
