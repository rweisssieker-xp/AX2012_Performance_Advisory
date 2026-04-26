import argparse
import json
from collections import Counter
from pathlib import Path

from ai_insights import generate_ai_insights
from admin_execution import build_execution_plan
from enterprise_observability import generate_enterprise_pack
from advanced_usps import generate_advanced_usps
from governance_extensions import generate_governance_extensions
from strategy_extensions import generate_strategy_extensions
from ai_ki_extensions import generate_ai_ki_extensions
from market_differentiators import generate_market_differentiators
from learning_extensions import generate_learning_extensions
from autonomous_intelligence import generate_autonomous_intelligence
from autonomous_ops import generate_autonomous_ops
from evidence_health import generate_evidence_health
from compare_environments import compare_environments
from skill_catalog import generate_skill_catalog
from axpa_core import analyze_evidence, module_health_scores, summarize_root_causes


SEVERITY_WEIGHT = {"critical": 4, "high": 3, "medium": 2, "low": 1}

ROOT_CAUSE_LABELS = {
    "sql-wait-analysis": "SQL wait pressure",
    "stale-statistics": "Stale statistics",
    "deployment-regression": "Deployment or plan regression",
    "missing-composite-index-candidate": "Index coverage candidate",
    "data-growth": "Data growth pressure",
    "blocking-chain": "Blocking chain",
    "parameter-sensitive-plan": "Parameter-sensitive plan",
    "tempdb-pressure": "TempDB pressure",
    "file-latency": "I/O latency",
    "batch-collision": "Batch collision",
}


def _counts(findings, getter):
    counter = Counter()
    for finding in findings:
        key = getter(finding) or "Unknown"
        counter[str(key)] += 1
    return [{"name": name, "value": value} for name, value in counter.most_common()]


def _risk_score(findings):
    if not findings:
        return 100
    penalty = sum(SEVERITY_WEIGHT.get(f.get("severity", "low"), 1) for f in findings)
    return max(0, min(100, round(100 - penalty * 100 / max(40, len(findings) * 4))))


def _top_findings(findings):
    ranked = sorted(
        findings,
        key=lambda f: (
            SEVERITY_WEIGHT.get(f.get("severity", "low"), 1),
            1 if f.get("confidence") == "high" else 0,
            len(f.get("evidence", [])),
        ),
        reverse=True,
    )
    return ranked[:20]


def _root_cause_bars(findings):
    groups = {}
    for finding in findings:
        playbook = finding.get("recommendation", {}).get("playbook") or finding.get("classification") or "review"
        label = ROOT_CAUSE_LABELS.get(playbook, playbook.replace("-", " ").title())
        group = groups.setdefault(
            playbook,
            {
                "name": label,
                "playbook": playbook,
                "value": 0,
                "riskPoints": 0,
                "highestSeverity": "informational",
                "modules": Counter(),
                "sampleIds": [],
            },
        )
        group["value"] += 1
        rank = SEVERITY_WEIGHT.get(finding.get("severity", "low"), 1)
        group["riskPoints"] += rank
        if rank > SEVERITY_WEIGHT.get(group["highestSeverity"], 0):
            group["highestSeverity"] = finding.get("severity", "low")
        module = finding.get("axContext", {}).get("module") or "Unknown"
        group["modules"][module] += 1
        if len(group["sampleIds"]) < 5:
            group["sampleIds"].append(finding.get("id", ""))
    rows = []
    for group in groups.values():
        modules = ", ".join(name for name, _ in group["modules"].most_common(3))
        rows.append(
            {
                "name": group["name"],
                "playbook": group["playbook"],
                "value": group["value"],
                "riskPoints": group["riskPoints"],
                "highestSeverity": group["highestSeverity"],
                "modules": modules,
                "sampleIds": group["sampleIds"],
            }
        )
    return sorted(rows, key=lambda row: (-row["riskPoints"], -row["value"], row["name"]))


def _collector_errors(evidence):
    root = Path(evidence)
    errors = []
    if not root.exists():
        return errors
    for path in sorted(root.glob("*.error.csv")):
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        errors.append({"source": path.name, "message": text[:1200], "bytes": path.stat().st_size})
    return errors


def _environment_label(evidence):
    root = Path(evidence)
    metadata_path = root / "metadata.json"
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            label = metadata.get("environment") or metadata.get("server") or metadata.get("name")
            if label:
                return str(label)
        except json.JSONDecodeError:
            pass
    return root.name or "Unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an interactive local HTML dashboard.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    environment_label = _environment_label(args.evidence)
    findings = analyze_evidence(args.evidence)
    ai = generate_ai_insights(args.evidence, "Warum war AX langsam?")
    admin_plan = build_execution_plan(args.evidence, Path(args.output).parent / "admin-execution", environment_label, "high")
    enterprise_pack = generate_enterprise_pack(args.evidence, Path(args.output).parent / "enterprise-observability", [args.evidence])
    advanced = generate_advanced_usps(args.evidence)
    governance = generate_governance_extensions(args.evidence, Path(args.output).parent / "governance")
    strategy = generate_strategy_extensions(args.evidence)
    ai_ki = generate_ai_ki_extensions(args.evidence)
    market = generate_market_differentiators(args.evidence)
    learning = generate_learning_extensions(args.evidence, Path(args.output).parent / "learning")
    autonomous = generate_autonomous_intelligence(args.evidence)
    autonomous_ops = generate_autonomous_ops(args.evidence)
    evidence_health = generate_evidence_health(args.evidence)
    sibling_evidence = [p for p in Path(args.evidence).parent.iterdir() if p.is_dir()] if Path(args.evidence).parent.exists() else [Path(args.evidence)]
    env_compare = compare_environments(sibling_evidence)
    skill_catalog = generate_skill_catalog(Path(__file__).resolve().parents[1])
    scores = module_health_scores(findings)
    causes = summarize_root_causes(findings)
    severity = _counts(findings, lambda f: f.get("severity"))
    modules = _counts(findings, lambda f: f.get("axContext", {}).get("module"))[:10]
    playbooks = _counts(findings, lambda f: f.get("recommendation", {}).get("playbook"))[:10]
    owners = _counts(findings, lambda f: f.get("recommendation", {}).get("owner"))[:8]
    payload = json.dumps(
        {
            "findings": findings,
            "environment": environment_label,
            "scores": scores,
            "causes": causes,
            "rootCauseBars": _root_cause_bars(findings),
            "severity": severity,
            "modules": modules,
            "playbooks": playbooks,
            "owners": owners,
            "topFindings": _top_findings(findings),
            "riskScore": _risk_score(findings),
            "collectorErrors": _collector_errors(args.evidence),
            "ai": ai,
            "adminExecution": admin_plan,
            "enterprise": enterprise_pack,
            "advanced": advanced,
            "governance": governance,
            "strategy": strategy,
            "aiKi": ai_ki,
            "market": market,
            "learning": learning,
            "autonomous": autonomous,
            "autonomousOps": autonomous_ops,
            "evidenceHealth": evidence_health,
            "environmentComparison": env_compare,
            "skillCatalog": skill_catalog,
        },
        ensure_ascii=False,
    )

    html = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AX Performance Advisor Dashboard</title>
<style>
:root{--bg:#f5f7fb;--panel:#ffffff;--ink:#172033;--muted:#667085;--line:#d9e0ea;--blue:#2563eb;--cyan:#0891b2;--green:#16803c;--amber:#b45309;--red:#b42318;--violet:#6d28d9}
*{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--ink);font-family:Segoe UI,Arial,sans-serif;font-size:14px;line-height:1.45}
.wrap{max-width:1440px;margin:0 auto;padding:24px}.hero{display:grid;grid-template-columns:1fr 320px;gap:18px;align-items:stretch;margin-bottom:18px}
.headline{background:#101828;color:white;border-radius:8px;padding:22px 24px;min-height:178px;display:flex;flex-direction:column;justify-content:space-between}
.headline h1{margin:0;font-size:30px;letter-spacing:0}.headline p{max-width:860px;margin:10px 0 0;color:#d0d5dd;font-size:15px}
.meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}.chip{border:1px solid rgba(255,255,255,.24);border-radius:999px;padding:5px 10px;color:#eef4ff;background:rgba(255,255,255,.08);font-size:12px}
.scoreCard{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:18px;display:grid;place-items:center;min-height:178px}
.ring{--pct:50;--color:var(--amber);width:142px;height:142px;border-radius:50%;background:conic-gradient(var(--color) calc(var(--pct)*1%),#e6eaf1 0);display:grid;place-items:center}
.ringInner{width:104px;height:104px;background:white;border-radius:50%;display:grid;place-items:center;text-align:center}.ringInner b{font-size:34px}.ringInner span{display:block;color:var(--muted);font-size:12px}
.kpis{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin-bottom:18px}.kpi{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px;min-height:96px}
.kpi label{display:block;color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.04em}.kpi strong{display:block;font-size:28px;margin-top:8px}.kpi small{display:block;color:var(--muted);margin-top:4px}
.grid{display:grid;grid-template-columns:1.15fr .85fr;gap:14px}.panel{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:16px;min-width:0}.panel h2{font-size:16px;margin:0 0 14px}
.bars{display:grid;gap:10px}.barRow{display:grid;grid-template-columns:minmax(120px,220px) 1fr 48px;gap:10px;align-items:center}.barLabel{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#344054}.barTrack{height:12px;background:#edf1f7;border-radius:999px;overflow:hidden}.barFill{height:100%;background:var(--blue);border-radius:999px}.barValue{text-align:right;color:var(--muted);font-variant-numeric:tabular-nums}
.donutWrap{display:grid;grid-template-columns:190px 1fr;gap:12px;align-items:center}.donut{width:170px;height:170px;border-radius:50%;display:grid;place-items:center;background:#e6eaf1}.donutCenter{width:96px;height:96px;border-radius:50%;background:white;display:grid;place-items:center;text-align:center}.legend{display:grid;gap:8px}.legendItem{display:grid;grid-template-columns:12px 1fr 40px;gap:8px;align-items:center}.swatch{width:12px;height:12px;border-radius:2px}
.filters{position:sticky;top:0;z-index:4;background:rgba(245,247,251,.96);backdrop-filter:blur(8px);border:1px solid var(--line);border-radius:8px;padding:12px;display:grid;grid-template-columns:1fr 160px 190px 160px;gap:10px;margin:18px 0}
input,select{width:100%;border:1px solid #cbd5e1;border-radius:6px;padding:9px 10px;background:white;color:var(--ink)}
.tableWrap{background:var(--panel);border:1px solid var(--line);border-radius:8px;overflow:hidden}table{width:100%;border-collapse:collapse}th,td{padding:10px 12px;border-bottom:1px solid #edf1f7;text-align:left;vertical-align:top}th{background:#f8fafc;color:#475467;font-size:12px;text-transform:uppercase;letter-spacing:.04em}tr:hover td{background:#fbfcff}
.sev{display:inline-block;border-radius:999px;padding:3px 8px;font-weight:600;font-size:12px}.critical{background:#fee4e2;color:#912018}.high{background:#ffead5;color:#93370d}.medium{background:#fef7c3;color:#854a0e}.low{background:#dcfae6;color:#085d3a}
.topList{display:grid;gap:10px}.finding{border:1px solid #edf1f7;border-radius:8px;padding:11px}.findingTitle{display:flex;gap:8px;align-items:flex-start;justify-content:space-between}.findingTitle b{font-size:13px}.finding p{margin:8px 0 0;color:var(--muted);font-size:12px}.muted{color:var(--muted)}.foot{margin-top:14px;color:var(--muted);font-size:12px}
.tabs{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0 10px}.tabBtn{border:1px solid var(--line);background:white;color:#344054;border-radius:6px;padding:8px 11px;cursor:pointer}.tabBtn.active{background:#101828;color:white;border-color:#101828}.tabPanel{display:none}.tabPanel.active{display:block}.twoCol{display:grid;grid-template-columns:1fr 1fr;gap:14px}.miniGrid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.mini{border:1px solid #edf1f7;border-radius:8px;padding:10px;background:#fbfcff}.mini b{display:block;font-size:18px}.list{display:grid;gap:8px}.listItem{border:1px solid #edf1f7;border-radius:8px;padding:10px;background:white}.listItem h3{font-size:13px;margin:0 0 6px}.listItem p{margin:0;color:var(--muted);font-size:12px}.warn{border-color:#fedf89;background:#fffcf5}.code{font-family:Consolas,monospace;font-size:12px;white-space:pre-wrap;word-break:break-word;color:#344054}
@media(max-width:1080px){.hero,.grid{grid-template-columns:1fr}.kpis{grid-template-columns:repeat(2,1fr)}.filters{grid-template-columns:1fr 1fr}.donutWrap{grid-template-columns:1fr}}@media(max-width:640px){.wrap{padding:12px}.kpis,.filters{grid-template-columns:1fr}.headline h1{font-size:24px}.barRow{grid-template-columns:1fr 1fr 38px}}
</style>
</head>
<body>
<main class="wrap">
  <section class="hero">
    <div class="headline">
      <div>
        <h1>AX Performance Advisor</h1>
        <p>Lokales Read-only Dashboard fuer Dynamics AX 2012 R3 CU13 und SQL Server 2016. Die Ansicht priorisiert Live-Befunde nach Risiko, Evidenz, Modul, Root Cause und umsetzbarem Playbook.</p>
      </div>
      <div class="meta">
        <span class="chip" id="environmentChip"></span>
        <span class="chip">Mode: Advisory / Read-only</span>
        <span class="chip" id="generated"></span>
      </div>
    </div>
    <aside class="scoreCard">
      <div class="ring" id="scoreRing"><div class="ringInner"><div><b id="score">0</b><span>Health Score</span></div></div></div>
    </aside>
  </section>

  <section class="kpis" id="kpis"></section>

  <section class="grid">
    <div class="panel">
      <h2>Severity-Verteilung</h2>
      <div class="donutWrap"><div class="donut" id="donut"><div class="donutCenter"><b id="donutTotal">0</b><span class="muted">Findings</span></div></div><div class="legend" id="severityLegend"></div></div>
    </div>
    <div class="panel">
      <h2>Top Root Causes</h2>
      <div class="bars" id="causes"></div>
    </div>
    <div class="panel">
      <h2>AX Module / Business Domain</h2>
      <div class="bars" id="modules"></div>
    </div>
    <div class="panel">
      <h2>Empfohlene Playbooks</h2>
      <div class="bars" id="playbooks"></div>
    </div>
  </section>

  <section class="panel" style="margin-top:14px">
    <h2>Priorisierte Top Findings</h2>
    <div class="topList" id="topFindings"></div>
  </section>

  <section class="tabs" aria-label="Dashboard views">
    <button class="tabBtn active" data-tab="ai">AI/KI Advisory</button>
    <button class="tabBtn" data-tab="actions">Safe Actions</button>
    <button class="tabBtn" data-tab="validation">GxP Validation</button>
    <button class="tabBtn" data-tab="evidence">Evidence Gaps</button>
    <button class="tabBtn" data-tab="tickets">Ticket Drafts</button>
    <button class="tabBtn" data-tab="collectors">Collector Status</button>
    <button class="tabBtn" data-tab="health">Evidence Health</button>
    <button class="tabBtn" data-tab="compare">Environment Compare</button>
    <button class="tabBtn" data-tab="skills">Skills Catalog</button>
    <button class="tabBtn" data-tab="real">Realization Pack</button>
    <button class="tabBtn" data-tab="qa">Implementation Q&A</button>
    <button class="tabBtn" data-tab="admin">Admin Execution</button>
    <button class="tabBtn" data-tab="enterprise">Enterprise Observability</button>
    <button class="tabBtn" data-tab="advanced">Advanced USPs</button>
    <button class="tabBtn" data-tab="governance">Governance</button>
    <button class="tabBtn" data-tab="strategy">Strategy</button>
    <button class="tabBtn" data-tab="aiki">More AI/KI</button>
    <button class="tabBtn" data-tab="market">More USPs</button>
    <button class="tabBtn" data-tab="learning">AI Learning</button>
    <button class="tabBtn" data-tab="auto">Autonomous AI</button>
    <button class="tabBtn" data-tab="ops">Autonomous Ops</button>
  </section>

  <section class="tabPanel active" id="tab-ai">
    <div class="twoCol">
      <div class="panel">
        <h2>Root Cause Chat</h2>
        <div id="aiChat"></div>
      </div>
      <div class="panel">
        <h2>Executive Narrative</h2>
        <div id="aiExecutive"></div>
      </div>
      <div class="panel">
        <h2>Remediation Plan</h2>
        <div class="list" id="aiPlan"></div>
      </div>
      <div class="panel">
        <h2>AI/KI Feature Coverage</h2>
        <div class="miniGrid" id="aiCoverage"></div>
      </div>
    </div>
  </section>

  <section class="tabPanel" id="tab-actions"><div class="panel"><h2>Safe Action Classifier</h2><div class="list" id="safeActions"></div></div></section>
  <section class="tabPanel" id="tab-validation"><div class="panel"><h2>GxP Validation Assistant</h2><div class="list" id="gxpValidation"></div></div></section>
  <section class="tabPanel" id="tab-evidence"><div class="panel"><h2>Evidence Gaps</h2><div class="list" id="evidenceGaps"></div></div></section>
  <section class="tabPanel" id="tab-tickets"><div class="panel"><h2>Ticket Drafts</h2><div class="list" id="ticketDrafts"></div></div></section>
  <section class="tabPanel" id="tab-collectors"><div class="panel"><h2>Collector Status</h2><div class="list" id="collectorStatus"></div></div></section>
  <section class="tabPanel" id="tab-health"><div class="panel"><h2>Evidence Health</h2><div class="list" id="evidenceHealth"></div></div></section>
  <section class="tabPanel" id="tab-compare"><div class="panel"><h2>Environment Compare</h2><div class="list" id="environmentCompare"></div></div></section>
  <section class="tabPanel" id="tab-skills"><div class="panel"><h2>Skills Catalog</h2><div class="list" id="skillsCatalog"></div></div></section>
  <section class="tabPanel" id="tab-real"><div class="panel"><h2>Realization Pack</h2><div class="list" id="realizationPack"></div></div></section>
  <section class="tabPanel" id="tab-qa">
    <div class="panel">
      <h2>Implementation Q&A</h2>
      <div class="filters" style="position:static;margin:0 0 12px;grid-template-columns:1fr 240px">
        <select id="qaFinding"></select>
        <select id="qaQuestion">
          <option value="next">Was ist der nächste sichere Umsetzungsschritt?</option>
          <option value="test">Wie teste ich das in TEST?</option>
          <option value="risk">Welche Risiken hat die Umsetzung?</option>
          <option value="approval">Braucht das CAB/GxP Approval?</option>
          <option value="rollback">Wie sieht Rollback aus?</option>
          <option value="evidence">Welche Evidence fehlt noch?</option>
        </select>
      </div>
      <div class="list" id="qaAnswer"></div>
    </div>
  </section>
  <section class="tabPanel" id="tab-admin">
    <div class="panel">
      <h2>Admin Execution Preview</h2>
      <div class="list" id="adminExecution"></div>
    </div>
  </section>
  <section class="tabPanel" id="tab-enterprise">
    <div class="panel">
      <h2>Enterprise Observability</h2>
      <div class="list" id="enterprisePack"></div>
    </div>
  </section>
  <section class="tabPanel" id="tab-advanced">
    <div class="panel">
      <h2>Advanced USPs</h2>
      <div class="list" id="advancedUsps"></div>
    </div>
  </section>
  <section class="tabPanel" id="tab-governance">
    <div class="panel">
      <h2>Governance Extensions</h2>
      <div class="list" id="governanceExtensions"></div>
    </div>
  </section>
  <section class="tabPanel" id="tab-strategy">
    <div class="panel">
      <h2>Strategy Extensions</h2>
      <div class="list" id="strategyExtensions"></div>
    </div>
  </section>
  <section class="tabPanel" id="tab-aiki">
    <div class="panel">
      <h2>More AI/KI</h2>
      <div class="list" id="aiKiExtensions"></div>
    </div>
  </section>
  <section class="tabPanel" id="tab-market">
    <div class="panel">
      <h2>More USPs</h2>
      <div class="list" id="marketDifferentiators"></div>
    </div>
  </section>
  <section class="tabPanel" id="tab-learning">
    <div class="panel">
      <h2>AI Learning</h2>
      <div class="list" id="learningExtensions"></div>
    </div>
  </section>
  <section class="tabPanel" id="tab-auto">
    <div class="panel">
      <h2>Autonomous AI</h2>
      <div class="list" id="autonomousIntelligence"></div>
    </div>
  </section>
  <section class="tabPanel" id="tab-ops">
    <div class="panel">
      <h2>Autonomous Ops</h2>
      <div class="list" id="autonomousOps"></div>
    </div>
  </section>

  <section class="filters">
    <input id="q" placeholder="Suchen nach Tabelle, Wait, Batch, Empfehlung...">
    <select id="sev"><option value="">Alle Severities</option><option>critical</option><option>high</option><option>medium</option><option>low</option></select>
    <select id="module"><option value="">Alle Module</option></select>
    <select id="playbook"><option value="">Alle Playbooks</option></select>
  </section>

  <section class="tableWrap">
    <table>
      <thead><tr><th>ID</th><th>Risiko</th><th>Modul</th><th>Befund</th><th>Empfehlung</th><th>Evidence</th></tr></thead>
      <tbody id="rows"></tbody>
    </table>
  </section>
  <div class="foot" id="foot"></div>
</main>
<script>
const data=__PAYLOAD__;
const colors={critical:'#b42318',high:'#d95f0e',medium:'#d97706',low:'#16803c',Unknown:'#64748b'};
const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const sevWeight={critical:4,high:3,medium:2,low:1};
function count(list,key){const m=new Map();list.forEach(x=>{const v=key(x)||'Unknown';m.set(v,(m.get(v)||0)+1)});return [...m.entries()].sort((a,b)=>b[1]-a[1]).map(([name,value])=>({name,value}))}
function fillSelect(id,items){const el=document.getElementById(id);items.forEach(i=>{const o=document.createElement('option');o.value=i.name;o.textContent=i.name;el.appendChild(o)})}
function bars(id,items,color){const max=Math.max(1,...items.map(i=>i.value));document.getElementById(id).innerHTML=items.slice(0,10).map(i=>`<div class="barRow" title="${esc(i.name)}${i.modules?' | Modules: '+esc(i.modules):''}${i.highestSeverity?' | Highest: '+esc(i.highestSeverity):''}"><div class="barLabel">${esc(i.name)}${i.highestSeverity?` <span class="muted">(${esc(i.highestSeverity)})</span>`:''}</div><div class="barTrack"><div class="barFill" style="width:${Math.max(4,i.value/max*100)}%;background:${color}"></div></div><div class="barValue">${i.value}</div></div>`).join('')||'<span class="muted">Keine Daten</span>'}
function severityDonut(){const total=data.findings.length||1;let start=0;const parts=['critical','high','medium','low'].map(s=>{const item=data.severity.find(x=>x.name===s);const value=item?item.value:0;const pct=value/total*100;const seg=`${colors[s]} ${start}% ${start+pct}%`;start+=pct;return seg});document.getElementById('donut').style.background=`conic-gradient(${parts.join(',')},#e6eaf1 0)`;document.getElementById('donutTotal').textContent=data.findings.length;document.getElementById('severityLegend').innerHTML=['critical','high','medium','low'].map(s=>{const v=(data.severity.find(x=>x.name===s)||{value:0}).value;return `<div class="legendItem"><span class="swatch" style="background:${colors[s]}"></span><span>${s}</span><b>${v}</b></div>`}).join('')}
function renderKpis(){const high=data.findings.filter(f=>['critical','high'].includes(f.severity)).length;const approval=data.findings.filter(f=>f.recommendation?.requiresApproval).length;const tables=new Set(data.findings.flatMap(f=>f.axContext?.tables||[]));const waitFindings=data.findings.filter(f=>(f.sqlContext?.waitTypes||[]).length).length;document.getElementById('kpis').innerHTML=[['Findings',data.findings.length,'alle generierten Befunde'],['High / Critical',high,'sofort priorisieren'],['Betroffene Tabellen',tables.size,'aus AX/SQL-Kontext'],['Wait-basierte Findings',waitFindings,'SQL-Wait-Korrelation'],['Approval-relevant',approval,'Change Control erforderlich']].map(k=>`<div class="kpi"><label>${k[0]}</label><strong>${k[1]}</strong><small>${k[2]}</small></div>`).join('')}
function renderTop(){const top=data.topFindings.slice(0,10);document.getElementById('topFindings').innerHTML=top.map(f=>`<article class="finding"><div class="findingTitle"><b>${esc(f.title)}</b><span class="sev ${esc(f.severity)}">${esc(f.severity)}</span></div><p>${esc(f.recommendation?.summary||f.likelyCause||'')}</p><p><b>Playbook:</b> ${esc(f.recommendation?.playbook||'')} <span class="muted">|</span> <b>Module:</b> ${esc(f.axContext?.module||'Unknown')} <span class="muted">|</span> <b>Confidence:</b> ${esc(f.confidence||'')}</p></article>`).join('')}
function filtered(){const q=document.getElementById('q').value.toLowerCase();const sev=document.getElementById('sev').value;const mod=document.getElementById('module').value;const play=document.getElementById('playbook').value;return data.findings.filter(f=>(!sev||f.severity===sev)&&(!mod||(f.axContext?.module||'Unknown')===mod)&&(!play||(f.recommendation?.playbook||'Unknown')===play)&&(!q||JSON.stringify(f).toLowerCase().includes(q))).sort((a,b)=>(sevWeight[b.severity]||0)-(sevWeight[a.severity]||0))}
function renderRows(){const rows=filtered();document.getElementById('rows').innerHTML=rows.slice(0,250).map(f=>{const evidence=(f.evidence||[]).slice(0,2).map(e=>`${esc(e.source)}:${esc(e.metric)}=${esc(e.value)}`).join('<br>');return `<tr><td>${esc(f.id)}</td><td><span class="sev ${esc(f.severity)}">${esc(f.severity)}</span><br><span class="muted">${esc(f.confidence)}</span></td><td>${esc(f.axContext?.module||'Unknown')}</td><td><b>${esc(f.title)}</b><br><span class="muted">${esc(f.likelyCause||'')}</span></td><td>${esc(f.recommendation?.summary||'')}<br><span class="muted">${esc(f.recommendation?.playbook||'')}</span></td><td>${evidence}</td></tr>`}).join('');document.getElementById('foot').textContent=`${rows.length} von ${data.findings.length} Findings angezeigt, Tabelle auf 250 Zeilen begrenzt.`}
function listItem(title,body,extra=''){return `<article class="listItem"><h3>${esc(title)}</h3><p>${body}</p>${extra}</article>`}
function renderAiTabs(){const ai=data.ai||{};document.getElementById('aiChat').innerHTML=listItem(ai.naturalLanguageRootCauseChat?.question||'Frage',esc(ai.naturalLanguageRootCauseChat?.answer||'Keine AI/KI-Antwort vorhanden.'),`<p class="muted">Finding IDs: ${(ai.naturalLanguageRootCauseChat?.supportingFindingIds||[]).map(esc).join(', ')}</p>`);document.getElementById('aiExecutive').innerHTML=listItem('Management Summary',`${esc(ai.executiveNarrative?.summary||'')}<br>${esc(ai.executiveNarrative?.riskMessage||'')}<br><b>Board Ask:</b> ${esc(ai.executiveNarrative?.boardAsk||'')}`);const plan=(ai.remediationPlanner?.weeklyPlan||[]);document.getElementById('aiPlan').innerHTML=plan.map(w=>listItem(`Week ${w.week}: ${w.focus}`,(w.actions||[]).map(a=>`<b>${esc(a.playbook)}</b> (${esc(a.findingCount)}): ${esc(a.firstAction)}`).join('<br>'))).join('')||listItem('Kein Plan','Keine Daten');document.getElementById('aiCoverage').innerHTML=[['Features',ai.metadata?.featureCount||0],['Findings',ai.metadata?.findingCount||0],['Action Groups',ai.noiseReduction?.actionableGroups||0],['Evidence Gaps',(ai.evidenceGapDetector||[]).length]].map(x=>`<div class="mini"><span class="muted">${esc(x[0])}</span><b>${esc(x[1])}</b></div>`).join('');document.getElementById('safeActions').innerHTML=(ai.safeActionClassifier||[]).map(a=>listItem(`${a.classification}: ${a.title}`,`${esc(a.why)}<br><b>Next:</b> ${esc(a.nextStep)}`)).join('')||listItem('Keine Actions','Keine Daten');document.getElementById('gxpValidation').innerHTML=(ai.gxpValidationAssistant||[]).slice(0,12).map(v=>listItem(v.findingId,`<b>Objective:</b> ${esc(v.testObjective)}<br><b>Expected:</b> ${esc(v.expectedResult)}<br><b>Deviation:</b> ${esc(v.deviationHandling)}<br><b>Approval:</b> ${esc(v.approvalPath)}`)).join('')||listItem('Keine Validierung','Keine Daten');document.getElementById('evidenceGaps').innerHTML=(ai.evidenceGapDetector||[]).map(g=>listItem(g.source,`${esc(g.reason)}<br><b>Next:</b> ${esc(g.nextCollection)}`)).join('')||listItem('Keine Evidence Gaps','Alle Pflichtquellen wurden erkannt.');document.getElementById('ticketDrafts').innerHTML=(ai.ticketAutoDrafting||[]).slice(0,12).map(t=>listItem(`${t.priority}: ${t.title}`,`${esc(t.description)}<br><b>Acceptance:</b> ${esc(t.acceptanceCriteria)}<br><b>Rollback:</b> ${esc(t.rollback)}`)).join('')||listItem('Keine Tickets','Keine Daten');document.getElementById('collectorStatus').innerHTML=(data.collectorErrors||[]).map(e=>listItem(e.source,`<span class="code">${esc(e.message)}</span>`,'')).join('')||listItem('Collector OK','Keine *.error.csv Dateien im Evidence-Ordner gefunden.');const rp=ai.realizationPack||{};document.getElementById('realizationPack').innerHTML=[listItem('Evidence Trust Score',`Score: <b>${esc(rp.evidenceTrustScore?.score)}</b> / Grade: <b>${esc(rp.evidenceTrustScore?.grade)}</b><br>Missing: ${esc((rp.evidenceTrustScore?.missingSources||[]).join(', '))}`),listItem('Collector Fix Suggestions',`${esc((rp.collectorFixSuggestions||[]).length)} suggestions generated`),listItem('SQL 2016 Support Risk',`${esc(rp.sql2016EndOfSupportRisk?.risk)} risk; date ${esc(rp.sql2016EndOfSupportRisk?.supportRiskDate)}`),listItem('Adapter Readiness',Object.entries(rp.adapterReadiness||{}).map(([k,v])=>`<b>${esc(k)}</b>: ${esc(v.status)}`).join('<br>')),listItem('Closed-loop Governance',`${esc((rp.closedLoopGovernance||[]).length)} finding states prepared`),listItem('Dynamic SLA Contracts',`${esc((rp.dynamicSlaContracts||[]).length)} candidate contracts`) ].join('')}
function renderEvidenceHealth(){const h=data.evidenceHealth||{};document.getElementById('evidenceHealth').innerHTML=[listItem('Collection Context',`Environment: <b>${esc(h.environment)}</b><br>Collected: ${esc(h.collectedAt)}<br>Evidence Health Score: <b>${esc(h.score)}</b><br>Present/Error/Empty: ${esc(h.summary?.present)}/${esc(h.summary?.error)}/${esc(h.summary?.empty)} of ${esc(h.summary?.total)}`),listItem('Source Matrix',`${(h.sources||[]).map(s=>`${esc(s.status)}: <b>${esc(s.label)}</b> (${esc(s.file)}, ${esc(s.importance)}, ${esc(s.bytes)} bytes) ${s.errorFile? ' error='+esc(s.errorFile):''}`).join('<br>')}`),listItem('AX Schema Discovery',`${(h.schemaDiscovery||[]).slice(0,30).map(x=>`${esc(x.discovery_type)}: ${esc(x.table_schema)}.${esc(x.table_name)}`).join('<br>')||'No schema discovery rows.'}`),listItem('AX Source Status',`${(h.sourceStatus||[]).map(x=>`${esc(x.status)}: ${esc(x.source)} -> ${esc(x.file)} (${esc(x.note)})`).join('<br>')||'No source_status.csv present.'}`)].join('')}
function renderEnvironmentCompare(){const c=data.environmentComparison||{};document.getElementById('environmentCompare').innerHTML=[listItem('Compared Environments',`Count: <b>${esc(c.environmentCount)}</b>`),...(c.environments||[]).map(e=>listItem(e.environment,`Findings: <b>${esc(e.findingCount)}</b><br>High/Critical: <b>${esc(e.highCritical)}</b><br>Top playbooks: ${esc((e.topPlaybooks||[]).join(', '))}`))].join('')}
function renderSkillsCatalog(){const s=data.skillCatalog||{};document.getElementById('skillsCatalog').innerHTML=[listItem('Skill Overview',`Skill count: <b>${esc(s.skillCount)}</b><br>Use Primary first, Advanced only when needed.`),...Object.entries(s.groups||{}).map(([group,items])=>listItem(group,`${(items||[]).map(x=>`<b>${esc(x.name)}</b>: ${esc(x.description)}`).join('<br>')||'No skills'}`))].join('')}
function qaFinding(){const id=document.getElementById('qaFinding').value;return data.findings.find(f=>f.id===id)||data.topFindings[0]||data.findings[0]}
function qaAnswerFor(f,q){if(!f)return ['Keine Finding ausgewählt','Keine Daten'];const rec=f.recommendation||{}, val=f.validation||{}, risk=f.changeReadiness||{}, ax=f.axContext||{};if(q==='next')return ['Nächster sicherer Schritt',`${esc(rec.summary||'Finding prüfen.')}<br><br><b>Sicherheitsgrenze:</b> Keine PROD-Änderung direkt aus dem Dashboard. Erst Evidence sichern, TEST messen, dann Approval.`];if(q==='test')return ['TEST-Vorgehen',`1. Vergleichbare TEST-Daten und Zeitfenster herstellen.<br>2. Baseline messen: ${esc(val.baselineWindow||'aktuelles Evidence-Fenster')}.<br>3. Maßnahme nur in TEST durchführen.<br>4. Erfolgskriterium: ${esc(val.successMetric||'Vorher/Nachher verbessern ohne Regression')}.<br>5. Ergebnis als Evidence Pack sichern.`];if(q==='risk')return ['Umsetzungsrisiko',`<b>Technical:</b> ${esc(risk.technicalRisk||'medium')}<br><b>AX Compatibility:</b> ${esc(risk.axCompatibilityRisk||'medium')}<br><b>Downtime:</b> ${esc(risk.downtimeRisk||'low')}<br><b>Rollback:</b> ${esc(risk.rollbackComplexity||'medium')}<br><b>Betroffene Module:</b> ${esc(ax.module||'Unknown')}`];if(q==='approval')return ['Approval',`<b>Approval Path:</b> ${esc(risk.approvalPath||'Review')}<br><b>Requires Approval:</b> ${esc(rec.requiresApproval!==false)}<br><b>Owner:</b> ${esc(rec.owner||ax.technicalOwner||'AX Operations')}<br><b>GxP Hinweis:</b> Bei produktionsnaher Änderung Test Evidence, Approval, Rollback und Post-Change-Messung anhängen.`];if(q==='rollback')return ['Rollback',`${esc(val.rollback||'Änderung über Change Control zurücknehmen.')}<br><br>Vor Umsetzung muss klar sein, welche SQL/AX/Batch-Konfiguration geändert wurde und wie der Ausgangszustand wiederhergestellt wird.`];return ['Fehlende Evidence',`Direkte Evidence im Finding: ${(f.evidence||[]).map(e=>esc(e.source+':'+e.metric)).join(', ')||'keine'}<br><br>Globale Gaps: ${(data.ai?.evidenceGapDetector||[]).map(g=>esc(g.source)).join(', ')||'keine'}.`]}
function renderQa(){const f=qaFinding();const q=document.getElementById('qaQuestion').value;const [title,body]=qaAnswerFor(f,q);document.getElementById('qaAnswer').innerHTML=listItem(`${title}: ${f?.id||''}`,`<b>${esc(f?.title||'')}</b><br><br>${body}`)}
function initQa(){const sel=document.getElementById('qaFinding');sel.innerHTML=(data.topFindings||data.findings).slice(0,40).map(f=>`<option value="${esc(f.id)}">${esc(f.severity)} | ${esc(f.id)} | ${esc(f.title).slice(0,100)}</option>`).join('');document.getElementById('qaFinding').addEventListener('input',renderQa);document.getElementById('qaQuestion').addEventListener('input',renderQa);renderQa()}
function renderAdmin(){const plan=data.adminExecution||{};const rows=(plan.actions||[]).slice(0,20).map(a=>listItem(`${a.status}: ${a.findingId}`,`<b>${esc(a.title)}</b><br>Action: ${esc(a.actionType)}<br>Environment: ${esc(a.environment)}<br>Token: <span class="code">${esc(a.confirmationToken)}</span><br>Script: <span class="code">${esc(a.script)}</span><br>Gates: ${Object.entries(a.gates||{}).map(([k,v])=>`${esc(k)}=${esc(v)}`).join(', ')}`)).join('');document.getElementById('adminExecution').innerHTML=[listItem('Policy Mode',`Mode: <b>${esc(plan.mode)}</b><br>Environment: <b>${esc(plan.environment)}</b><br>Actions: ${esc(plan.actionCount)}<br>Executable after gates: ${esc(plan.executableCount)}<br><br>Execution is not performed by the dashboard. Admin reviews the generated script, approval, token, rollback, and validation before any database/tool execution.`),rows].join('')}
function renderEnterprise(){const e=data.enterprise||{};document.getElementById('enterprisePack').innerHTML=[listItem('Time-Series Store',`DB: <span class="code">${esc(e.timeSeriesStore?.db)}</span><br>Run: ${esc(e.timeSeriesStore?.runId)}<br>Findings: ${esc(e.timeSeriesStore?.findings)}<br>Health: ${esc(e.timeSeriesStore?.healthScore)}`),listItem('Alerts',`Alerts: <b>${esc(e.alerts?.alertCount)}</b><br>${(e.alerts?.alerts||[]).slice(0,8).map(a=>`${esc(a.severity)}: ${esc(a.title)} -> ${esc(a.route)}`).join('<br>')}`),listItem('Estate Inventory',`Environments: ${esc(e.estateInventory?.environmentCount)}<br>${(e.estateInventory?.environments||[]).map(x=>`${esc(x.name)}: ${esc(x.findingCount)} findings`).join('<br>')}`),listItem('Plan Repository',`Entries: ${esc(e.planRepository?.entryCount)}<br>Query families: ${esc(e.planRepository?.queryFamilies)}<br>Regression candidates: ${esc((e.planRepository?.regressionCandidates||[]).length)}`),listItem('Notification Payloads',`Teams: <span class="code">${esc(e.notifications?.teams)}</span><br>ServiceNow: <span class="code">${esc(e.notifications?.serviceNow)}</span><br>PagerDuty: <span class="code">${esc(e.notifications?.pagerDuty)}</span>`),listItem('Competitive Coverage',`${(e.competitorCoverage?.covered||[]).map(esc).join('<br>')}`)].join('')}
function renderAdvanced(){const a=data.advanced||{};document.getElementById('advancedUsps').innerHTML=[listItem('SLO Burn Rate',`SLOs: ${esc(a.sloBurnRate?.sloCount)}<br>${(a.sloBurnRate?.items||[]).slice(0,8).map(x=>`${esc(x.status)}: ${esc(x.slo)} burn=${esc(x.burnRate)}`).join('<br>')}`),listItem('Maintenance Window Optimizer',`${(a.maintenanceWindowOptimizer?.sequence||[]).map(x=>`${esc(x.window)} ${esc(x.playbook)} (${esc(x.findingCount)})`).join('<br>')}`),listItem('Cost Of Delay',`Daily risk points: <b>${esc(a.costOfDelay?.totalDailyRiskPoints)}</b><br>${(a.costOfDelay?.items||[]).slice(0,6).map(x=>`${esc(x.findingId)}: ${esc(x.dailyRiskPoints)}`).join('<br>')}`),listItem('Release Gate',`Status: <b>${esc(a.releaseGate?.status)}</b><br>Blockers: ${esc(a.releaseGate?.blockerCount)}`),listItem('Retention Candidates',`Candidates: ${esc(a.retentionCandidates?.candidateCount)}<br>${(a.retentionCandidates?.candidates||[]).slice(0,8).map(x=>`${esc(x.table)} (${esc(x.signals)})`).join('<br>')}`),listItem('Known Issue Matches',`Matches: ${esc(a.knownIssueMatches?.matchCount)}<br>${(a.knownIssueMatches?.matches||[]).slice(0,8).map(x=>`${esc(x.knownIssueId)} -> ${esc(x.findingId)}`).join('<br>')}`),listItem('Executive Briefing',`${esc(a.executiveBriefings?.oneMinute)}<br><b>Ask:</b> ${esc(a.executiveBriefings?.decisionAsk)}<br><b>Risk:</b> ${esc(a.executiveBriefings?.riskIfDeferred)}`)].join('')}
function renderGovernance(){const g=data.governance||{};document.getElementById('governanceExtensions').innerHTML=[listItem('Runbook Automation',`${(g.runbookAutomation||[]).slice(0,5).map(x=>`${esc(x.findingId)}: ${esc(x.playbook)}`).join('<br>')}`),listItem('RACI Matrix',`${(g.raciMatrix||[]).map(x=>`${esc(x.owner)}: ${esc(x.findingCount)} findings, high=${esc(x.highCount)}`).join('<br>')}`),listItem('Business Impact Timeline',`${(g.businessImpactTimeline||[]).map(x=>`${esc(x.window)}: ${esc(x.findingCount)} findings, high=${esc(x.highCount)}`).join('<br>')}`),listItem('Suppression Governance',`${(g.suppressionGovernance||[]).slice(0,8).map(x=>`${esc(x.scope)} (${esc(x.findingCount)}) expiry=${esc(x.expiry)}`).join('<br>')}`),listItem('Data Quality Checks',`Score: <b>${esc(g.dataQualityChecks?.score)}</b><br>Empty files: ${(g.dataQualityChecks?.emptyFiles||[]).map(esc).join(', ')}<br>Collector errors: ${(g.dataQualityChecks?.collectorErrors||[]).map(esc).join(', ')}`),listItem('Audit Export',`CSV: <span class="code">${esc(g.auditExport?.csv)}</span><br>JSON: <span class="code">${esc(g.auditExport?.json)}</span><br>Rows: ${esc(g.auditExport?.rows)}`)].join('')}
function renderStrategy(){const s=data.strategy||{};document.getElementById('strategyExtensions').innerHTML=[listItem('What-if Simulation',`${(s.whatIfSimulation?.scenarios||[]).slice(0,8).map(x=>`${esc(x.scenario)}: ${esc(x.riskReductionPercent)}% reduction estimate`).join('<br>')}`),listItem('Baseline Benchmark',`Health: <b>${esc(s.baselineBenchmark?.healthScore)}</b><br>${esc(s.baselineBenchmark?.benchmarkInterpretation)}`),listItem('Evidence Completeness Roadmap',`${(s.evidenceCompletenessRoadmap?.sources||[]).map(x=>`${esc(x.present?'done':'missing')}: ${esc(x.source)} - ${esc(x.value)}`).join('<br>')}`),listItem('Remediation Kanban',`Now: ${esc((s.remediationKanban?.Now||[]).length)}<br>Next: ${esc((s.remediationKanban?.Next||[]).length)}<br>Later: ${esc((s.remediationKanban?.Later||[]).length)}<br>Waiting Evidence: ${esc((s.remediationKanban?.['Waiting Evidence']||[]).length)}`),listItem('KPI Contracts',`${(s.kpiContracts||[]).slice(0,8).map(x=>`${esc(x.kpi)} current=${esc(x.current)} target=${esc(x.target)}`).join('<br>')}`),listItem('Capability Matrix',`${(s.capabilityMatrix||[]).map(x=>`${esc(x.status)}: ${esc(x.capability)} - ${esc(x.differentiator)}`).join('<br>')}`)].join('')}
function renderAiKi(){const k=data.aiKi||{};document.getElementById('aiKiExtensions').innerHTML=[listItem('Hypothesis Ranking',`${(k.hypothesisRanking||[]).slice(0,8).map(x=>`${esc(x.hypothesis)} score=${esc(x.score)} confidence=${esc(x.confidence)}`).join('<br>')}`),listItem('Counterfactuals',`${(k.counterfactuals||[]).slice(0,5).map(x=>`${esc(x.findingId)}: ${esc(x.ifWeValidateInTest)}`).join('<br>')}`),listItem('Causal Narrative',`${esc(k.causalNarrative?.summary)}<br>${(k.causalNarrative?.chain||[]).map(x=>`${esc(x.cause)} -> ${esc(x.effect)}`).join('<br>')}`),listItem('LLM Context Pack',`Context findings: ${esc((k.llmContextPack?.contextFindings||[]).length)}<br>Policy: ${esc(k.llmContextPack?.sourcePolicy)}<br><span class="code">${esc((k.llmContextPack?.systemPrompt||'').slice(0,300))}</span>`),listItem('Evidence Chunks',`Chunks: ${esc((k.evidenceChunks||[]).length)}<br>${(k.evidenceChunks||[]).slice(0,3).map(x=>`${esc(x.id)}: ${esc(x.text).slice(0,180)}`).join('<br>')}`),listItem('Confidence Calibration',`${Object.entries(k.confidenceCalibration?.summary||{}).map(([a,b])=>`${esc(a)}=${esc(b)}`).join('<br>')}`)].join('')}
function renderMarket(){const m=data.market||{};document.getElementById('marketDifferentiators').innerHTML=[listItem('Vendor-neutral Positioning',`${esc(m.vendorNeutralComparison?.positioning)}<br><b>AXPA:</b> ${(m.vendorNeutralComparison?.axpaStrength||[]).map(esc).join(', ')}`),listItem('Migration Readiness',`Score: <b>${esc(m.migrationReadiness?.readinessScore)}</b><br>Signals: ${esc(m.migrationReadiness?.signalCount)}<br>${esc(m.migrationReadiness?.recommendation)}`),listItem('Resilience Score',`Score: <b>${esc(m.resilienceScore?.score)}</b><br>High: ${esc(m.resilienceScore?.highFindings)} Debt: ${esc(m.resilienceScore?.debtItems)} Approval: ${esc(m.resilienceScore?.approvalItems)}`),listItem('Knowledge Graph',`Nodes: ${esc(m.knowledgeGraph?.nodeCount)}<br>Edges: ${esc(m.knowledgeGraph?.edgeCount)}`),listItem('Process Owner Scorecards',`${(m.processOwnerScorecards||[]).slice(0,8).map(x=>`${esc(x.owner)} score=${esc(x.score)} findings=${esc(x.findingCount)} high=${esc(x.highCount)}`).join('<br>')}`),listItem('Evidence Marketplace',`${(m.evidenceMarketplace||[]).map(x=>`${esc(x.evidence)}: ${esc(x.value)}`).join('<br>')}`),listItem('Value Realization',`Opportunities: ${esc(m.valueRealization?.opportunityCount)}<br>${(m.valueRealization?.opportunities||[]).slice(0,8).map(x=>`${esc(x.initiative)} (${esc(x.findingCount)})`).join('<br>')}`)].join('')}
function renderLearning(){const l=data.learning||{};document.getElementById('learningExtensions').innerHTML=[listItem('Recommendation Memory',`Entries: ${esc((l.recommendationMemory?.entries||[]).length)}<br>DB: <span class="code">${esc(l.recommendationMemory?.db)}</span>`),listItem('Similarity Search',`${(l.similaritySearch||[]).slice(0,5).map(x=>`${esc(x.findingId)} similar=${esc((x.similar||[]).length)}`).join('<br>')}`),listItem('Acceptance Simulation',`${Object.entries(l.acceptanceSimulation||{}).map(([k,v])=>`${esc(k)}: items=${esc(v.items)} load=${esc(v.governanceLoad)}`).join('<br>')}`),listItem('Executive Narrative Variants',`${Object.entries(l.executiveNarrativeVariants||{}).map(([k,v])=>`<b>${esc(k)}</b>: ${esc(v)}`).join('<br>')}`),listItem('Anomaly Explanation',`${(l.anomalyExplanation||[]).slice(0,5).map(x=>`${esc(x.findingId)}: ${esc(x.plainExplanation).slice(0,180)}`).join('<br>')}`),listItem('Action Confidence Tuning',`${(l.actionConfidenceTuning||[]).slice(0,8).map(x=>`${esc(x.findingId)} confidence=${esc(x.actionConfidence)}`).join('<br>')}`)].join('')}
function renderAutonomous(){const a=data.autonomous||{};document.getElementById('autonomousIntelligence').innerHTML=[listItem('Evidence Scout',`${(a.evidenceScout?.sources||[]).map(x=>`${esc(x.present?'present':'missing')}: ${esc(x.source)} - ${esc(x.whyItMatters)}`).join('<br>')}`),listItem('Investigation Tree',`${esc(a.investigationTree?.rootQuestion)}<br>${(a.investigationTree?.nodes||[]).slice(0,5).map(x=>`${esc(x.findingId)}: ${esc(x.question)}`).join('<br>')}`),listItem('Root Cause Debate',`${(a.rootCauseDebate||[]).slice(0,6).map(x=>`<b>${esc(x.hypothesis)}</b>: ${esc(x.argumentFor)} / ${esc(x.argumentAgainst)}`).join('<br>')}`),listItem('Recommendation Quality Gate',`Pass: ${esc(a.recommendationQualityGate?.passCount)}<br>Items: ${esc((a.recommendationQualityGate?.items||[]).length)}`),listItem('KPI Storyboard',`${(a.kpiStoryboard?.slides||[]).map(x=>`<b>${esc(x.title)}</b>: ${esc(x.message)}`).join('<br>')}`),listItem('Anonymized Pattern Library',`Patterns: ${esc((a.anonymizedPatternLibrary||[]).length)}<br>${(a.anonymizedPatternLibrary||[]).slice(0,5).map(x=>`${esc(x.patternId)} ${esc(x.playbook)} ${esc(x.module)}`).join('<br>')}`)].join('')}
function renderAutonomousOps(){const o=data.autonomousOps||{};const p=o.evidenceAcquisitionPlanner||{};document.getElementById('autonomousOps').innerHTML=[listItem('AI Investigation Queue',`${(o.investigationQueue||[]).slice(0,8).map(x=>`<b>${esc(x.priority)}</b> ${esc(x.findingId)}: ${esc(x.nextQuestion)}<br>Evidence: ${esc((x.nextEvidence||[]).join(', '))}<br>Decision: ${esc(x.decision)}`).join('<br><br>')}`),listItem('AI Follow-up Questions',`${(o.followUpQuestions||[]).slice(0,5).map(x=>`<b>${esc(x.findingId)}</b><br>${(x.questions||[]).map(q=>`${esc(q.question)} <span class="muted">(${esc(q.actionType)})</span>`).join('<br>')}`).join('<br><br>')}`),listItem('Evidence Acquisition Planner',`Target: <b>${esc(p.target?.server)}</b> / DB: <b>${esc(p.target?.database)}</b><br>Missing: ${esc(p.missingCount)}<br>${(p.tasks||[]).map(t=>`${esc(t.status)}: ${esc(t.label)}<br><span class="code">${esc(t.command)}</span>`).join('<br><br>')}`),listItem('Autonomous Change Drafting',`${(o.changeDrafts||[]).slice(0,6).map(x=>`<b>${esc(x.changeType)}</b> ${esc(x.findingId)} approval=${esc(x.approvalPath)} rollback=${esc(x.risk?.rollback)}`).join('<br>')}`),listItem('Recommendation Readiness Gate',`${(o.readinessGate||[]).slice(0,10).map(x=>`${esc(x.status)}: ${esc(x.findingId)} score=${esc(x.score)}`).join('<br>')}`),listItem('Next Best Actions',`${(o.nextBestActions||[]).map(x=>`<b>${esc(x.action)}</b> ${esc(x.findingId)}<br>${esc(x.whyThisFirst)}`).join('<br><br>')}`),listItem('Operator Decision Memory',`Status: ${esc(o.operatorDecisionMemory?.status)}<br>Model: ${esc(o.operatorDecisionMemory?.memoryModel)}<br>${(o.operatorDecisionMemory?.playbookBacklog||[]).slice(0,8).map(x=>`${esc(x.playbook)}: ${esc(x.openFindings)}`).join('<br>')}`),listItem('AI Executive Risk Briefing',`${esc(o.executiveRiskBriefing?.headline)}<br><b>Ask:</b> ${esc(o.executiveRiskBriefing?.decisionAsk)}<br><b>Non-goal:</b> ${esc(o.executiveRiskBriefing?.nonGoal)}`),listItem('20 Autonomous Ops Features',`Feature count: <b>${esc(o.featureCount)}</b><br>Safe classifier: ${esc((o.safeToAutomateClassifier||[]).length)}<br>Decision trees: ${esc((o.rootCauseDecisionTree||[]).length)}<br>Post-change checklist: ${esc((o.postChangeEvidenceChecklist||[]).join(', '))}`)].join('')}
function initTabs(){document.querySelectorAll('.tabBtn').forEach(btn=>btn.addEventListener('click',()=>{document.querySelectorAll('.tabBtn').forEach(b=>b.classList.remove('active'));document.querySelectorAll('.tabPanel').forEach(p=>p.classList.remove('active'));btn.classList.add('active');document.getElementById('tab-'+btn.dataset.tab).classList.add('active')}))}
function init(){const score=data.riskScore||0;document.getElementById('score').textContent=score;const ring=document.getElementById('scoreRing');ring.style.setProperty('--pct',score);ring.style.setProperty('--color',score>=75?'var(--green)':score>=50?'var(--amber)':'var(--red)');document.getElementById('environmentChip').textContent='Environment: '+esc(data.environment||'Unknown');document.getElementById('generated').textContent='Generated: '+new Date().toLocaleString();renderKpis();severityDonut();bars('causes',data.rootCauseBars||[],'#2563eb');bars('modules',data.modules,'#0891b2');bars('playbooks',data.playbooks,'#6d28d9');fillSelect('module',data.modules);fillSelect('playbook',data.playbooks);renderTop();renderAiTabs();renderEvidenceHealth();renderEnvironmentCompare();renderSkillsCatalog();initQa();renderAdmin();renderEnterprise();renderAdvanced();renderGovernance();renderStrategy();renderAiKi();renderMarket();renderLearning();renderAutonomous();renderAutonomousOps();initTabs();['q','sev','module','playbook'].forEach(id=>document.getElementById(id).addEventListener('input',renderRows));renderRows()}
init();
</script>
</body>
</html>"""
    html = html.replace("__PAYLOAD__", payload)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(html, encoding="utf-8")
    print(f"Wrote dashboard to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
