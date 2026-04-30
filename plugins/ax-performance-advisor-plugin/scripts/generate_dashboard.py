import argparse
import csv
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
from ax_live_blocking_intelligence import generate_ax_live_blocking_intelligence
from platform_extensions import generate_platform_extensions
from axpa_core import analyze_evidence, batch_collision_summary, load_evidence, module_health_scores, summarize_root_causes


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
    "batch-collision-and-read-pressure": "Batch collision and read pressure",
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
        parsed = {}
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
                if rows:
                    parsed = rows[0]
        except csv.Error:
            parsed = {}
        errors.append({
            "source": path.name,
            "message": text[:1200],
            "bytes": path.stat().st_size,
            "outputFile": parsed.get("output_file", ""),
            "error": parsed.get("error", ""),
            "collectedAt": parsed.get("collected_at", ""),
            "nextStep": "Collector query or permissions/schema compatibility prüfen, dann Snapshot erneut ausführen.",
        })
    return errors


def _environment_label(evidence):
    root = Path(evidence)
    metadata_path = root / "metadata.json"
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            label = metadata.get("environment") or metadata.get("server") or metadata.get("sqlServer") or metadata.get("name")
            database = metadata.get("axDatabase") or metadata.get("database")
            if label and database:
                return f"{label} / {database}"
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
    ax_live_blocking = generate_ax_live_blocking_intelligence(args.evidence)
    batch_collisions = batch_collision_summary(load_evidence(args.evidence))
    platform = generate_platform_extensions(args.evidence, Path(args.output).parent / "platform-extensions", Path(args.output).parent / f"{environment_label.split(' / ')[0]}-trends.sqlite", Path(args.output).parent / f"{environment_label.split(' / ')[0]}-pipeline-manifest.json")
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
            "axLiveBlocking": ax_live_blocking,
            "batchCollisions": batch_collisions,
            "platform": platform,
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
:root{--bg:#eef2f7;--panel:#ffffff;--panel2:#f8fafc;--ink:#121826;--muted:#667085;--line:#d7deea;--blue:#2563eb;--cyan:#0891b2;--green:#16803c;--amber:#b45309;--red:#b42318;--violet:#6d28d9;--shadow:0 18px 45px rgba(16,24,40,.08)}
*{box-sizing:border-box} body{margin:0;background:radial-gradient(circle at 20% 0,#f8fbff 0,#eef2f7 36%,#e8eef6 100%);color:var(--ink);font-family:Segoe UI,Arial,sans-serif;font-size:14px;line-height:1.45}
.wrap{max-width:1480px;margin:0 auto;padding:26px}.hero{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:18px;align-items:stretch;margin-bottom:16px}
.headline{background:linear-gradient(135deg,#111827 0%,#1f2937 60%,#0f766e 140%);color:white;border-radius:10px;padding:24px 26px;min-height:188px;display:flex;flex-direction:column;justify-content:space-between;box-shadow:var(--shadow);position:relative;overflow:hidden}.headline:after{content:"";position:absolute;right:28px;top:24px;width:220px;height:140px;border:1px solid rgba(255,255,255,.12);border-radius:10px;background:linear-gradient(135deg,rgba(255,255,255,.09),rgba(255,255,255,.02));transform:skewX(-10deg)}
.headline h1{margin:0;font-size:32px;letter-spacing:0}.headline p{max-width:850px;margin:10px 0 0;color:#d9e2ef;font-size:15px}.headline>*{position:relative;z-index:1}
.meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}.chip{border:1px solid rgba(255,255,255,.24);border-radius:999px;padding:5px 10px;color:#eef4ff;background:rgba(255,255,255,.09);font-size:12px}
.scoreCard{background:rgba(255,255,255,.92);border:1px solid rgba(215,222,234,.9);border-radius:10px;padding:18px;display:grid;place-items:center;min-height:188px;box-shadow:var(--shadow)}
.ring{--pct:50;--color:var(--amber);width:148px;height:148px;border-radius:50%;background:conic-gradient(var(--color) calc(var(--pct)*1%),#e6eaf1 0);display:grid;place-items:center;box-shadow:inset 0 0 0 1px rgba(255,255,255,.7)}.ringInner{width:108px;height:108px;background:white;border-radius:50%;display:grid;place-items:center;text-align:center;box-shadow:0 8px 18px rgba(16,24,40,.08)}.ringInner b{font-size:36px}.ringInner span{display:block;color:var(--muted);font-size:12px}
.kpis{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin-bottom:16px}.kpi{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px;min-height:98px;box-shadow:0 10px 24px rgba(16,24,40,.045);position:relative;overflow:hidden}.kpi:before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--blue)}.kpi:nth-child(2):before{background:var(--red)}.kpi:nth-child(3):before{background:var(--cyan)}.kpi:nth-child(4):before{background:var(--amber)}.kpi:nth-child(5):before{background:var(--violet)}
.kpi label{display:block;color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.06em}.kpi strong{display:block;font-size:29px;margin-top:8px;letter-spacing:0}.kpi small{display:block;color:var(--muted);margin-top:4px}
.opsMap{display:grid;grid-template-columns:1.1fr .9fr;gap:14px;margin-bottom:16px}.radar{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;box-shadow:var(--shadow)}.radar h2,.panel h2{font-size:16px;margin:0 0 14px}.signalGrid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.signal{border:1px solid #e5eaf2;border-radius:9px;background:linear-gradient(180deg,#fff,#f8fafc);padding:12px;min-height:96px}.signal b{display:block;font-size:24px}.signal span{color:var(--muted);font-size:12px}.signal.good{border-color:#bbf7d0}.signal.warn{border-color:#fedf89}.signal.bad{border-color:#fecaca}.miniTimeline{display:grid;grid-template-columns:repeat(24,1fr);gap:3px;align-items:end;height:92px;border:1px solid #e5eaf2;border-radius:9px;padding:10px;background:#fbfcff}.tick{background:#cbd5e1;border-radius:3px 3px 0 0;min-height:4px}.tick.hot{background:#d95f0e}.tick.warm{background:#d97706}.tick.cool{background:#0891b2}
.grid{display:grid;grid-template-columns:1.15fr .85fr;gap:14px}.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;min-width:0;box-shadow:0 10px 24px rgba(16,24,40,.045)}
.bars{display:grid;gap:10px}.barRow{display:grid;grid-template-columns:minmax(120px,220px) 1fr 52px;gap:10px;align-items:center}.barLabel{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#344054}.barTrack{height:13px;background:#edf1f7;border-radius:999px;overflow:hidden}.barFill{height:100%;background:linear-gradient(90deg,var(--blue),#60a5fa);border-radius:999px}.barValue{text-align:right;color:var(--muted);font-variant-numeric:tabular-nums}
.donutWrap{display:grid;grid-template-columns:190px 1fr;gap:12px;align-items:center}.donut{width:170px;height:170px;border-radius:50%;display:grid;place-items:center;background:#e6eaf1}.donutCenter{width:96px;height:96px;border-radius:50%;background:white;display:grid;place-items:center;text-align:center;box-shadow:0 8px 18px rgba(16,24,40,.08)}.legend{display:grid;gap:8px}.legendItem{display:grid;grid-template-columns:12px 1fr 40px;gap:8px;align-items:center}.swatch{width:12px;height:12px;border-radius:3px}
.filters{position:sticky;top:0;z-index:4;background:rgba(238,242,247,.93);backdrop-filter:blur(10px);border:1px solid var(--line);border-radius:10px;padding:12px;display:grid;grid-template-columns:1fr 160px 190px 160px;gap:10px;margin:18px 0;box-shadow:0 10px 24px rgba(16,24,40,.06)}
input,select{width:100%;border:1px solid #cbd5e1;border-radius:7px;padding:9px 10px;background:white;color:var(--ink)}
.tableWrap{background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:auto;box-shadow:var(--shadow)}table{width:100%;border-collapse:collapse}th,td{padding:10px 12px;border-bottom:1px solid #edf1f7;text-align:left;vertical-align:top}th{background:#f8fafc;color:#475467;font-size:12px;text-transform:uppercase;letter-spacing:.04em;position:sticky;top:0;z-index:1}tr:hover td{background:#fbfcff}
.sev{display:inline-block;border-radius:999px;padding:3px 8px;font-weight:700;font-size:12px}.critical{background:#fee4e2;color:#912018}.high{background:#ffead5;color:#93370d}.medium{background:#fef7c3;color:#854a0e}.low{background:#dcfae6;color:#085d3a}
.topList{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.finding{border:1px solid #edf1f7;border-radius:9px;padding:12px;background:linear-gradient(180deg,#fff,#fbfcff)}.findingTitle{display:flex;gap:8px;align-items:flex-start;justify-content:space-between}.findingTitle b{font-size:13px}.finding p{margin:8px 0 0;color:var(--muted);font-size:12px}.muted{color:var(--muted)}.foot{margin-top:14px;color:var(--muted);font-size:12px}
.tabs{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0 10px}.tabBtn{border:1px solid var(--line);background:white;color:#344054;border-radius:7px;padding:8px 11px;cursor:pointer;box-shadow:0 4px 12px rgba(16,24,40,.035)}.tabBtn:hover{border-color:#9aa9bd}.tabBtn.active{background:#111827;color:white;border-color:#111827}.tabPanel{display:none}.tabPanel.active{display:block}.twoCol{display:grid;grid-template-columns:1fr 1fr;gap:14px}.miniGrid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.mini{border:1px solid #edf1f7;border-radius:9px;padding:10px;background:#fbfcff}.mini b{display:block;font-size:18px}.list{display:grid;gap:8px}.listItem{border:1px solid #edf1f7;border-radius:9px;padding:11px;background:linear-gradient(180deg,#fff,#fbfcff)}.listItem h3{font-size:13px;margin:0 0 6px}.listItem p{margin:0;color:var(--muted);font-size:12px}.warn{border-color:#fedf89;background:#fffcf5}.code{font-family:Consolas,monospace;font-size:12px;white-space:pre-wrap;word-break:break-word;color:#344054}
.collisionCards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.collisionCard{border:1px solid #e5eaf2;border-radius:9px;padding:11px;background:#fff}.collisionCard b{display:block;margin-bottom:4px}.collisionBar{height:8px;background:#edf1f7;border-radius:999px;overflow:hidden;margin-top:8px}.collisionFill{height:100%;background:linear-gradient(90deg,#d95f0e,#f59e0b);border-radius:999px}
.spark{display:flex;gap:4px;align-items:end;height:86px;border:1px solid #edf1f7;border-radius:9px;padding:9px;background:#fbfcff;margin-top:8px}.sparkBar{flex:1;min-width:5px;border-radius:4px 4px 0 0;background:linear-gradient(180deg,#2563eb,#60a5fa)}.sparkBar.red{background:linear-gradient(180deg,#b42318,#f97316)}.sparkBar.green{background:linear-gradient(180deg,#16803c,#22c55e)}
.sparkWrap{border:1px solid #e5eaf2;border-radius:10px;background:#fbfcff;padding:10px;margin-top:8px}.sparkMeta{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px}.sparkMeta b{font-size:12px}.sparkMeta span{font-size:12px;color:var(--muted)}.sparkWrap .spark{border:0;border-radius:0;background:transparent;padding:0;margin:0;height:54px}.platformHero{display:grid;grid-template-columns:1.3fr .7fr;gap:12px;margin-bottom:12px}.platformBrief{border:1px solid #d7deea;border-radius:12px;background:linear-gradient(135deg,#111827,#1f2937);color:white;padding:16px;min-height:150px}.platformBrief h3{margin:0 0 8px;font-size:17px}.platformBrief p{margin:0;color:#d9e2ef}.metricGrid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.metricCard{border:1px solid #e5eaf2;border-radius:10px;background:white;padding:12px;min-height:84px}.metricCard b{display:block;font-size:24px;color:#111827}.metricCard span{display:block;color:var(--muted);font-size:12px}.metricCard.bad{border-color:#fecaca;background:#fff7f7}.metricCard.warn{border-color:#fedf89;background:#fffcf5}.metricCard.good{border-color:#bbf7d0;background:#f7fff9}.platformTable{width:100%;border:1px solid #e5eaf2;border-radius:9px;overflow:hidden;margin-top:8px}.platformTable table{font-size:12px}.platformTable th{position:static}.statusDot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;background:#94a3b8}.statusDot.red,.statusDot.critical,.statusDot.high,.statusDot.bad{background:#b42318}.statusDot.amber,.statusDot.medium,.statusDot.warn{background:#d97706}.statusDot.green,.statusDot.good,.statusDot.ok{background:#16803c}
.chartGrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:8px 0 12px}.chartCard{border:1px solid #e5eaf2;border-radius:10px;background:linear-gradient(180deg,#fff,#fbfcff);padding:12px;min-width:0}.chartCard h3{font-size:13px;margin:0 0 8px}.chartSub{color:var(--muted);font-size:12px;margin-top:-4px;margin-bottom:8px}.hbarChart{display:grid;gap:8px}.hbar{display:grid;grid-template-columns:minmax(90px,190px) 1fr 48px;gap:8px;align-items:center}.hbarLabel{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#344054;font-size:12px}.hbarTrack{height:16px;background:#edf1f7;border-radius:999px;overflow:hidden}.hbarFill{height:100%;border-radius:999px;background:linear-gradient(90deg,#2563eb,#60a5fa)}.hbarValue{text-align:right;color:#667085;font-size:12px;font-variant-numeric:tabular-nums}.donutMini{display:grid;grid-template-columns:88px 1fr;gap:12px;align-items:center}.donutMiniRing{width:82px;height:82px;border-radius:50%;display:grid;place-items:center;background:#e6eaf1}.donutMiniCenter{width:48px;height:48px;border-radius:50%;background:white;display:grid;place-items:center;font-weight:700;box-shadow:0 6px 16px rgba(16,24,40,.08)}.donutLegend{display:grid;gap:6px}.donutLegend div{display:grid;grid-template-columns:10px 1fr auto;gap:7px;align-items:center;font-size:12px}.heatmap{display:grid;grid-template-columns:repeat(auto-fit,minmax(52px,1fr));gap:6px}.heatCell{border:1px solid #e5eaf2;border-radius:8px;min-height:54px;padding:7px;background:#f8fafc;display:flex;flex-direction:column;justify-content:space-between}.heatCell b{font-size:13px}.heatCell span{font-size:11px;color:#667085}.heatCell.hot{background:#fff1e7;border-color:#f97316}.heatCell.warn{background:#fffcf5;border-color:#fedf89}.heatCell.good{background:#f7fff9;border-color:#bbf7d0}.miniStatLine{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}.miniStatLine span{border:1px solid #e5eaf2;border-radius:999px;padding:4px 8px;background:white;color:#475467;font-size:12px}
.flow{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}.flowStep{border:1px solid #d7deea;border-radius:999px;padding:6px 10px;background:#fff;font-size:12px}.flowStep.hot{border-color:#f97316;background:#fff7ed}.timelineVis{display:grid;gap:8px;margin-top:8px}.timeEvent{display:grid;grid-template-columns:118px 98px 1fr;gap:8px;align-items:start;border-left:3px solid #94a3b8;padding:7px 8px;background:#fbfcff;border-radius:0 8px 8px 0}.timeEvent.high,.timeEvent.critical{border-left-color:#b42318}.timeEvent.medium{border-left-color:#d97706}.timeEvent.info{border-left-color:#2563eb}.graphBox{border:1px solid #e5eaf2;border-radius:9px;background:#fbfcff;padding:10px;margin-top:8px}.visualGrid{display:grid;grid-template-columns:1.1fr .9fr;gap:10px;margin:8px 0 12px}.visualGrid.three{grid-template-columns:1fr 1fr 1fr}.networkBox{border:1px solid #e5eaf2;border-radius:10px;background:radial-gradient(circle at 30% 20%,#ffffff,#f8fafc);padding:10px;min-height:240px}.visualTitle{display:flex;justify-content:space-between;gap:8px;align-items:center;margin-bottom:6px}.visualTitle b{font-size:13px}.visualBadge{border:1px solid #d7deea;border-radius:999px;padding:3px 8px;background:#fff;font-size:11px;color:#475569}.matrixBox{border:1px solid #e5eaf2;border-radius:10px;background:#fff;padding:10px;display:grid;gap:8px}.matrixCell{border:1px solid #edf1f7;border-radius:8px;padding:9px;background:#fbfcff}.matrixCell b{display:block}.matrixCell.good{border-color:#bbf7d0;background:#f7fff9}.matrixCell.warn{border-color:#fedf89;background:#fffcf5}.matrixCell.bad{border-color:#fecaca;background:#fff7f7}.nodeGrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:8px}.nodeCard{border:1px solid #d7deea;border-radius:8px;background:white;padding:9px}.nodeCard.high{border-color:#fecaca;background:#fff7f7}.nodeCard.medium{border-color:#fedf89;background:#fffcf5}.chain{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}.chain span{border:1px solid #d7deea;border-radius:6px;padding:4px 6px;background:white;font-size:12px}
@media(max-width:1080px){.hero,.grid,.opsMap{grid-template-columns:1fr}.kpis{grid-template-columns:repeat(2,1fr)}.filters{grid-template-columns:1fr 1fr}.donutWrap{grid-template-columns:1fr}.topList,.collisionCards{grid-template-columns:1fr}}@media(max-width:640px){.wrap{padding:12px}.kpis,.filters,.signalGrid{grid-template-columns:1fr}.headline h1{font-size:24px}.barRow{grid-template-columns:1fr 1fr 38px}.miniGrid{grid-template-columns:1fr 1fr}}
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

  <section class="opsMap">
    <div class="radar">
      <h2>Operations Radar</h2>
      <div class="signalGrid" id="opsSignals"></div>
    </div>
    <div class="radar">
      <h2>Batch Collision Timeline</h2>
      <div class="miniTimeline" id="batchTimeline"></div>
    </div>
  </section>

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
    <button class="tabBtn" data-tab="batchcollisions">Batch Collisions</button>
    <button class="tabBtn" data-tab="liveblocking">AX Live Blocking</button>
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
    <button class="tabBtn" data-tab="platform">Platform</button>
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
  <section class="tabPanel" id="tab-batchcollisions"><div class="panel"><h2>AX Batch Collision Analysis</h2><div class="list" id="batchCollisions"></div></div></section>
  <section class="tabPanel" id="tab-liveblocking"><div class="panel"><h2>AX Live Blocking</h2><div class="list" id="axLiveBlocking"></div></div></section>
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
  <section class="tabPanel" id="tab-platform">
    <div class="panel">
      <h2>Platform Extensions</h2>
      <div class="list" id="platformExtensions"></div>
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
function renderOpsRadar(){const b=data.batchCollisions||{};const blocked=data.axLiveBlocking?.blockedRows||0;const errors=(data.collectorErrors||[]).length;const high=data.findings.filter(f=>['critical','high'].includes(f.severity)).length;const sig=[['Batch Peak',b.peakConcurrency||0,'parallel laufende Tasks',(b.peakConcurrency||0)>=10?'bad':(b.peakConcurrency||0)>=5?'warn':'good'],['Kollisionen',b.collisionCount||0,'erkannte Overlaps',(b.collisionCount||0)>=30?'bad':(b.collisionCount||0)>0?'warn':'good'],['Live Blocking',blocked,'blockierte AX Worker',blocked>0?'bad':'good'],['High Risk',high,'High/Critical Findings',high>20?'bad':high>5?'warn':'good']];document.getElementById('opsSignals').innerHTML=sig.map(x=>`<div class="signal ${x[3]}"><span>${esc(x[0])}</span><b>${esc(x[1])}</b><span>${esc(x[2])}</span></div>`).join('');const groups=(b.groupCollisions||[]).slice(0,24);const max=Math.max(1,...groups.map(g=>g.totalOverlapSeconds||0));document.getElementById('batchTimeline').innerHTML=Array.from({length:24},(_,i)=>{const g=groups[i]||{};const h=Math.max(4,Math.round(((g.totalOverlapSeconds||0)/max)*76));const cls=h>54?'hot':h>24?'warm':'cool';return `<div class="tick ${cls}" style="height:${h}px" title="${esc(g.groups||'no collision')} ${esc(g.totalOverlapSeconds||0)}s"></div>`}).join('')}
function renderTop(){const top=data.topFindings.slice(0,10);document.getElementById('topFindings').innerHTML=top.map(f=>`<article class="finding"><div class="findingTitle"><b>${esc(f.title)}</b><span class="sev ${esc(f.severity)}">${esc(f.severity)}</span></div><p>${esc(f.recommendation?.summary||f.likelyCause||'')}</p><p><b>Playbook:</b> ${esc(f.recommendation?.playbook||'')} <span class="muted">|</span> <b>Module:</b> ${esc(f.axContext?.module||'Unknown')} <span class="muted">|</span> <b>Confidence:</b> ${esc(f.confidence||'')}</p></article>`).join('')}
function filtered(){const q=document.getElementById('q').value.toLowerCase();const sev=document.getElementById('sev').value;const mod=document.getElementById('module').value;const play=document.getElementById('playbook').value;return data.findings.filter(f=>(!sev||f.severity===sev)&&(!mod||(f.axContext?.module||'Unknown')===mod)&&(!play||(f.recommendation?.playbook||'Unknown')===play)&&(!q||JSON.stringify(f).toLowerCase().includes(q))).sort((a,b)=>(sevWeight[b.severity]||0)-(sevWeight[a.severity]||0))}
function renderRows(){const rows=filtered();document.getElementById('rows').innerHTML=rows.slice(0,250).map(f=>{const evidence=(f.evidence||[]).slice(0,2).map(e=>`${esc(e.source)}:${esc(e.metric)}=${esc(e.value)}`).join('<br>');return `<tr><td>${esc(f.id)}</td><td><span class="sev ${esc(f.severity)}">${esc(f.severity)}</span><br><span class="muted">${esc(f.confidence)}</span></td><td>${esc(f.axContext?.module||'Unknown')}</td><td><b>${esc(f.title)}</b><br><span class="muted">${esc(f.likelyCause||'')}</span></td><td>${esc(f.recommendation?.summary||'')}<br><span class="muted">${esc(f.recommendation?.playbook||'')}</span></td><td>${evidence}</td></tr>`}).join('');document.getElementById('foot').textContent=`${rows.length} von ${data.findings.length} Findings angezeigt, Tabelle auf 250 Zeilen begrenzt.`}
function listItem(title,body,extra=''){return `<article class="listItem"><h3>${esc(title)}</h3><p>${body}</p>${extra}</article>`}
function spark(series,cls='',label='Trend'){const vals=(series||[]).map(x=>Number(x.value||0));if(!vals.length)return `<div class="sparkWrap"><div class="sparkMeta"><b>${esc(label)}</b><span>No data</span></div></div>`;const max=Math.max(1,...vals);const latest=vals[vals.length-1];return `<div class="sparkWrap"><div class="sparkMeta"><b>${esc(label)}</b><span>Latest ${esc(latest)} | Max ${esc(max)}</span></div><div class="spark">${vals.slice(-30).map((v,i)=>`<div class="sparkBar ${cls}" title="Run ${i+1}: ${esc(v)}" style="height:${Math.max(5,Math.round(v/max*54))}px"></div>`).join('')}</div></div>`}
function metricCard(label,value,sub='',cls=''){return `<div class="metricCard ${esc(cls)}"><b>${esc(value)}</b><span>${esc(label)}</span>${sub?`<span>${esc(sub)}</span>`:''}</div>`}
function hbarChart(title,rows,sub=''){const clean=(rows||[]).filter(x=>x&&Number(x.value||0)>0).slice(0,8);const max=Math.max(1,...clean.map(x=>Number(x.value||0)));return `<div class="chartCard"><h3>${esc(title)}</h3>${sub?`<div class="chartSub">${esc(sub)}</div>`:''}<div class="hbarChart">${clean.length?clean.map((x,i)=>{const cls=i===0?'#b42318':i===1?'#d95f0e':i===2?'#d97706':'#2563eb';return `<div class="hbar" title="${esc(x.title||x.name)} ${esc(x.value)}"><div class="hbarLabel">${esc(x.name)}</div><div class="hbarTrack"><div class="hbarFill" style="width:${Math.max(5,Number(x.value||0)/max*100)}%;background:linear-gradient(90deg,${cls},#60a5fa)"></div></div><div class="hbarValue">${esc(x.value)}</div></div>`}).join(''):'<span class="muted">Keine verwertbaren Daten</span>'}</div></div>`}
function donutChart(title,items,sub=''){const rows=(items||[]).filter(x=>x&&Number(x.value||0)>=0).slice(0,6);const total=rows.reduce((s,x)=>s+Number(x.value||0),0)||1;let start=0;const palette=['#b42318','#d95f0e','#d97706','#2563eb','#0891b2','#16803c'];const segs=rows.map((x,i)=>{const pct=Number(x.value||0)/total*100;const seg=`${palette[i%palette.length]} ${start}% ${start+pct}%`;start+=pct;return seg});return `<div class="chartCard"><h3>${esc(title)}</h3>${sub?`<div class="chartSub">${esc(sub)}</div>`:''}<div class="donutMini"><div class="donutMiniRing" style="background:conic-gradient(${segs.join(',')},#e6eaf1 0)"><div class="donutMiniCenter">${esc(total)}</div></div><div class="donutLegend">${rows.length?rows.map((x,i)=>`<div><span class="swatch" style="background:${palette[i%palette.length]}"></span><span>${esc(x.name)}</span><b>${esc(x.value)}</b></div>`).join(''):'<span class="muted">Keine Daten</span>'}</div></div></div>`}
function heatmapChart(title,rows,sub=''){const clean=(rows||[]).filter(Boolean).slice(0,24);const vals=clean.map(x=>Number(x.value||0));const max=Math.max(1,...vals);return `<div class="chartCard"><h3>${esc(title)}</h3>${sub?`<div class="chartSub">${esc(sub)}</div>`:''}<div class="heatmap">${clean.length?clean.map(x=>{const v=Number(x.value||0);const ratio=v/max;const cls=ratio>.66?'hot':ratio>.33?'warn':'good';return `<div class="heatCell ${cls}" title="${esc(x.name)} ${esc(v)}"><span>${esc(x.name)}</span><b>${esc(v)}</b></div>`}).join(''):'<span class="muted">Keine Daten</span>'}</div></div>`}
function chartGrid(...charts){return `<div class="chartGrid">${charts.filter(Boolean).join('')}</div>`}
function topFromObjects(rows,labelKeys,valueKeys){return (rows||[]).map((x,i)=>({name:labelKeys.map(k=>x?.[k]).find(Boolean)||`Item ${i+1}`,value:Number(valueKeys.map(k=>x?.[k]).find(v=>Number(v)>0)||0),title:JSON.stringify(x)})).sort((a,b)=>b.value-a.value)}
function platformTable(rows,cols){return `<div class="platformTable"><table><thead><tr>${cols.map(c=>`<th>${esc(c[1])}</th>`).join('')}</tr></thead><tbody>${(rows||[]).map(r=>`<tr>${cols.map(c=>`<td>${c[2]?c[2](r):esc(r[c[0]])}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`}
function platformOverview(p){const live=p.liveBatchCollisionWatch||{};const sla=p.axBusinessProcessSla||{};const gaps=p.evidenceGapAssistant||{};const reg=p.deploymentRegressionGuard||{};const alerts=p.alertingRules||{};const work=p.adminRemediationWorkbench||{};return `<div class="platformHero"><div class="platformBrief"><h3>Platform Command Center</h3><p>Die wichtigsten Betriebsrisiken aus Batch, Blocking, Query Store, Trendstore und AI/KI sind hier zu einer handlungsorientierten Sicht zusammengezogen.</p><div class="flow"><span class="flowStep hot">Batch</span><span class="flowStep hot">Blocking</span><span class="flowStep">Query Store</span><span class="flowStep">Lifecycle</span><span class="flowStep">AI/KI</span></div></div><div class="metricGrid">${metricCard('Batch Alerts',live.alerts?.length||0,`Peak ${live.peakConcurrency||0}`,(live.alerts?.length||0)>0?'bad':'good')}${metricCard('Blocking Chains',p.sqlBlockingChainRecorder?.chainCount||0,`${p.sqlBlockingChainRecorder?.sampleCount||0} samples`,(p.sqlBlockingChainRecorder?.chainCount||0)>0?'warn':'good')}${metricCard('Process SLA',sla.processCount||0,'business views','')}${metricCard('Evidence Gaps',gaps.gapCount||0,`${gaps.lowConfidenceFindings||0} low confidence`,(gaps.gapCount||0)>0?'warn':'good')}${metricCard('Regressions',reg.regressionCount||0,reg.status||'',(reg.regressionCount||0)>0?'bad':'good')}${metricCard('Admin Actions',work.actionCount||0,`${alerts.enabledCount||0}/${alerts.ruleCount||0} alerts on`,'')}</div></div>`}
function flow(steps,hot=''){return `<div class="flow">${(steps||[]).map(s=>`<span class="flowStep ${s===hot?'hot':''}">${esc(s)}</span>`).join('')}</div>`}
function timeline(events){return `<div class="timelineVis">${(events||[]).slice(0,28).map(e=>`<div class="timeEvent ${esc(e.severity||'info')}"><span class="muted">${esc(String(e.time||'').slice(0,16))}</span><b>${esc(e.type)}</b><div>${esc(e.title)}<br><span class="muted">${esc(e.detail)}</span></div></div>`).join('')}</div>`}
function nodeGrid(nodes){return `<div class="nodeGrid">${(nodes||[]).slice(0,16).map(n=>`<div class="nodeCard ${esc(n.risk)}"><b>${esc(n.aos)}</b><br>Sessions ${esc(n.sessions)} | Batch ${esc(n.batchTasks)} | Blocked ${esc(n.blockedRows)}<br><span class="muted">Pressure ${esc(n.pressure)} | Groups: ${esc(Object.keys(n.groups||{}).slice(0,4).join(', '))}</span></div>`).join('')}</div>`}
function deadlockSvg(graph){const nodes=(graph?.nodes||[]).slice(0,5);const res=(graph?.resources||[]).slice(0,4);if(!nodes.length&&!res.length)return '<div class="graphBox muted">No parsed deadlock nodes.</div>';const all=[...nodes.map((n,i)=>({id:n.id,label:n.spid||n.id,type:'p',victim:n.victim,x:80+i*120,y:42})),...res.map((r,i)=>({id:r.id,label:(r.object||r.id||'resource').slice(0,18),type:'r',x:120+i*130,y:132}))];const pos=new Map(all.map(n=>[n.id,n]));const lines=(graph.edges||[]).slice(0,12).map(e=>{const a=pos.get(e.from),b=pos.get(e.to);return a&&b?`<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" stroke="${e.type==='waits'?'#b42318':'#2563eb'}" stroke-width="2"/>`:''}).join('');const circles=all.map(n=>`<g><circle cx="${n.x}" cy="${n.y}" r="26" fill="${n.victim?'#fee4e2':n.type==='r'?'#e0f2fe':'#eef2ff'}" stroke="${n.victim?'#b42318':'#64748b'}"/><text x="${n.x}" y="${n.y+4}" text-anchor="middle" font-size="10">${esc(n.label)}</text></g>`).join('');return `<div class="graphBox"><svg viewBox="0 0 720 190" width="100%" height="190" role="img">${lines}${circles}</svg></div>`}
function topologySvg(aos){const nodes=(aos.nodes||[]).slice(0,8);if(!nodes.length)return '<div class="graphBox muted">No AOS nodes.</div>';const max=Math.max(1,...nodes.map(n=>Number(n.pressure||0)));return `<div class="graphBox"><svg viewBox="0 0 760 220" width="100%" height="220" role="img">${nodes.map((n,i)=>{const x=70+(i%4)*180,y=65+Math.floor(i/4)*95,r=22+Math.round(Number(n.pressure||0)/max*20);return `<g><circle cx="${x}" cy="${y}" r="${r}" fill="${n.risk==='high'?'#fee4e2':n.risk==='medium'?'#fef7c3':'#dcfae6'}" stroke="#64748b"/><text x="${x}" y="${y-2}" text-anchor="middle" font-size="11">${esc(String(n.aos).slice(0,14))}</text><text x="${x}" y="${y+13}" text-anchor="middle" font-size="10">B${esc(n.batchTasks)} S${esc(n.sessions)}</text></g>`}).join('')}</svg></div>`}
function dependencySvg(g){const edges=(g?.edges||[]).slice(0,12);const names=[...new Set(edges.flatMap(e=>[e.fromGroup,e.toGroup]).filter(Boolean))].slice(0,10);if(!names.length)return '<div class="networkBox muted">No batch dependency edges.</div>';const cx=360,cy=150,rad=105;const pos=new Map(names.map((n,i)=>[n,{x:cx+Math.cos((Math.PI*2*i/names.length)-Math.PI/2)*rad,y:cy+Math.sin((Math.PI*2*i/names.length)-Math.PI/2)*rad}]));const max=Math.max(1,...edges.map(e=>Number(e.count||0)));const lines=edges.map(e=>{const a=pos.get(e.fromGroup),b=pos.get(e.toGroup);return a&&b?`<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" stroke="#2563eb" stroke-opacity=".45" stroke-width="${1+Number(e.count||0)/max*5}"><title>${esc(e.fromGroup)} -> ${esc(e.toGroup)} ${esc(e.count)}</title></line>`:''}).join('');const nodes=names.map(n=>{const p=pos.get(n);const risk=(g?.rescheduleRisks||[]).filter(r=>r.moveGroup===n).length;return `<g><circle cx="${p.x}" cy="${p.y}" r="${risk?28:23}" fill="${risk?'#fff1e7':'#e0f2fe'}" stroke="${risk?'#f97316':'#0891b2'}" stroke-width="2"/><text x="${p.x}" y="${p.y+4}" text-anchor="middle" font-size="11" font-weight="700">${esc(String(n).slice(0,10))}</text><text x="${p.x}" y="${p.y+20}" text-anchor="middle" font-size="9">${risk?risk+' risks':''}</text></g>`}).join('');return `<div class="networkBox"><div class="visualTitle"><b>Batch Dependency Network</b><span class="visualBadge">${esc(edges.length)} edges</span></div><svg viewBox="0 0 720 300" width="100%" height="300" role="img">${lines}${nodes}</svg></div>`}
function maturityRadar(m){const comps=m?.components||{};const entries=Object.entries(comps);if(!entries.length)return '<div class="networkBox muted">No maturity components.</div>';const cx=180,cy=150,rad=95;const max=20;const pts=entries.map(([k,v],i)=>{const a=(Math.PI*2*i/entries.length)-Math.PI/2;return {k,v:Number(v||0),x:cx+Math.cos(a)*rad*(Number(v||0)/max),y:cy+Math.sin(a)*rad*(Number(v||0)/max),lx:cx+Math.cos(a)*(rad+24),ly:cy+Math.sin(a)*(rad+24)}});const poly=pts.map(p=>`${p.x},${p.y}`).join(' ');const axes=pts.map(p=>`<line x1="${cx}" y1="${cy}" x2="${p.lx}" y2="${p.ly}" stroke="#d7deea"/><text x="${p.lx}" y="${p.ly}" text-anchor="middle" font-size="10">${esc(p.k)}</text>`).join('');return `<div class="networkBox"><div class="visualTitle"><b>Operational Maturity Radar</b><span class="visualBadge">Score ${esc(m?.score||0)}</span></div><svg viewBox="0 0 360 300" width="100%" height="300" role="img"><circle cx="${cx}" cy="${cy}" r="${rad}" fill="none" stroke="#e5eaf2"/><circle cx="${cx}" cy="${cy}" r="${rad/2}" fill="none" stroke="#edf1f7"/>${axes}<polygon points="${poly}" fill="rgba(37,99,235,.22)" stroke="#2563eb" stroke-width="2"/>${pts.map(p=>`<circle cx="${p.x}" cy="${p.y}" r="4" fill="#2563eb"><title>${esc(p.k)} ${esc(p.v)}</title></circle>`).join('')}<text x="${cx}" y="${cy+5}" text-anchor="middle" font-size="22" font-weight="800">${esc(m?.score||0)}</text></svg></div>`}
function decisionMatrix(s){const d=s?.d365MigrationSignalDashboard||{};const e=s?.evidenceSla||{};const mature=s?.operationalMaturityScore||{};const cls=d.decision==='tune-first'?'good':'warn';return `<div class="matrixBox"><div class="matrixCell ${cls}"><b>D365 Decision</b>${esc(d.decision||'n/a')}<br><span class="muted">${esc(d.message||'')}</span></div><div class="matrixCell ${Number(e.score||0)>=80?'good':'warn'}"><b>Evidence SLA</b>${esc(e.score||0)} / ${esc(e.status||'')}</div><div class="matrixCell ${Number(mature.score||0)>=80?'good':'warn'}"><b>Operational Maturity</b>${esc(mature.score||0)} / ${esc(mature.grade||'')}</div><div class="matrixCell warn"><b>Signal Balance</b>structural=${esc(d.structuralSignals||0)} | tuning=${esc(d.tuningSignals||0)}</div></div>`}
function batchRescheduleDetails(cal){const proposals=(cal?.proposals||[]).slice(0,10);const low=(cal?.lowLoadSlots||[]).slice(0,6).map(x=>`${esc(x.hour)} (${esc(x.taskCount)} tasks)`).join(', ');const peaks=(cal?.peakSlots||[]).slice(0,6).map(x=>`${esc(x.hour)} ${esc(x.taskCount)} tasks, dominant ${esc(x.dominantGroup)}`).join('<br>');return `<div class="metricGrid">${metricCard('Batch Tasks',cal?.taskCount||0,'analysed tasks','')}${metricCard('Vorschlaege',proposals.length,'concrete move candidates',proposals.length?'warn':'good')}${metricCard('Low-load Slots',(cal?.lowLoadSlots||[]).length,low,'good')}</div><br><b>Peak Slots:</b><br>${peaks||'Keine Peak-Slots'}${platformTable(proposals,[['currentHour','Von'],['targetHour','Nach'],['moveGroup','Gruppe'],['moveTaskCount','Tasks'],['targetTaskCount','Ziel-Tasks'],['expectedOverlapReductionPercent','Reduktion %'],['expectedEffect','Effekt']])}<br>${proposals.map((p,i)=>`<div class="listItem"><h3>${i+1}. ${esc(p.proposal)}</h3><p><b>Entscheidung:</b> ${esc(p.decisionRationale||p.reason)}<br><b>Warum genau diese Gruppe:</b> ${esc(p.moveGroup)} macht ${esc(p.groupSharePercent||0)}% der Tasks im Peak ${esc(p.currentHour)} aus. Nach Verschiebung sinkt der Peak rechnerisch von ${esc(p.taskCount)} auf ${esc(p.currentPeakAfterMove)} Tasks.<br><b>Warum dieser Zielslot:</b> ${esc(p.targetHour)} hat aktuell ${esc(p.targetTaskCount)} Task(s), davon ${esc(p.targetSameGroupTasks)} aus derselben Gruppe. Load Score: ${esc(p.targetLoadScore)}.<br><b>Erwarteter Effekt:</b> ${esc(p.expectedEffect)}<br><b>Risikoannahme:</b> ${esc(p.riskNote)}<br><b>Konkreter Change-Kandidat:</b> ${esc(p.changeCandidate)}<br><b>Umsetzung:</b> ${esc(p.implementationHint)}<br><b>Validierung:</b> ${esc(p.validation)}<br><b>Rollback:</b> ${esc(p.rollback)}<br><b>Beispiel-Tasks:</b><br>${(p.exampleTasks||[]).slice(0,6).map(t=>`${esc(t.caption)} <span class="muted">task=${esc(t.taskId)}, duration=${esc(t.durationSeconds)}s</span>`).join('<br>')||'Keine Beispiel-Tasks'}</p></div>`).join('')}`}
function batchDependencyDetails(g){const edgeBars=(g?.edges||[]).slice(0,10).map(e=>({name:`${e.fromGroup||'?'} -> ${e.toGroup||'?'}`,value:e.count||0}));return `<div class="metricGrid">${metricCard('Job Chains',g?.chainCount||0,'batch jobs with task order','')}${metricCard('Group Edges',g?.edgeCount||0,'cross-group dependencies',(g?.edgeCount||0)?'warn':'good')}${metricCard('Move Risks',(g?.rescheduleRisks||[]).length,'validate before moving',(g?.rescheduleRisks||[]).length?'warn':'good')}</div><div class="visualGrid">${dependencySvg(g)}${hbarChart('Staerkste Gruppen-Abhaengigkeiten',edgeBars,'Dicke Linien und Balken zeigen, welche Gruppen beim Rescheduling zuerst geschuetzt werden muessen.')}</div>${platformTable((g?.edges||[]).slice(0,12),[['fromGroup','Von Gruppe'],['toGroup','Nach Gruppe'],['count','Ketten']])}${platformTable((g?.rescheduleRisks||[]).slice(0,12),[['moveGroup','Move Group'],['dependentGroups','Abhaengig von',x=>esc((x.dependentGroups||[]).join(', '))],['risk','Risiko'],['validation','Validierung']])}<br>${(g?.chains||[]).slice(0,8).map(c=>`<div class="listItem"><h3>${esc(c.risk)}: ${esc(c.jobName)} (${esc(c.jobId)})</h3><p><b>Gruppen:</b> ${esc((c.groups||[]).join(' -> '))}<br><b>Tasks:</b> ${esc(c.taskCount)} | <b>Dauer:</b> ${esc(c.durationSeconds)}s<br><b>Transitions:</b><br>${(c.transitions||[]).map(t=>`${esc(t.fromGroup)} -> ${esc(t.toGroup)}: ${esc(t.fromTask)} -> ${esc(t.toTask)}`).join('<br>')||'Keine Gruppenwechsel'}</p></div>`).join('')}`}
function strategicUspDetails(s){const coverage=[{name:'SLA contracts',value:s?.batchSlaContractManager?.contractCount||0},{name:'AOS recommendations',value:(s?.aosAffinityAdvisor?.recommendations||[]).length},{name:'Archive candidates',value:s?.dataGrowthArchivingRoi?.candidateCount||0},{name:'Change simulations',value:s?.changeSimulationQueue?.simulationCount||0},{name:'Known matches',value:s?.knownIssueMatcher?.matchCount||0}];const aosBars=(s?.aosAffinityAdvisor?.recommendations||[]).slice(0,8).map(x=>({name:x.aos||'AOS',value:(Number(x.sessions||0)+Number(x.batchTasks||0)+Number(x.blockedRows||0))}));const archiveBars=(s?.dataGrowthArchivingRoi?.candidates||[]).slice(0,8).map(x=>({name:x.table||'table',value:x.rows||x.modifications||0}));return `<div class="metricGrid">${metricCard('Maturity',s?.operationalMaturityScore?.score??0,`grade ${s?.operationalMaturityScore?.grade||''}`,'good')}${metricCard('Evidence SLA',s?.evidenceSla?.score??0,s?.evidenceSla?.status||'',(s?.evidenceSla?.score||0)>=80?'good':'warn')}${metricCard('D365 Signal',s?.d365MigrationSignalDashboard?.decision||'n/a',`${s?.d365MigrationSignalDashboard?.structuralSignals||0} structural`,'warn')}</div><div class="visualGrid">${maturityRadar(s?.operationalMaturityScore)}${decisionMatrix(s)}</div>${chartGrid(hbarChart('Strategic USP Coverage',coverage,'Reale Ausgaben je USP.'),donutChart('Maturity Components',Object.entries(s?.operationalMaturityScore?.components||{}).map(([name,value])=>({name,value})),'Monitoring, Batch, SQL, Governance, Automation.'))}<div class="visualGrid">${hbarChart('AOS Affinity Pressure',aosBars,'Sessions + Batch Tasks + blocked Rows je AOS als Priorisierung fuer AOS-Zuordnung.')}${hbarChart('Archiving ROI Candidates',archiveBars,'Groesste Tabellen-/Modifikationssignale, bei denen Archivierung mehr bringen kann als Tuning.')}</div>${listItem('Batch SLA Contract Manager',`Contracts: <b>${esc(s?.batchSlaContractManager?.contractCount||0)}</b>${platformTable((s?.batchSlaContractManager?.contracts||[]).slice(0,8),[['batchGroup','Batch Group'],['targetWindow','Target'],['businessOwner','Owner'],['escalation','Escalation']])}`)}${listItem('Deadlock-to-AX-Process Attribution',`Deadlocks: <b>${esc(s?.deadlockToAxProcessAttribution?.deadlockCount||0)}</b><br>${esc(s?.deadlockToAxProcessAttribution?.nextEvidence||'')}${platformTable((s?.deadlockToAxProcessAttribution?.items||[]),[['deadlockId','Deadlock'],['victim','Victim'],['tables','Tables',x=>esc((x.tables||[]).join(', '))],['confidence','Confidence']])}`)}${listItem('AOS Affinity Advisor',platformTable((s?.aosAffinityAdvisor?.recommendations||[]).slice(0,10),[['aos','AOS'],['sessions','Sessions'],['batchTasks','Batch'],['blockedRows','Blocked'],['recommendation','Recommendation']]))}${listItem('Data Growth / Archiving ROI',platformTable((s?.dataGrowthArchivingRoi?.candidates||[]).slice(0,10),[['table','Table'],['rows','Rows'],['modifications','Mods'],['roi','ROI'],['reason','Reason']]))}${listItem('Change Simulation Queue',platformTable((s?.changeSimulationQueue?.simulations||[]).slice(0,8),[['scenario','Scenario'],['expectedEffect','Expected'],['risk','Risk'],['validation','Validation']]))}${listItem('Evidence SLA',`Score: <b>${esc(s?.evidenceSla?.score)}</b> | Status: <b>${esc(s?.evidenceSla?.status)}</b><br>Required for CAB: ${esc((s?.evidenceSla?.requiredForCab||[]).join(', '))}`)}${listItem('Known-Issue Matcher AX 2012 CU13',platformTable((s?.knownIssueMatcher?.matches||[]).slice(0,12),[['findingId','Finding'],['pattern','Pattern'],['confidence','Confidence'],['nextAction','Next Action']]))}${listItem('D365 Migration Signal Dashboard',`${esc(s?.d365MigrationSignalDashboard?.message||'')}<br><b>Decision:</b> ${esc(s?.d365MigrationSignalDashboard?.decision)} | structural=${esc(s?.d365MigrationSignalDashboard?.structuralSignals)} | tuning=${esc(s?.d365MigrationSignalDashboard?.tuningSignals)}`)}`}
function gapClosureDetails(g){const rows=Object.entries(g||{}).map(([name,item])=>({feature:name,status:item.status||'unknown',next:item.nextStep||item.recommendation||item.dashboardEffect||item.healthcheck||item.executionRule||''}));return `${chartGrid(donutChart('Gap Closure Status',count(rows,x=>x.status),'Status der 10 zuletzt offenen Feature-Luecken.'),hbarChart('Gap Closure Coverage',rows.map(x=>({name:x.feature,value:x.status.includes('active')||x.status.includes('ready')||x.status.includes('present')||x.status==='good'?2:1})),'2 = aktiv/ready, 1 = vorbereitet/needs action.'))}${platformTable(rows,[['feature','Feature'],['status','Status'],['next','Naechster Schritt']])}${Object.entries(g||{}).map(([name,item])=>`<div class="listItem"><h3>${esc(name)} - ${esc(item.status||'unknown')}</h3><p>${Object.entries(item).filter(([k])=>k!=='status').slice(0,8).map(([k,v])=>`<b>${esc(k)}:</b> ${esc(Array.isArray(v)?v.join(', '):typeof v==='object'?JSON.stringify(v):v)}`).join('<br>')}</p></div>`).join('')}`}
function renderAiTabs(){const ai=data.ai||{};document.getElementById('aiChat').innerHTML=listItem(ai.naturalLanguageRootCauseChat?.question||'Frage',esc(ai.naturalLanguageRootCauseChat?.answer||'Keine AI/KI-Antwort vorhanden.'),`<p class="muted">Finding IDs: ${(ai.naturalLanguageRootCauseChat?.supportingFindingIds||[]).map(esc).join(', ')}</p>`);document.getElementById('aiExecutive').innerHTML=listItem('Management Summary',`${esc(ai.executiveNarrative?.summary||'')}<br>${esc(ai.executiveNarrative?.riskMessage||'')}<br><b>Board Ask:</b> ${esc(ai.executiveNarrative?.boardAsk||'')}`);const plan=(ai.remediationPlanner?.weeklyPlan||[]);document.getElementById('aiPlan').innerHTML=plan.map(w=>listItem(`Week ${w.week}: ${w.focus}`,(w.actions||[]).map(a=>`<b>${esc(a.playbook)}</b> (${esc(a.findingCount)}): ${esc(a.firstAction)}`).join('<br>'))).join('')||listItem('Kein Plan','Keine Daten');document.getElementById('aiCoverage').innerHTML=[['Features',ai.metadata?.featureCount||0],['Findings',ai.metadata?.findingCount||0],['Action Groups',ai.noiseReduction?.actionableGroups||0],['Evidence Gaps',(data.platform?.evidenceGapAssistant?.gapCount ?? (ai.evidenceGapDetector||[]).length)]].map(x=>`<div class="mini"><span class="muted">${esc(x[0])}</span><b>${esc(x[1])}</b></div>`).join('');document.getElementById('safeActions').innerHTML=(ai.safeActionClassifier||[]).map(a=>listItem(`${a.classification}: ${a.title}`,`${esc(a.why)}<br><b>Next:</b> ${esc(a.nextStep)}`)).join('')||listItem('Keine Actions','Keine Daten');document.getElementById('gxpValidation').innerHTML=(ai.gxpValidationAssistant||[]).slice(0,12).map(v=>listItem(v.findingId,`<b>Objective:</b> ${esc(v.testObjective)}<br><b>Expected:</b> ${esc(v.expectedResult)}<br><b>Deviation:</b> ${esc(v.deviationHandling)}<br><b>Approval:</b> ${esc(v.approvalPath)}`)).join('')||listItem('Keine Validierung','Keine Daten');const gapRows=data.platform?.evidenceGapAssistant?.gaps||[];document.getElementById('evidenceGaps').innerHTML=[`<div class="metricGrid">${metricCard('Evidence Gaps',data.platform?.evidenceGapAssistant?.gapCount ?? gapRows.length,'missing/partial sources',(data.platform?.evidenceGapAssistant?.gapCount||0)>0?'warn':'good')}${metricCard('Low Confidence',data.platform?.evidenceGapAssistant?.lowConfidenceFindings ?? 0,'findings needing proof','warn')}${metricCard('AI Gap Hints',(ai.evidenceGapDetector||[]).length,'AI detector rows','')}</div>`,gapRows.length?listItem('Collector Roadmap',`Welche Quelle fehlt fuer welches Feature:${platformTable(gapRows,[['status','Status',x=>`<span class="statusDot ${esc(x.status==='ok'?'green':x.status==='partial'?'amber':'red')}"></span>${esc(x.status)}`],['capability','Capability'],['missing','Missing Files',x=>esc((x.missing||[]).join(', '))],['collector','Collector'],['when','When']])}`):(ai.evidenceGapDetector||[]).map(g=>listItem(g.source,`${esc(g.reason)}<br><b>Next:</b> ${esc(g.nextCollection)}`)).join('')||listItem('Keine Evidence Gaps','Alle Pflichtquellen wurden erkannt.')].join('');document.getElementById('ticketDrafts').innerHTML=(ai.ticketAutoDrafting||[]).slice(0,12).map(t=>listItem(`${t.priority}: ${t.title}`,`${esc(t.description)}<br><b>Acceptance:</b> ${esc(t.acceptanceCriteria)}<br><b>Rollback:</b> ${esc(t.rollback)}`)).join('')||listItem('Keine Tickets','Keine Daten');const ce=data.collectorErrors||[];document.getElementById('collectorStatus').innerHTML=[`<div class="metricGrid">${metricCard('Collector Errors',ce.length,'*.error.csv files',ce.length?'bad':'good')}${metricCard('Failed Outputs',ce.filter(e=>e.outputFile).length,'parsed error rows',ce.length?'warn':'good')}${metricCard('Evidence Health',data.evidenceHealth?.score ?? 'n/a','overall score',(data.evidenceHealth?.score||0)>=80?'good':(data.evidenceHealth?.score||0)>=50?'warn':'bad')}</div>`,ce.length?listItem('Collector Fehleranalyse',`Nicht als Roh-CSV, sondern als handlungsorientierte Liste:${platformTable(ce,[['source','Error File'],['outputFile','Output'],['error','Cause',x=>esc(String(x.error||x.message||'').slice(0,220))],['collectedAt','Collected'],['nextStep','Next Step']])}`):listItem('Collector OK','Keine *.error.csv Dateien im Evidence-Ordner gefunden.')].join('');const rp=ai.realizationPack||{};document.getElementById('realizationPack').innerHTML=[listItem('Evidence Trust Score',`Score: <b>${esc(rp.evidenceTrustScore?.score)}</b> / Grade: <b>${esc(rp.evidenceTrustScore?.grade)}</b><br>Missing: ${esc((rp.evidenceTrustScore?.missingSources||[]).join(', '))}`),listItem('Collector Fix Suggestions',`${esc((rp.collectorFixSuggestions||[]).length)} suggestions generated`),listItem('SQL 2016 Support Risk',`${esc(rp.sql2016EndOfSupportRisk?.risk)} risk; date ${esc(rp.sql2016EndOfSupportRisk?.supportRiskDate)}`),listItem('Adapter Readiness',Object.entries(rp.adapterReadiness||{}).map(([k,v])=>`<b>${esc(k)}</b>: ${esc(v.status)}`).join('<br>')),listItem('Closed-loop Governance',`${esc((rp.closedLoopGovernance||[]).length)} finding states prepared`),listItem('Dynamic SLA Contracts',`${esc((rp.dynamicSlaContracts||[]).length)} candidate contracts`) ].join('')}
function renderEvidenceHealth(){const h=data.evidenceHealth||{};document.getElementById('evidenceHealth').innerHTML=[listItem('Collection Context',`Environment: <b>${esc(h.environment)}</b><br>Collected: ${esc(h.collectedAt)}<br>Evidence Health Score: <b>${esc(h.score)}</b><br>Present/Error/Empty: ${esc(h.summary?.present)}/${esc(h.summary?.error)}/${esc(h.summary?.empty)} of ${esc(h.summary?.total)}`),listItem('Source Matrix',`${(h.sources||[]).map(s=>`${esc(s.status)}: <b>${esc(s.label)}</b> (${esc(s.file)}, ${esc(s.importance)}, ${esc(s.bytes)} bytes) ${s.errorFile? ' error='+esc(s.errorFile):''}`).join('<br>')}`),listItem('AX Schema Discovery',`${(h.schemaDiscovery||[]).slice(0,30).map(x=>`${esc(x.discovery_type)}: ${esc(x.table_schema)}.${esc(x.table_name)}`).join('<br>')||'No schema discovery rows.'}`),listItem('AX Source Status',`${(h.sourceStatus||[]).map(x=>`${esc(x.status)}: ${esc(x.source)} -> ${esc(x.file)} (${esc(x.note)})`).join('<br>')||'No source_status.csv present.'}`)].join('')}
function renderEnvironmentCompare(){const c=data.environmentComparison||{};document.getElementById('environmentCompare').innerHTML=[listItem('Compared Environments',`Count: <b>${esc(c.environmentCount)}</b>`),...(c.environments||[]).map(e=>listItem(e.environment,`Findings: <b>${esc(e.findingCount)}</b><br>High/Critical: <b>${esc(e.highCritical)}</b><br>Top playbooks: ${esc((e.topPlaybooks||[]).join(', '))}`))].join('')}
function renderSkillsCatalog(){const s=data.skillCatalog||{};document.getElementById('skillsCatalog').innerHTML=[listItem('Skill Overview',`Skill count: <b>${esc(s.skillCount)}</b><br>Use Primary first, Advanced only when needed.`),...Object.entries(s.groups||{}).map(([group,items])=>listItem(group,`${(items||[]).map(x=>`<b>${esc(x.name)}</b>: ${esc(x.description)}`).join('<br>')||'No skills'}`))].join('')}
function renderBatchCollisions(){const b=data.batchCollisions||{};const max=Math.max(1,...(b.groupCollisions||[]).map(x=>x.totalOverlapSeconds||0));const groupCards=(b.groupCollisions||[]).slice(0,12).map(x=>`<div class="collisionCard"><b>${esc(x.groups)}</b><span class="muted">${esc(x.collisions)} Kollisionen, ${esc(x.totalOverlapSeconds)}s Overlap, max ${esc(x.maxOverlapSeconds)}s</span><div class="collisionBar"><div class="collisionFill" style="width:${Math.max(5,(x.totalOverlapSeconds||0)/max*100)}%"></div></div><p>${(x.examples||[]).slice(0,3).map(esc).join('<br>')}</p></div>`).join('');document.getElementById('batchCollisions').innerHTML=[
listItem('Collision Summary',`Tasks: <b>${esc(b.taskCount)}</b><br>Collisions: <b>${esc(b.collisionCount)}</b><br>Peak concurrency: <b>${esc(b.peakConcurrency)}</b><br>Peak window: ${esc(b.peakWindow)}<br>Live blocked rows: ${esc(b.liveBlockedRows)}`),
listItem('Recommended Actions',`${(b.recommendations||[]).map(esc).join('<br>')||'No recommendations.'}`),
`<div class="collisionCards">${groupCards||listItem('Group Collisions','No group collisions detected.')}</div>`,
listItem('Job Pair Collisions',`${(b.jobCollisions||[]).slice(0,20).map(x=>`${esc(x.window)} | <b>${esc(x.left)}</b> (${esc(x.leftGroup)}) <> <b>${esc(x.right)}</b> (${esc(x.rightGroup)}) overlap=${esc(x.overlapSeconds)}s`).join('<br>')||'No job pair collisions detected.'}`),
listItem('Short Runner Storms',`${(b.shortRunnerStorms||[]).slice(0,12).map(x=>`${esc(x.minute)}: <b>${esc(x.shortTaskCount)}</b> short tasks; groups=${esc((x.groups||[]).join(', '))}<br>${esc((x.examples||[]).join(', '))}`).join('<br><br>')||'No short-runner storm detected.'}`),
listItem('Long Runners',`${(b.longRunners||[]).slice(0,15).map(x=>`${esc(x.window)} | <b>${esc(x.name)}</b> (${esc(x.group)}, ${esc(x.company)}) duration=${esc(x.durationSeconds)}s`).join('<br>')||'No long-running batch tasks in current window.'}`)
].join('')}
function renderAxLiveBlocking(){const b=data.axLiveBlocking||{};document.getElementById('axLiveBlocking').innerHTML=[listItem('Live Blocking Summary',`Rows: <b>${esc(b.sourceRows)}</b><br>Blocked: <b>${esc(b.blockedRows)}</b><br>${esc(b.executiveSummary?.message||'')}`),listItem('Blocking Chain Radar',`${(b.blockingChainRadar||[]).map(x=>`Blocker ${esc(x.blockingSessionId)}: ${esc(x.blockedCount)} blocked, maxWait=${esc(x.maxWaitMs)} ms, tables=${esc((x.tables||[]).join(', '))}<br>${esc(x.nextAction)}`).join('<br><br>')||'No live blocker rows.'}`),listItem('Critical Query Classifier',`${(b.criticalQueryClassifier||[]).slice(0,10).map(x=>`${esc(x.queryClass)} session=${esc(x.sessionId)} blocker=${esc(x.blockingSessionId)} table=${esc(x.table)} module=${esc(x.module)}<br>${esc(x.aiInterpretation)}<br>${esc(x.safeQuestion)}`).join('<br><br>')||'No blocked AX query rows.'}`),listItem('Hot Table Contention',`${(b.hotTableContention||[]).map(x=>`${esc(x.table)} (${esc(x.module)}): ${esc(x.blockedSessions)} blocked sessions`).join('<br>')||'No table contention.'}`),listItem('Worker / AOS Impact',`Users:<br>${(b.workerImpactMap||[]).map(x=>`${esc(x.user)}: ${esc(x.blockedSessions)}`).join('<br>')||'none'}<br><br>Hosts:<br>${(b.aosHostImpact||[]).map(x=>`${esc(x.host)}: ${esc(x.blockedSessions)}`).join('<br>')||'none'}`),listItem('AI/KI Safe Questions',`${(b.safeActionQuestions||[]).map(x=>`${esc(x.mode)}: ${esc(x.question)}<br>${esc(x.why)}`).join('<br><br>')||'No live blocking action questions.'}`),listItem('Validation Plan',`${(b.validationPlan||[]).map(esc).join('<br>')}`),listItem('Evidence Gaps',`${(b.evidenceGaps||[]).map(esc).join('<br>')}`)].join('')}
function qaFinding(){const id=document.getElementById('qaFinding').value;return data.findings.find(f=>f.id===id)||data.topFindings[0]||data.findings[0]}
function qaAnswerFor(f,q){if(!f)return ['Keine Finding ausgewählt','Keine Daten'];const rec=f.recommendation||{}, val=f.validation||{}, risk=f.changeReadiness||{}, ax=f.axContext||{};if(q==='next')return ['Nächster sicherer Schritt',`${esc(rec.summary||'Finding prüfen.')}<br><br><b>Sicherheitsgrenze:</b> Keine PROD-Änderung direkt aus dem Dashboard. Erst Evidence sichern, TEST messen, dann Approval.`];if(q==='test')return ['TEST-Vorgehen',`1. Vergleichbare TEST-Daten und Zeitfenster herstellen.<br>2. Baseline messen: ${esc(val.baselineWindow||'aktuelles Evidence-Fenster')}.<br>3. Maßnahme nur in TEST durchführen.<br>4. Erfolgskriterium: ${esc(val.successMetric||'Vorher/Nachher verbessern ohne Regression')}.<br>5. Ergebnis als Evidence Pack sichern.`];if(q==='risk')return ['Umsetzungsrisiko',`<b>Technical:</b> ${esc(risk.technicalRisk||'medium')}<br><b>AX Compatibility:</b> ${esc(risk.axCompatibilityRisk||'medium')}<br><b>Downtime:</b> ${esc(risk.downtimeRisk||'low')}<br><b>Rollback:</b> ${esc(risk.rollbackComplexity||'medium')}<br><b>Betroffene Module:</b> ${esc(ax.module||'Unknown')}`];if(q==='approval')return ['Approval',`<b>Approval Path:</b> ${esc(risk.approvalPath||'Review')}<br><b>Requires Approval:</b> ${esc(rec.requiresApproval!==false)}<br><b>Owner:</b> ${esc(rec.owner||ax.technicalOwner||'AX Operations')}<br><b>GxP Hinweis:</b> Bei produktionsnaher Änderung Test Evidence, Approval, Rollback und Post-Change-Messung anhängen.`];if(q==='rollback')return ['Rollback',`${esc(val.rollback||'Änderung über Change Control zurücknehmen.')}<br><br>Vor Umsetzung muss klar sein, welche SQL/AX/Batch-Konfiguration geändert wurde und wie der Ausgangszustand wiederhergestellt wird.`];return ['Fehlende Evidence',`Direkte Evidence im Finding: ${(f.evidence||[]).map(e=>esc(e.source+':'+e.metric)).join(', ')||'keine'}<br><br>Globale Gaps: ${(data.ai?.evidenceGapDetector||[]).map(g=>esc(g.source)).join(', ')||'keine'}.`]}
function renderQa(){const f=qaFinding();const q=document.getElementById('qaQuestion').value;const [title,body]=qaAnswerFor(f,q);document.getElementById('qaAnswer').innerHTML=listItem(`${title}: ${f?.id||''}`,`<b>${esc(f?.title||'')}</b><br><br>${body}`)}
function initQa(){const sel=document.getElementById('qaFinding');sel.innerHTML=(data.topFindings||data.findings).slice(0,40).map(f=>`<option value="${esc(f.id)}">${esc(f.severity)} | ${esc(f.id)} | ${esc(f.title).slice(0,100)}</option>`).join('');document.getElementById('qaFinding').addEventListener('input',renderQa);document.getElementById('qaQuestion').addEventListener('input',renderQa);renderQa()}
function renderAdmin(){const plan=data.adminExecution||{};const rows=(plan.actions||[]).slice(0,20).map(a=>listItem(`${a.status}: ${a.findingId}`,`<b>${esc(a.title)}</b><br>Action: ${esc(a.actionType)}<br>Environment: ${esc(a.environment)}<br>Token: <span class="code">${esc(a.confirmationToken)}</span><br>Script: <span class="code">${esc(a.script)}</span><br>Gates: ${Object.entries(a.gates||{}).map(([k,v])=>`${esc(k)}=${esc(v)}`).join(', ')}`)).join('');document.getElementById('adminExecution').innerHTML=[listItem('Policy Mode',`Mode: <b>${esc(plan.mode)}</b><br>Environment: <b>${esc(plan.environment)}</b><br>Actions: ${esc(plan.actionCount)}<br>Executable after gates: ${esc(plan.executableCount)}<br><br>Execution is not performed by the dashboard. Admin reviews the generated script, approval, token, rollback, and validation before any database/tool execution.`),rows].join('')}
function renderEnterprise(){const e=data.enterprise||{};const ts=e.timeSeriesStore||{};const health=Number(ts.healthScore||data.riskScore||0);document.getElementById('enterprisePack').innerHTML=[`<div class="platformHero"><div class="platformBrief"><h3>Enterprise Observability Control</h3><p>Diese Sicht bewertet, ob AXPA als dauerhaftes Observability-Modul betrieben werden kann: Trendstore, Alerting, Estate Inventory, Plan Repository und Push-Payloads.</p></div><div class="metricGrid">${metricCard('Health',health,`run ${ts.runId||''}`,health>=75?'good':health>=50?'warn':'bad')}${metricCard('Findings',ts.findings||data.findings.length,'current run',(ts.findings||0)>100?'warn':'')}${metricCard('Alerts',e.alerts?.alertCount||0,'routes prepared',(e.alerts?.alertCount||0)>0?'warn':'good')}${metricCard('Environments',e.estateInventory?.environmentCount||0,'estate scope','')}${metricCard('Plans',e.planRepository?.entryCount||0,`${e.planRepository?.queryFamilies||0} families`,'')}${metricCard('Regressions',(e.planRepository?.regressionCandidates||[]).length,'plan candidates',(e.planRepository?.regressionCandidates||[]).length?'bad':'good')}</div></div>`,listItem('Time-Series Store',`DB: <span class="code">${esc(ts.db)}</span><br>Run: ${esc(ts.runId)}<br>Findings: ${esc(ts.findings)}<br>Health: ${esc(health)}<br><span class="muted">Falls der Enterprise-Pack-Health leer ist, nutzt die Anzeige den Dashboard Health Score als Fallback.</span>`),listItem('Alerts',`Alerts: <b>${esc(e.alerts?.alertCount)}</b>${platformTable((e.alerts?.alerts||[]).slice(0,10),[['severity','Severity',x=>`<span class="statusDot ${esc(x.severity)}"></span>${esc(x.severity)}`],['title','Title'],['route','Route']])}`),listItem('Estate Inventory',`Environments: ${esc(e.estateInventory?.environmentCount)}${platformTable((e.estateInventory?.environments||[]),[['name','Environment'],['findingCount','Findings'],['highCritical','High/Critical']])}`),listItem('Plan Repository',`Entries: ${esc(e.planRepository?.entryCount)}<br>Query families: ${esc(e.planRepository?.queryFamilies)}<br>Regression candidates: ${esc((e.planRepository?.regressionCandidates||[]).length)}`),listItem('Notification Payloads',`Teams: <span class="code">${esc(e.notifications?.teams)}</span><br>ServiceNow: <span class="code">${esc(e.notifications?.serviceNow)}</span><br>PagerDuty: <span class="code">${esc(e.notifications?.pagerDuty)}</span>`),listItem('Competitive Coverage',`${(e.competitorCoverage?.covered||[]).map(esc).join('<br>')}`)].join('')}
function renderAdvanced(){const a=data.advanced||{};document.getElementById('advancedUsps').innerHTML=[listItem('SLO Burn Rate',`SLOs: ${esc(a.sloBurnRate?.sloCount)}<br>${(a.sloBurnRate?.items||[]).slice(0,8).map(x=>`${esc(x.status)}: ${esc(x.slo)} burn=${esc(x.burnRate)}`).join('<br>')}`),listItem('Maintenance Window Optimizer',`${(a.maintenanceWindowOptimizer?.sequence||[]).map(x=>`${esc(x.window)} ${esc(x.playbook)} (${esc(x.findingCount)})`).join('<br>')}`),listItem('Cost Of Delay',`Daily risk points: <b>${esc(a.costOfDelay?.totalDailyRiskPoints)}</b><br>${(a.costOfDelay?.items||[]).slice(0,6).map(x=>`${esc(x.findingId)}: ${esc(x.dailyRiskPoints)}`).join('<br>')}`),listItem('Release Gate',`Status: <b>${esc(a.releaseGate?.status)}</b><br>Blockers: ${esc(a.releaseGate?.blockerCount)}`),listItem('Retention Candidates',`Candidates: ${esc(a.retentionCandidates?.candidateCount)}<br>${(a.retentionCandidates?.candidates||[]).slice(0,8).map(x=>`${esc(x.table)} (${esc(x.signals)})`).join('<br>')}`),listItem('Known Issue Matches',`Matches: ${esc(a.knownIssueMatches?.matchCount)}<br>${(a.knownIssueMatches?.matches||[]).slice(0,8).map(x=>`${esc(x.knownIssueId)} -> ${esc(x.findingId)}`).join('<br>')}`),listItem('Executive Briefing',`${esc(a.executiveBriefings?.oneMinute)}<br><b>Ask:</b> ${esc(a.executiveBriefings?.decisionAsk)}<br><b>Risk:</b> ${esc(a.executiveBriefings?.riskIfDeferred)}`),listItem('Temporal Hotspot Map',`Peak: <b>${esc(a.temporalHotspotMap?.peakHour)}</b> score=${esc(a.temporalHotspotMap?.peakScore)}<br>${(a.temporalHotspotMap?.timeline||[]).slice(0,10).map(x=>`${esc(x.hour)} batch=${esc(x.batchTasks||0)} blocking=${esc(x.liveBlocking||0)} qs=${esc(x.queryStoreHotspots||0)}`).join('<br>')}`),listItem('Workload Fingerprinting',`Dominant: <b>${esc(a.workloadFingerprinting?.dominantFamily)}</b><br>${(a.workloadFingerprinting?.items||[]).slice(0,8).map(x=>`${esc(x.family)} weight=${esc(x.weight)}`).join('<br>')}`),listItem('Archive Impact Sandbox',`${(a.archiveImpactSandbox?.scenarios||[]).map(x=>`${esc(x.scenario)}: drop=${esc(x.estimatedRiskPointDrop)} (${esc(x.candidateCount)} tables)`).join('<br>')}`),listItem('Performance Budgeting',`Status: <b>${esc(a.performanceBudgeting?.status)}</b><br>${(a.performanceBudgeting?.budgets||[]).map(x=>`${esc(x.status)} ${esc(x.metric)} ${esc(x.current)}/${esc(x.target)}`).join('<br>')}`),listItem('Validation Orchestrator',`Steps: ${esc(a.validationOrchestrator?.stepCount)}<br>${(a.validationOrchestrator?.steps||[]).slice(0,6).map(x=>`${esc(x.findingId)}: ${esc(x.acceptance)}`).join('<br>')}`),listItem('Operator Copilot Context',`Evidence files: ${esc(Object.keys(a.operatorCopilotContext?.evidenceFiles||{}).length)}<br>${(a.operatorCopilotContext?.suggestedQuestions||[]).map(esc).join('<br>')}`),listItem('Self-calibrating Thresholds',`Samples: ${esc(a.selfCalibratingThresholds?.sampleCount)}<br>${(a.selfCalibratingThresholds?.thresholds||[]).map(x=>`${esc(x.metric)} p95=${esc(x.p95)} alert=${esc(x.recommendedAlert)}`).join('<br>')}`)].join('')}
function renderGovernance(){const g=data.governance||{};document.getElementById('governanceExtensions').innerHTML=[listItem('Runbook Automation',`${(g.runbookAutomation||[]).slice(0,5).map(x=>`${esc(x.findingId)}: ${esc(x.playbook)}`).join('<br>')}`),listItem('RACI Matrix',`${(g.raciMatrix||[]).map(x=>`${esc(x.owner)}: ${esc(x.findingCount)} findings, high=${esc(x.highCount)}`).join('<br>')}`),listItem('Business Impact Timeline',`${(g.businessImpactTimeline||[]).map(x=>`${esc(x.window)}: ${esc(x.findingCount)} findings, high=${esc(x.highCount)}`).join('<br>')}`),listItem('Suppression Governance',`${(g.suppressionGovernance||[]).slice(0,8).map(x=>`${esc(x.scope)} (${esc(x.findingCount)}) expiry=${esc(x.expiry)}`).join('<br>')}`),listItem('Data Quality Checks',`Score: <b>${esc(g.dataQualityChecks?.score)}</b><br>Empty files: ${(g.dataQualityChecks?.emptyFiles||[]).map(esc).join(', ')}<br>Collector errors: ${(g.dataQualityChecks?.collectorErrors||[]).map(esc).join(', ')}`),listItem('Audit Export',`CSV: <span class="code">${esc(g.auditExport?.csv)}</span><br>JSON: <span class="code">${esc(g.auditExport?.json)}</span><br>Rows: ${esc(g.auditExport?.rows)}`)].join('')}
function renderStrategy(){const s=data.strategy||{};document.getElementById('strategyExtensions').innerHTML=[listItem('What-if Simulation',`${(s.whatIfSimulation?.scenarios||[]).slice(0,8).map(x=>`${esc(x.scenario)}: ${esc(x.riskReductionPercent)}% reduction estimate`).join('<br>')}`),listItem('Baseline Benchmark',`Health: <b>${esc(s.baselineBenchmark?.healthScore)}</b><br>${esc(s.baselineBenchmark?.benchmarkInterpretation)}`),listItem('Evidence Completeness Roadmap',`${(s.evidenceCompletenessRoadmap?.sources||[]).map(x=>`${esc(x.present?'done':'missing')}: ${esc(x.source)} - ${esc(x.value)}`).join('<br>')}`),listItem('Remediation Kanban',`Now: ${esc((s.remediationKanban?.Now||[]).length)}<br>Next: ${esc((s.remediationKanban?.Next||[]).length)}<br>Later: ${esc((s.remediationKanban?.Later||[]).length)}<br>Waiting Evidence: ${esc((s.remediationKanban?.['Waiting Evidence']||[]).length)}`),listItem('KPI Contracts',`${(s.kpiContracts||[]).slice(0,8).map(x=>`${esc(x.kpi)} current=${esc(x.current)} target=${esc(x.target)}`).join('<br>')}`),listItem('Capability Matrix',`${(s.capabilityMatrix||[]).map(x=>`${esc(x.status)}: ${esc(x.capability)} - ${esc(x.differentiator)}`).join('<br>')}`)].join('')}
function renderAiKi(){const k=data.aiKi||{};document.getElementById('aiKiExtensions').innerHTML=[
listItem('Hypothesis Ranking',`${(k.hypothesisRanking||[]).slice(0,8).map(x=>`${esc(x.hypothesis)} score=${esc(x.score)} confidence=${esc(x.confidence)}`).join('<br>')}`),
listItem('Batch Reschedule Simulator',`Tasks: <b>${esc(k.batchRescheduleSimulator?.taskCount)}</b><br>Collisions: <b>${esc(k.batchRescheduleSimulator?.collisionCount)}</b><br>Peak: <b>${esc(k.batchRescheduleSimulator?.peakConcurrency)}</b> @ ${esc(k.batchRescheduleSimulator?.peakWindow)}<br>${(k.batchRescheduleSimulator?.candidates||[]).slice(0,6).map(x=>`<b>${esc(x.groups)}</b>: ${esc(x.proposal)} (${esc(x.estimatedOverlapReductionPercent)}% potential overlap reduction, risk ${esc(x.risk)})`).join('<br>')}`),
listItem('Root Cause Bridge',`${(k.rootCauseBridge||[]).slice(0,8).map(x=>`<b>${esc(x.hypothesis)}</b><br>${esc((x.supportingEvidence||[]).join(', '))}<br><span class="muted">${esc(x.decidingTest)}</span>`).join('<br><br>')}`),
listItem('Next Best Evidence',`${(k.nextBestEvidence||[]).map(x=>`${esc(x.present?'present':'missing')}: <b>${esc(x.source)}</b> (${esc(x.businessValue)}) - ${esc(x.why)}`).join('<br>')}`),
listItem('Change ROI Prioritizer',`${(k.changeRoiPrioritizer||[]).slice(0,8).map(x=>`<b>${esc(x.score)}</b> ${esc(x.findingId)}: ${esc(x.title)}<br>${esc(x.firstMove)}<br><span class="muted">${esc(x.approval)}</span>`).join('<br><br>')}`),
listItem('Admin Copilot Questions',`${(k.adminCopilotQuestions||[]).slice(0,5).map(x=>`<b>${esc(x.findingId)}</b> ${esc(x.title)}<br>${(x.questions||[]).map(esc).join('<br>')}<br><span class="muted">${esc(x.safeBoundary)}</span>`).join('<br><br>')}`),
listItem('Counterfactuals',`${(k.counterfactuals||[]).slice(0,5).map(x=>`${esc(x.findingId)}: ${esc(x.ifWeValidateInTest)}`).join('<br>')}`),
listItem('Causal Narrative',`${esc(k.causalNarrative?.summary)}<br>${(k.causalNarrative?.chain||[]).map(x=>`${esc(x.cause)} -> ${esc(x.effect)}`).join('<br>')}`),
listItem('LLM Context Pack',`Context findings: ${esc((k.llmContextPack?.contextFindings||[]).length)}<br>Policy: ${esc(k.llmContextPack?.sourcePolicy)}<br><span class="code">${esc((k.llmContextPack?.systemPrompt||'').slice(0,300))}</span>`),
listItem('Evidence Chunks',`Chunks: ${esc((k.evidenceChunks||[]).length)}<br>${(k.evidenceChunks||[]).slice(0,3).map(x=>`${esc(x.id)}: ${esc(x.text).slice(0,180)}`).join('<br>')}`),
listItem('Confidence Calibration',`${Object.entries(k.confidenceCalibration?.summary||{}).map(([a,b])=>`${esc(a)}=${esc(b)}`).join('<br>')}`)
].join('')}
function renderMarket(){const m=data.market||{};document.getElementById('marketDifferentiators').innerHTML=[
listItem('Vendor-neutral Positioning',`${esc(m.vendorNeutralComparison?.positioning)}<br><b>AXPA:</b> ${(m.vendorNeutralComparison?.axpaStrength||[]).map(esc).join(', ')}`),
listItem('Migration Readiness',`Score: <b>${esc(m.migrationReadiness?.readinessScore)}</b><br>Signals: ${esc(m.migrationReadiness?.signalCount)}<br>${esc(m.migrationReadiness?.recommendation)}`),
listItem('Resilience Score',`Score: <b>${esc(m.resilienceScore?.score)}</b><br>High: ${esc(m.resilienceScore?.highFindings)} Debt: ${esc(m.resilienceScore?.debtItems)} Approval: ${esc(m.resilienceScore?.approvalItems)}`),
listItem('Performance Digital Twin',`Nodes: <b>${esc(m.performanceDigitalTwin?.nodeCount)}</b><br>Processes: ${(m.performanceDigitalTwin?.layers?.businessProcesses||[]).slice(0,6).map(x=>`${esc(x.name)}=${esc(x.riskSignals)}`).join(', ')}<br>Hot tables: ${(m.performanceDigitalTwin?.layers?.hotTables||[]).slice(0,6).map(x=>`${esc(x.name)}=${esc(x.riskSignals)}`).join(', ')}`),
listItem('Causal Graph Engine',`Nodes: <b>${esc(m.causalGraphEngine?.nodeCount)}</b><br>Edges: <b>${esc(m.causalGraphEngine?.edgeCount)}</b><br>${(m.causalGraphEngine?.edges||[]).slice(0,8).map(x=>`${esc(x.from)} -> ${esc(x.to)} (${esc(x.type)})`).join('<br>')}`),
listItem('Performance Contract Tests',`Contracts: <b>${esc(m.performanceContractTests?.contractCount)}</b><br>${(m.performanceContractTests?.contracts||[]).slice(0,6).map(x=>`${esc(x.findingId)}: ${esc(x.contract)} target=${esc(x.target)}`).join('<br>')}`),
listItem('Change Blast Radius',`${(m.changeBlastRadius?.changeTypes||[]).slice(0,8).map(x=>`<b>${esc(x.changeType)}</b>: ${esc(x.blastRadius)} modules=${esc((x.modules||[]).join(', '))}`).join('<br>')}`),
listItem('Performance Debt Interest',`Debt items: <b>${esc(m.performanceDebtInterest?.debtItemCount)}</b><br>${(m.performanceDebtInterest?.items||[]).slice(0,8).map(x=>`${esc(x.interest)} ${esc(x.findingId)} ${esc(x.owner)}`).join('<br>')}`),
listItem('Remediation Portfolio Optimizer',`${(m.remediationPortfolioOptimizer?.portfolio||[]).slice(0,8).map(x=>`<b>${esc(x.score)}</b> ${esc(x.findingId)}: ${esc(x.firstMove).slice(0,120)}`).join('<br>')}`),
listItem('AX Aging Risk Index',`Score: <b>${esc(m.axAgingRiskIndex?.score)}</b><br>High=${esc(m.axAgingRiskIndex?.highFindings)} Growth=${esc(m.axAgingRiskIndex?.growthSignals)} Debt=${esc(m.axAgingRiskIndex?.debtSignals)}<br>${esc(m.axAgingRiskIndex?.interpretation)}`),
listItem('Regression Test Skeletons',`Tests: <b>${esc(m.regressionTestSkeletons?.testCount)}</b><br>${(m.regressionTestSkeletons?.tests||[]).slice(0,8).map(x=>`${esc(x.name)} -> ${esc(x.assertion).slice(0,130)}`).join('<br>')}`),
listItem('Knowledge Graph',`Nodes: ${esc(m.knowledgeGraph?.nodeCount)}<br>Edges: ${esc(m.knowledgeGraph?.edgeCount)}`),
listItem('Process Owner Scorecards',`${(m.processOwnerScorecards||[]).slice(0,8).map(x=>`${esc(x.owner)} score=${esc(x.score)} findings=${esc(x.findingCount)} high=${esc(x.highCount)}`).join('<br>')}`),
listItem('Evidence Marketplace',`${(m.evidenceMarketplace||[]).map(x=>`${esc(x.evidence)}: ${esc(x.value)}`).join('<br>')}`),
listItem('Value Realization',`Opportunities: ${esc(m.valueRealization?.opportunityCount)}<br>${(m.valueRealization?.opportunities||[]).slice(0,8).map(x=>`${esc(x.initiative)} (${esc(x.findingCount)})`).join('<br>')}`)
].join('')}
function renderLearning(){const l=data.learning||{};document.getElementById('learningExtensions').innerHTML=[listItem('Recommendation Memory',`Entries: ${esc((l.recommendationMemory?.entries||[]).length)}<br>DB: <span class="code">${esc(l.recommendationMemory?.db)}</span>`),listItem('Similarity Search',`${(l.similaritySearch||[]).slice(0,5).map(x=>`${esc(x.findingId)} similar=${esc((x.similar||[]).length)}`).join('<br>')}`),listItem('Acceptance Simulation',`${Object.entries(l.acceptanceSimulation||{}).map(([k,v])=>`${esc(k)}: items=${esc(v.items)} load=${esc(v.governanceLoad)}`).join('<br>')}`),listItem('Executive Narrative Variants',`${Object.entries(l.executiveNarrativeVariants||{}).map(([k,v])=>`<b>${esc(k)}</b>: ${esc(v)}`).join('<br>')}`),listItem('Anomaly Explanation',`${(l.anomalyExplanation||[]).slice(0,5).map(x=>`${esc(x.findingId)}: ${esc(x.plainExplanation).slice(0,180)}`).join('<br>')}`),listItem('Action Confidence Tuning',`${(l.actionConfidenceTuning||[]).slice(0,8).map(x=>`${esc(x.findingId)} confidence=${esc(x.actionConfidence)}`).join('<br>')}`)].join('')}
function renderAutonomous(){const a=data.autonomous||{};document.getElementById('autonomousIntelligence').innerHTML=[listItem('Evidence Scout',`${(a.evidenceScout?.sources||[]).map(x=>`${esc(x.present?'present':'missing')}: ${esc(x.source)} - ${esc(x.whyItMatters)}`).join('<br>')}`),listItem('Investigation Tree',`${esc(a.investigationTree?.rootQuestion)}<br>${(a.investigationTree?.nodes||[]).slice(0,5).map(x=>`${esc(x.findingId)}: ${esc(x.question)}`).join('<br>')}`),listItem('Root Cause Debate',`${(a.rootCauseDebate||[]).slice(0,6).map(x=>`<b>${esc(x.hypothesis)}</b>: ${esc(x.argumentFor)} / ${esc(x.argumentAgainst)}`).join('<br>')}`),listItem('Recommendation Quality Gate',`Pass: ${esc(a.recommendationQualityGate?.passCount)}<br>Items: ${esc((a.recommendationQualityGate?.items||[]).length)}`),listItem('KPI Storyboard',`${(a.kpiStoryboard?.slides||[]).map(x=>`<b>${esc(x.title)}</b>: ${esc(x.message)}`).join('<br>')}`),listItem('Anonymized Pattern Library',`Patterns: ${esc((a.anonymizedPatternLibrary||[]).length)}<br>${(a.anonymizedPatternLibrary||[]).slice(0,5).map(x=>`${esc(x.patternId)} ${esc(x.playbook)} ${esc(x.module)}`).join('<br>')}`)].join('')}
function renderAutonomousOps(){const o=data.autonomousOps||{};const p=o.evidenceAcquisitionPlanner||{};document.getElementById('autonomousOps').innerHTML=[listItem('AI Investigation Queue',`${(o.investigationQueue||[]).slice(0,8).map(x=>`<b>${esc(x.priority)}</b> ${esc(x.findingId)}: ${esc(x.nextQuestion)}<br>Evidence: ${esc((x.nextEvidence||[]).join(', '))}<br>Decision: ${esc(x.decision)}`).join('<br><br>')}`),listItem('AI Follow-up Questions',`${(o.followUpQuestions||[]).slice(0,5).map(x=>`<b>${esc(x.findingId)}</b><br>${(x.questions||[]).map(q=>`${esc(q.question)} <span class="muted">(${esc(q.actionType)})</span>`).join('<br>')}`).join('<br><br>')}`),listItem('Evidence Acquisition Planner',`Target: <b>${esc(p.target?.server)}</b> / DB: <b>${esc(p.target?.database)}</b><br>Missing: ${esc(p.missingCount)}<br>${(p.tasks||[]).map(t=>`${esc(t.status)}: ${esc(t.label)}<br><span class="code">${esc(t.command)}</span>`).join('<br><br>')}`),listItem('Autonomous Change Drafting',`${(o.changeDrafts||[]).slice(0,6).map(x=>`<b>${esc(x.changeType)}</b> ${esc(x.findingId)} approval=${esc(x.approvalPath)} rollback=${esc(x.risk?.rollback)}`).join('<br>')}`),listItem('Recommendation Readiness Gate',`${(o.readinessGate||[]).slice(0,10).map(x=>`${esc(x.status)}: ${esc(x.findingId)} score=${esc(x.score)}`).join('<br>')}`),listItem('Next Best Actions',`${(o.nextBestActions||[]).map(x=>`<b>${esc(x.action)}</b> ${esc(x.findingId)}<br>${esc(x.whyThisFirst)}`).join('<br><br>')}`),listItem('Operator Decision Memory',`Status: ${esc(o.operatorDecisionMemory?.status)}<br>Model: ${esc(o.operatorDecisionMemory?.memoryModel)}<br>${(o.operatorDecisionMemory?.playbookBacklog||[]).slice(0,8).map(x=>`${esc(x.playbook)}: ${esc(x.openFindings)}`).join('<br>')}`),listItem('AI Executive Risk Briefing',`${esc(o.executiveRiskBriefing?.headline)}<br><b>Ask:</b> ${esc(o.executiveRiskBriefing?.decisionAsk)}<br><b>Non-goal:</b> ${esc(o.executiveRiskBriefing?.nonGoal)}`),listItem('20 Autonomous Ops Features',`Feature count: <b>${esc(o.featureCount)}</b><br>Safe classifier: ${esc((o.safeToAutomateClassifier||[]).length)}<br>Decision trees: ${esc((o.rootCauseDecisionTree||[]).length)}<br>Post-change checklist: ${esc((o.postChangeEvidenceChecklist||[]).join(', '))}`)].join('')}
function renderPlatform(){const p=data.platform||{};const life=p.recommendationLifecycle||{};const trend=p.trendDashboard||{};const incident=p.incidentReplay||{};const plan=p.queryPlanDiff||{};const aos=p.aosTopology||{};const push=p.productivePushReadiness||{};const ai=p.aiDecisionCockpit||{};document.getElementById('platformExtensions').innerHTML=[
platformOverview(p),
listItem('Historisches Trend-Dashboard',`Runs: <b>${esc(trend.runCount||0)}</b><br><b>Interpretation:</b> Health sollte steigen, High Findings und Batch-Kollisionen sollten fallen. Query Store Top-Risiken zeigen, welche Playbooks ueber mehrere Runs dominant bleiben.<br><b>Query Store Top-Risiken:</b><br>${(trend.series?.queryStoreTopRisks||[]).slice(-5).map(x=>`${esc(x.runId)}: ${Object.entries(x.value||{}).map(([k,v])=>`${esc(k)}=${esc(v)}`).join(', ')}`).join('<br>')}`,spark(trend.series?.healthScore,'green','Health Score')+spark(trend.series?.highCount,'red','High Findings')+spark(trend.series?.batchCollisions,'red','Batch Collisions')+spark(trend.series?.peakConcurrency,'','Peak Concurrency')),
listItem('Recommendation Lifecycle',`States: ${Object.entries(life.stateCounts||{}).map(([k,v])=>`${esc(k)}=${esc(v)}`).join(', ')}<br>Statefile: <span class="code">${esc(life.stateFile)}</span>${flow(life.workflow,'in_test')}<br>${(life.items||[]).slice(0,8).map(x=>`<b>${esc(x.state)}</b> ${esc(x.findingId)}: ${esc(x.nextGate)} <span class="muted">audit=${esc(x.auditKey)}</span><br><span class="code">python scripts/manage_recommendation_lifecycle.py --state-file ${esc(life.stateFile)} --finding-id ${esc(x.findingId)} --state accepted --actor USER</span>`).join('<br>')}`),
listItem('Incident Replay als Timeline',`Events: <b>${esc(incident.eventCount)}</b> | Lanes: ${(incident.lanes||[]).map(x=>`${esc(x.name)}=${esc(x.count)}`).join(', ')}${timeline(incident.events)}<br><b>AI Incident Commander:</b><br>${(incident.aiIncidentCommander||[]).map(x=>`${esc(x.step)}. ${esc(x.prove)} -> ${esc(x.then)}`).join('<br>')}`),
listItem('Query Plan Diff / Regression Watch',`Plan rows: ${esc(plan.planRows)} | Query Store rows: ${esc(plan.queryStoreRows)}<br>Planwechsel: ${esc((plan.newPlanSignals||[]).length)} | Historische neue Plaene: ${esc((plan.historicalDiff?.newPlans||[]).length)} | Historische Regressionen: ${esc((plan.historicalDiff?.regressions||[]).length)}<br>Scans: ${esc((plan.newScanSignals||[]).length)} | Lookups: ${esc((plan.newLookupSignals||[]).length)} | Parallelitaet: ${esc((plan.newParallelismSignals||[]).length)} | QS Regression: ${esc((plan.queryStoreRegressions||[]).length)}<br>${(plan.queryStoreRegressions||[]).slice(0,8).map(x=>`Query ${esc(x.queryId)} plan ${esc(x.planId)} duration=${esc(x.avgDurationMs)} reads=${esc(x.avgReads)}`).join('<br>')}`),
listItem('Deadlock Graph Visualizer',`Available: <b>${esc(p.deadlockGraph?.available)}</b> | Deadlocks: ${esc(p.deadlockGraph?.deadlockCount)}<br>${(p.deadlockGraph?.graphs||[]).slice(0,3).map(x=>`<b>${esc(x.id)}</b> victim=${esc(x.victim)} nodes=${esc((x.nodes||[]).length)} edges=${esc((x.edges||[]).length)} resources=${esc((x.resources||[]).length)}${deadlockSvg(x)}<div class="chain">${(x.edges||[]).slice(0,8).map(e=>`<span>${esc(e.from)} ${esc(e.type)} ${esc(e.to)}</span>`).join('')}</div>`).join('<br>')}`),
listItem('AOS Topology Map',`Nodes: <b>${esc(aos.nodeCount)}</b> | Edges: ${esc((aos.edges||[]).length)}${topologySvg(aos)}${nodeGrid(aos.nodes)}`),
listItem('Scheduler Hardening',`Manifest status: <b>${esc(p.schedulerHardening?.manifestStatus)}</b><br>Lockfile: <span class="code">${esc(p.schedulerHardening?.lockFile)}</span><br>${Object.entries(p.schedulerHardening?.checks||{}).map(([k,v])=>`${esc(k)}=${esc(v.status)} - ${esc(v.recommendation)}`).join('<br>')}`),
listItem('Productive Push Integrations',`Mode: <b>${esc(push.mode)}</b><br>${Object.entries(push).filter(([k])=>k!=='mode').map(([k,v])=>`<b>${esc(k)}</b>: ${esc(v.status)} records=${esc(v.records)} missing=${esc((v.missing||[]).join(', '))} dedupe=${esc((v.dedupeKeys||[])[0]||'')}`).join('<br>')}`),
listItem('X++ Attribution / Query-to-X++ Mapper',`Trace rows: <b>${esc(p.xppAttribution?.traceRows)}</b> | Model rows: <b>${esc(p.xppAttribution?.modelRows)}</b><br>Inputs: ${esc((p.xppAttribution?.mapperInputs||[]).join(', '))}<br>${(p.xppAttribution?.mappings||[]).slice(0,8).map(x=>`${esc(x.findingId)} ${esc(x.queryHash)} confidence=${esc(x.confidence)} trace=${esc(x.traceCandidateCount)} model=${esc(x.modelCandidateCount)} process=${esc(x.businessProcess)} next=${esc(x.nextEvidence)}`).join('<br>')}`),
listItem('Test-vs-Prod Drift Guard',`${Object.entries(p.environmentDriftGuard?.dimensions||{}).map(([k,v])=>`<b>${esc(k)}</b>: rows=${esc(v.rows)} compare=${esc(v.compare)}`).join('<br>')}<br><br><b>Deep comparisons:</b><br>${(p.environmentDriftGuard?.comparisons||[]).slice(0,4).map(c=>`<b>${esc(c.environment)}</b>: ${Object.entries(c.dimensions||{}).map(([k,v])=>`${esc(k)} ${esc(v.risk)} +${esc(v.onlyHere)}/-${esc(v.onlyThere)}`).join(' | ')}`).join('<br>')}<br><br>${esc(p.environmentDriftGuard?.recommendation)}`),
listItem('AI/KI USP Cockpit',`<b>CIO:</b> ${esc(ai.cioAsk)}<br><b>CAB:</b> ${esc(ai.cabAsk)}<br><b>Risk:</b> ${esc(ai.riskIfDeferred)}<br><br><b>AI Batch Twin:</b><br>${(ai.batchTwin||[]).slice(0,5).map(x=>`${esc(x.groups||x.scenario)} overlap=${esc(x.currentOverlapSeconds||'')} reduction=${esc(x.expectedOverlapReductionPercent)}%`).join('<br>')}<br><br><b>Confidence Ladder:</b><br>${(ai.confidenceLadder||[]).slice(0,6).map(x=>`${esc(x.findingId)} ${esc(x.confidence)}: ${esc(x.nextProof)}`).join('<br>')}<br><br><b>Evidence Quality Coach:</b><br>${(ai.evidenceQualityCoach||[]).map(x=>`${esc(x.present?'present':'missing')}: ${esc(x.collector)} - ${esc(x.when)}`).join('<br>')}<br><br><b>Modernization Signal:</b> ${esc(ai.modernizationSignal?.message)}<br><b>Process Owner Briefings:</b><br>${(ai.processOwnerBriefings||[]).slice(0,8).map(x=>esc(x.brief)).join('<br>')}`),
listItem('Live Batch Collision Watch',`Mode: ${esc(p.liveBatchCollisionWatch?.mode)}<br>Collisions: <b>${esc(p.liveBatchCollisionWatch?.collisionCount)}</b> | Peak concurrency: ${esc(p.liveBatchCollisionWatch?.peakConcurrency)} | Peak: ${esc(p.liveBatchCollisionWatch?.peakWindow)}${platformTable((p.liveBatchCollisionWatch?.alerts||[]).slice(0,10),[['severity','Severity',x=>`<span class="statusDot ${esc(x.severity)}"></span>${esc(x.severity)}`],['groups','Batch Groups'],['collisions','Count'],['totalOverlapSeconds','Overlap s'],['nextCheck','Next Check']])}`),
listItem('Batch Reschedule Calendar',batchRescheduleDetails(p.batchRescheduleCalendar)),
listItem('AX Batch Dependency Graph',batchDependencyDetails(p.batchDependencyGraph)),
listItem('SQL Blocking Chain Recorder',`Samples: <b>${esc(p.sqlBlockingChainRecorder?.sampleCount)}</b> | Chains: ${esc(p.sqlBlockingChainRecorder?.chainCount)}${platformTable((p.sqlBlockingChainRecorder?.chains||[]).slice(0,8),[['rootBlocker','Root Blocker'],['victimCount','Victims'],['totalWaitMs','Total Wait ms'],['rootKnown','Root Known'],['victims','Victim Sessions',x=>esc((x.victims||[]).slice(0,8).join(', '))]])}`),
listItem('AX Business Process SLA',`Processes: <b>${esc(p.axBusinessProcessSla?.processCount)}</b>${platformTable((p.axBusinessProcessSla?.items||[]).slice(0,12),[['status','SLA',x=>`<span class="statusDot ${esc(x.status)}"></span>${esc(x.status)}`],['process','Process'],['high','High'],['riskPoints','Risk'],['topPlaybooks','Dominant Risk']])}`),
listItem('Evidence Gap Assistant',`Gaps: <b>${esc(p.evidenceGapAssistant?.gapCount)}</b> | Low-confidence findings: ${esc(p.evidenceGapAssistant?.lowConfidenceFindings)}${platformTable((p.evidenceGapAssistant?.gaps||[]),[['status','Status',x=>`<span class="statusDot ${esc(x.status==='ok'?'green':x.status==='partial'?'amber':'red')}"></span>${esc(x.status)}`],['capability','Capability'],['missing','Missing Files',x=>esc((x.missing||[]).join(', '))],['collector','Collector'],['when','When']])}`),
listItem('Deployment Regression Guard',`Status: <b>${esc(p.deploymentRegressionGuard?.status)}</b> | QS rows: ${esc(p.deploymentRegressionGuard?.queryStoreRows)} | New plans: ${esc(p.deploymentRegressionGuard?.newPlanCount)} | Regressions: ${esc(p.deploymentRegressionGuard?.regressionCount)}${platformTable((p.deploymentRegressionGuard?.topRuntimeQueries||[]).slice(0,10),[['queryId','Query'],['planId','Plan'],['avgDurationMs','Avg Duration ms'],['avgReads','Avg Reads']])}`),
listItem('Admin Remediation Workbench',`Actions: <b>${esc(p.adminRemediationWorkbench?.actionCount)}</b><br>${(p.adminRemediationWorkbench?.actions||[]).slice(0,8).map(x=>`${esc(x.findingId)} ${esc(x.scriptType)} ${esc(x.allowedAction)}`).join('<br>')}`),
listItem('Alerting Rules',`Rules: <b>${esc(p.alertingRules?.ruleCount)}</b> | Enabled: ${esc(p.alertingRules?.enabledCount)} | High-risk signals: ${esc(p.alertingRules?.currentHighRiskSignals)}<br>${(p.alertingRules?.rules||[]).map(x=>`${esc(x.enabled?'on':'off')} ${esc(x.rule)} -> ${esc(x.target)} (${esc(x.condition)})`).join('<br>')}`),
listItem('AI Safe Feature Bundle',`Incident chain: ${esc(p.aiSafeFeatures?.incidentCommander?.eventChainLength)} | Batch twin scenarios: ${esc(p.aiSafeFeatures?.batchTwin?.scenarioCount)} | CAB briefs: ${esc(p.aiSafeFeatures?.changeBoardBrief?.briefCount)}<br><b>First proof:</b> ${esc(p.aiSafeFeatures?.incidentCommander?.firstProof)}<br><b>Top safe plan:</b><br>${(p.aiSafeFeatures?.safeRemediationPlanner?.items||[]).slice(0,6).map(x=>`${esc(x.findingId)} score=${esc(x.priorityScore)} lane=${esc(x.recommendedLane)}`).join('<br>')}`),
listItem('Strategic USP Pack',strategicUspDetails(p.strategicUspPack)),
listItem('Gap Closure - letzte 10 reale Features',gapClosureDetails(p.gapClosure))
].join('')}
function enhanceTabSummaries(){const ai=data.ai||{};const safe=ai.safeActionClassifier||[];if(document.getElementById('safeActions'))document.getElementById('safeActions').insertAdjacentHTML('afterbegin',`<div class="metricGrid">${metricCard('Safe Action Summary',safe.length,'classified recommendations','')}${metricCard('CAB Required',safe.filter(x=>String(x.classification||'').toLowerCase().includes('cab')).length,'approval path','warn')}${metricCard('Preview Boundary',safe.filter(x=>String(x.nextStep||'').toLowerCase().includes('review')).length,'manual review','good')}</div>`);const gxp=ai.gxpValidationAssistant||[];if(document.getElementById('gxpValidation'))document.getElementById('gxpValidation').insertAdjacentHTML('afterbegin',`<div class="metricGrid">${metricCard('GxP Validation Summary',gxp.length,'test packages','')}${metricCard('CAB Approval',gxp.filter(x=>String(x.approvalPath||'').includes('CAB')).length,'approval path','warn')}${metricCard('Deviation Handling',gxp.filter(x=>x.deviationHandling).length,'documented','good')}</div>`);const rp=ai.realizationPack||{};if(document.getElementById('realizationPack'))document.getElementById('realizationPack').insertAdjacentHTML('afterbegin',`<div class="metricGrid">${metricCard('Realization Summary',rp.evidenceTrustScore?.score??'n/a',`grade ${rp.evidenceTrustScore?.grade||''}`,(rp.evidenceTrustScore?.score||0)>=80?'good':'warn')}${metricCard('Collector Fixes',(rp.collectorFixSuggestions||[]).length,'suggestions','warn')}${metricCard('SLA Contracts',(rp.dynamicSlaContracts||[]).length,'candidate contracts','')}</div>`);const cmp=data.environmentComparison||{};if(document.getElementById('environmentCompare'))document.getElementById('environmentCompare').insertAdjacentHTML('afterbegin',`<div class="metricGrid">${metricCard('Environment Compare Summary',cmp.environmentCount||0,'compared snapshots','')}${metricCard('Highest Risk',(cmp.environments||[]).reduce((m,x)=>Math.max(m,Number(x.highCritical||0)),0),'high/critical max','warn')}${metricCard('Current Findings',data.findings.length,'active dashboard','')}</div>`);if(document.getElementById('qaAnswer'))document.getElementById('qaAnswer').insertAdjacentHTML('afterbegin',`<div class="metricGrid">${metricCard('Implementation Q&A Summary',(data.topFindings||[]).length,'selectable findings','')}${metricCard('Top Severity',(data.topFindings?.[0]?.severity||'n/a'),'first recommendation','warn')}${metricCard('Questions',document.getElementById('qaQuestion')?.options?.length||0,'guided prompts','')}</div>`);const admin=data.adminExecution||{};if(document.getElementById('adminExecution'))document.getElementById('adminExecution').insertAdjacentHTML('afterbegin',`<div class="metricGrid">${metricCard('Admin Execution Summary',admin.actionCount||0,'preview actions','warn')}${metricCard('Executable',admin.executableCount||0,'after gates','good')}${metricCard('Policy',admin.mode||'preview-only','no dashboard execution','good')}</div>`);const auto=data.autonomous||{};if(document.getElementById('autonomousIntelligence'))document.getElementById('autonomousIntelligence').insertAdjacentHTML('afterbegin',`<div class="metricGrid">${metricCard('Autonomous AI Summary',(auto.evidenceScout?.sources||[]).length,'evidence scouts','')}${metricCard('Missing Evidence',(auto.evidenceScout?.sources||[]).filter(x=>!x.present).length,'collector needs','warn')}${metricCard('Quality Gate',auto.recommendationQualityGate?.passCount||0,'passed recommendations','good')}</div>`)}
function addVisualCharts(){const ai=data.ai||{},p=data.platform||{},b=data.batchCollisions||{},live=data.axLiveBlocking||{};const add=(id,html)=>{const el=document.getElementById(id);if(el&&html)el.insertAdjacentHTML('afterbegin',html)};add('aiChat',chartGrid(hbarChart('AI Risk Inputs',[{name:'Findings',value:data.findings?.length||0},{name:'High/Critical',value:(data.findings||[]).filter(f=>['critical','high'].includes(f.severity)).length},{name:'Action Groups',value:ai.noiseReduction?.actionableGroups||0},{name:'Evidence Gaps',value:p.evidenceGapAssistant?.gapCount ?? (ai.evidenceGapDetector||[]).length},{name:'Tickets',value:(ai.ticketAutoDrafting||[]).length}],'Die wichtigsten KI-Eingangssignale als komprimierte Sicht.'),donutChart('AI Coverage',[{name:'safe actions',value:(ai.safeActionClassifier||[]).length},{name:'gxp tests',value:(ai.gxpValidationAssistant||[]).length},{name:'tickets',value:(ai.ticketAutoDrafting||[]).length},{name:'evidence hints',value:(ai.evidenceGapDetector||[]).length}],'Welche KI-Bausteine im aktuellen Run Daten liefern.')));add('safeActions',chartGrid(donutChart('Action-Klassen',count(ai.safeActionClassifier||[],x=>x.classification||'unknown'),'Wie viele Empfehlungen sofort, CAB-pflichtig oder nur pruefbar sind.'),hbarChart('Naechste Umsetzungsschritte',count(ai.safeActionClassifier||[],x=>x.nextStep||'missing'),'Verdichtet die operativen To-dos statt langer Textkarten.')));add('gxpValidation',chartGrid(donutChart('Approval-Pfade',count(ai.gxpValidationAssistant||[],x=>x.approvalPath||'unknown'),'GxP-/CAB-Last nach Freigabepfad.'),hbarChart('Deviation Handling',count(ai.gxpValidationAssistant||[],x=>x.deviationHandling||'missing'),'Wo Nachweis- oder Abweichungsarbeit entsteht.')));add('evidenceGaps',chartGrid(donutChart('Evidence Status',count(p.evidenceGapAssistant?.gaps||[],x=>x.status||'unknown'),'Fehlende, partielle und vorhandene Quellen.'),hbarChart('Collector Prioritaet',count(p.evidenceGapAssistant?.gaps||[],x=>x.collector||'unknown'),'Welche Collector zuerst nachziehen.')));add('collectorStatus',chartGrid(donutChart('Collector Health',[{name:'errors',value:(data.collectorErrors||[]).length},{name:'ok sources',value:Math.max(0,Number(data.evidenceHealth?.summary?.present||0))},{name:'empty',value:Number(data.evidenceHealth?.summary?.empty||0)}],'Technischer Zustand der Evidence-Dateien.'),hbarChart('Fehlerursachen',count(data.collectorErrors||[],x=>String(x.error||x.message||'unknown').slice(0,48)),'Gruppierte Ursachen statt Rohfehler.')));add('environmentCompare',chartGrid(hbarChart('High/Critical je Umgebung',(data.environmentComparison?.environments||[]).map(x=>({name:x.environment,value:x.highCritical||0})),'Drift-Risiko sofort sichtbar.'),hbarChart('Findings je Umgebung',(data.environmentComparison?.environments||[]).map(x=>({name:x.environment,value:x.findingCount||0})),'Volumenvergleich der analysierten Snapshots.')));add('batchCollisions',chartGrid(hbarChart('Batch-Kollisionen nach Gruppe',topFromObjects(b.groupCollisions||[],['groups','group'],['collisions','collisionCount','totalOverlapSeconds']),'Priorisiert die schwersten Overlap-Gruppen.'),heatmapChart('Peak-Fenster / Stunden',(b.hourlyConcurrency||b.hourly||b.groupCollisions||[]).map((x,i)=>({name:x.hour??x.currentHour??String(i+1),value:x.peakConcurrency??x.taskCount??x.collisions??0})),'Heatmap fuer Zeitfenster mit Lastspitzen.')));add('axLiveBlocking',chartGrid(hbarChart('Blocking Chains',topFromObjects(live.blockingChains||live.chains||[],['rootBlocker','blockingSessionId','sessionId'],['victimCount','blockedCount','totalWaitMs']),'Blocker mit meisten Opfern oder Wartezeit.'),hbarChart('Hot Tables',count(data.findings||[],x=>(x.axContext?.tables||[])[0]||'Unknown'),'Tabellen, die in Findings am haeufigsten auftauchen.')));add('enterprisePack',chartGrid(donutChart('Enterprise Alerts',[{name:'enabled',value:p.alertingRules?.enabledCount||0},{name:'disabled',value:Math.max(0,(p.alertingRules?.ruleCount||0)-(p.alertingRules?.enabledCount||0))},{name:'high-risk signals',value:p.alertingRules?.currentHighRiskSignals||0}],'Alerting-Reifegrad.'),hbarChart('Business SLA Risiken',topFromObjects(p.axBusinessProcessSla?.items||[],['process'],['riskPoints','high']),'Fachprozesse mit hoechstem Risiko.')));add('advancedUsps',chartGrid(hbarChart('Regression Guard',topFromObjects(p.deploymentRegressionGuard?.topRuntimeQueries||[],['queryId'],['avgDurationMs','avgReads']),'Query Store Hotspots nach Laufzeit/Reads.'),hbarChart('Plan Diff Signale',[{name:'new plans',value:p.queryPlanDiff?.newPlanSignals?.length||0},{name:'scans',value:p.queryPlanDiff?.newScanSignals?.length||0},{name:'lookups',value:p.queryPlanDiff?.newLookupSignals?.length||0},{name:'parallelism',value:p.queryPlanDiff?.newParallelismSignals?.length||0},{name:'QS regressions',value:p.queryPlanDiff?.queryStoreRegressions?.length||0}],'Planwechsel werden als Signalgruppen sichtbar.')));add('governanceExtensions',chartGrid(donutChart('Lifecycle States',Object.entries(p.recommendationLifecycle?.stateCounts||{}).map(([name,value])=>({name,value})),'Status der Empfehlungen.'),hbarChart('Readiness Gate',topFromObjects(data.autonomousOps?.readinessGate||[],['status','findingId'],['score']),'Welche Findings umsetzungsreif sind.')));add('strategyExtensions',chartGrid(hbarChart('Modernization Signale',count(ai.processOwnerBriefings||[],x=>String(x.owner||x.process||x.brief||'unknown').split(':')[0]),'Fachliche Risiko-Verteilung.'),hbarChart('Safe Remediation Nutzen',topFromObjects(p.aiSafeFeatures?.safeRemediationPlanner?.items||[],['findingId','recommendedLane'],['priorityScore']),'Nutzen/Risiko-Priorisierung fuer Massnahmen.')));add('aiKiExtensions',chartGrid(hbarChart('Confidence Ladder',topFromObjects(p.aiDecisionCockpit?.confidenceLadder||[],['findingId','confidence'],['score','confidenceScore']),'Beweisreife je Root-Cause-Hypothese.'),hbarChart('AI Batch Twin',topFromObjects(p.aiDecisionCockpit?.batchTwin||[],['groups','scenario'],['expectedOverlapReductionPercent','currentOverlapSeconds']),'Simulierter Overlap-Abbau.')));add('marketDifferentiators',chartGrid(hbarChart('AX Module Risiken',data.modules||[],'AX-spezifischer Vorsprung gegen generische DB-Tools.'),hbarChart('Playbook-Fokus',data.playbooks||[],'Wo das Advisor-Wissen am meisten greift.')));add('learningExtensions',chartGrid(hbarChart('Similarity Search',topFromObjects(data.learning?.similaritySearch||[],['findingId'],['similarCount']).map(x=>x.value?x:{...x,value:1}),'Wiedererkennbare Muster fuer kuenftige Runs.'),donutChart('Acceptance Simulation',Object.entries(data.learning?.acceptanceSimulation||{}).map(([name,v])=>({name,value:v.items||0})),'Governance-Last nach Annahmeszenario.')));add('autonomousIntelligence',chartGrid(donutChart('Evidence Scout',(data.autonomous?.evidenceScout?.sources||[]).reduce((a,x)=>{const k=x.present?'present':'missing';const r=a.find(y=>y.name===k);if(r)r.value++;else a.push({name:k,value:1});return a},[]),'KI zeigt, welche Beweise noch fehlen.'),hbarChart('Pattern Library',count(data.autonomous?.anonymizedPatternLibrary||[],x=>x.playbook||'unknown'),'Wiederverwendbare Root-Cause-Muster.')));add('autonomousOps',chartGrid(hbarChart('Investigation Queue',topFromObjects(data.autonomousOps?.investigationQueue||[],['findingId','priority'],['score','riskScore']).map(x=>x.value?x:{...x,value:1}),'Naechste Fragen nach Prioritaet.'),hbarChart('Next Best Actions',count(data.autonomousOps?.nextBestActions||[],x=>x.action||'unknown'),'Operative KI-Aktionsgruppen.')));add('platformExtensions',chartGrid(hbarChart('Platform Top Risiken',[{name:'Batch Alerts',value:p.liveBatchCollisionWatch?.alerts?.length||0},{name:'Blocking Chains',value:p.sqlBlockingChainRecorder?.chainCount||0},{name:'Evidence Gaps',value:p.evidenceGapAssistant?.gapCount||0},{name:'Regressions',value:p.deploymentRegressionGuard?.regressionCount||0},{name:'Lifecycle Open',value:(p.recommendationLifecycle?.items||[]).length||0}],'Kompakte Executive-Grafik fuer den Platform Tab.'),heatmapChart('Batch Reschedule Calendar',topFromObjects(p.batchRescheduleCalendar?.proposals||[],['currentHour'],['taskCount','expectedOverlapReductionPercent']).map(x=>({name:String(x.name),value:x.value})),'Stunden mit Verschiebebedarf.')))}
function enhanceCollectorCoverage(){const el=document.getElementById('collectorStatus');const rows=data.evidenceHealth?.sourceStatus||[];if(!el||!rows.length)return;el.insertAdjacentHTML('afterbegin',listItem('Collector Source Coverage',`AX-Quellen aus source_status.csv:<br>${rows.map(x=>`<b>${esc(x.source)}</b>: ${esc(x.status)} -> ${esc(x.file)} <span class="muted">${esc(x.note||'')}</span>`).join('<br>')}`))}
function initTabs(){document.querySelectorAll('.tabBtn').forEach(btn=>btn.addEventListener('click',()=>{document.querySelectorAll('.tabBtn').forEach(b=>b.classList.remove('active'));document.querySelectorAll('.tabPanel').forEach(p=>p.classList.remove('active'));btn.classList.add('active');document.getElementById('tab-'+btn.dataset.tab).classList.add('active')}))}
function init(){const score=data.riskScore||0;document.getElementById('score').textContent=score;const ring=document.getElementById('scoreRing');ring.style.setProperty('--pct',score);ring.style.setProperty('--color',score>=75?'var(--green)':score>=50?'var(--amber)':'var(--red)');document.getElementById('environmentChip').textContent='Environment: '+esc(data.environment||'Unknown');document.getElementById('generated').textContent='Generated: '+new Date().toLocaleString();renderKpis();renderOpsRadar();severityDonut();bars('causes',data.rootCauseBars||[],'#2563eb');bars('modules',data.modules,'#0891b2');bars('playbooks',data.playbooks,'#6d28d9');fillSelect('module',data.modules);fillSelect('playbook',data.playbooks);renderTop();renderAiTabs();renderEvidenceHealth();renderEnvironmentCompare();renderSkillsCatalog();renderBatchCollisions();renderAxLiveBlocking();initQa();renderAdmin();renderEnterprise();renderAdvanced();renderGovernance();renderStrategy();renderAiKi();renderMarket();renderLearning();renderAutonomous();renderAutonomousOps();renderPlatform();enhanceTabSummaries();addVisualCharts();enhanceCollectorCoverage();initTabs();['q','sev','module','playbook'].forEach(id=>document.getElementById(id).addEventListener('input',renderRows));renderRows()}
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
