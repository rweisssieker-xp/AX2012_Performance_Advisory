from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sqlite3
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from axpa_core import analyze_evidence, batch_collision_summary, load_evidence, parse_ax_datetime, summarize_root_causes, write_json


SEV = {"critical": 5, "high": 4, "medium": 3, "low": 2, "informational": 1}


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _top(findings: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    return sorted(findings, key=lambda f: (SEV.get(f.get("severity"), 1), len(f.get("evidence", []))), reverse=True)[:limit]


def _num(value: Any, default: float = 0) -> float:
    try:
        if value in (None, ""):
            return default
        if isinstance(value, str):
            text = value.strip()
            if "," in text and "." in text:
                text = text.replace(".", "").replace(",", ".")
            elif "," in text:
                text = text.replace(",", ".")
            return float(text)
        return float(value)
    except (TypeError, ValueError):
        return default


def _hash_payload(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def trend_dashboard(evidence: str | Path, trend_db: str | Path | None) -> dict[str, Any]:
    if not trend_db or not Path(trend_db).exists():
        return {"available": False, "reason": "Trend store not found.", "runs": [], "series": {}}
    with sqlite3.connect(trend_db) as conn:
        conn.row_factory = sqlite3.Row
        runs = [dict(r) for r in conn.execute("SELECT * FROM runs ORDER BY rowid DESC LIMIT 30").fetchall()]
        batch = []
        try:
            batch = [dict(r) for r in conn.execute("SELECT * FROM batch_run_metrics ORDER BY rowid DESC LIMIT 30").fetchall()]
        except sqlite3.OperationalError:
            batch = []
        top_risks = []
        try:
            top_risks = [dict(r) for r in conn.execute("SELECT run_id, severity, playbook, count FROM finding_groups ORDER BY rowid DESC LIMIT 120").fetchall()]
        except sqlite3.OperationalError:
            top_risks = []
    run_series = list(reversed(runs))
    batch_by_run = {r.get("run_id"): r for r in batch}
    risk_by_run: dict[str, Counter] = defaultdict(Counter)
    for row in top_risks:
        key = row.get("playbook") or row.get("severity") or "unknown"
        risk_by_run[str(row.get("run_id"))][str(key)] += int(_num(row.get("count")))
    return {
        "available": True,
        "runCount": len(runs),
        "runs": runs,
        "scorecards": [
            {
                "runId": r.get("run_id"),
                "startedAt": r.get("started_at") or r.get("created_at"),
                "healthScore": r.get("health_score") or max(0, 100 - int(_num(r.get("high_count"))) * 2 - int(_num(r.get("finding_count"))) // 10),
                "findings": r.get("finding_count"),
                "highFindings": r.get("high_count"),
                "batchCollisions": batch_by_run.get(r.get("run_id"), {}).get("collision_count", 0),
                "peakConcurrency": batch_by_run.get(r.get("run_id"), {}).get("peak_concurrency", 0),
                "topQueryStoreRisk": risk_by_run.get(str(r.get("run_id")), Counter()).most_common(1)[0][0] if risk_by_run.get(str(r.get("run_id"))) else "unknown",
            }
            for r in run_series
        ],
        "series": {
            "healthScore": [{"runId": r.get("run_id"), "value": r.get("health_score") or max(0, 100 - int(_num(r.get("high_count"))) * 2 - int(_num(r.get("finding_count"))) // 10)} for r in run_series],
            "findingCount": [{"runId": r.get("run_id"), "value": r.get("finding_count")} for r in run_series],
            "highCount": [{"runId": r.get("run_id"), "value": r.get("high_count")} for r in run_series],
            "batchCollisions": [{"runId": r.get("run_id"), "value": r.get("collision_count")} for r in reversed(batch)],
            "peakConcurrency": [{"runId": r.get("run_id"), "value": r.get("peak_concurrency")} for r in reversed(batch)],
            "queryStoreTopRisks": [{"runId": run, "value": dict(counter.most_common(5))} for run, counter in risk_by_run.items()],
        },
    }


def recommendation_lifecycle(findings: list[dict[str, Any]], state_file: str | Path | None = None) -> dict[str, Any]:
    persisted = {}
    state_path = Path(state_file) if state_file else None
    if state_path and state_path.exists():
        try:
            persisted = json.loads(state_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            persisted = {}
    states = []
    for f in findings:
        sev = f.get("severity")
        confidence = f.get("confidence")
        saved = (persisted.get("items") or {}).get(f["id"], {}) if isinstance(persisted.get("items"), dict) else {}
        if saved.get("state"):
            state = saved["state"]
            next_gate = saved.get("nextGate", "Continue stored lifecycle.")
        elif sev in {"critical", "high"} and confidence == "high":
            state = "ready_for_test"
            next_gate = "Assign owner, create TEST validation task, prepare CAB evidence."
        elif sev in {"critical", "high"}:
            state = "needs_evidence"
            next_gate = "Collect missing evidence before TEST or CAB."
        elif f.get("recommendation", {}).get("requiresApproval"):
            state = "proposed"
            next_gate = "Operations review."
        else:
            state = "monitor"
            next_gate = "Track next run."
        states.append(
            {
                "findingId": f["id"],
                "title": f["title"],
                "state": state,
                "owner": f.get("axContext", {}).get("technicalOwner", "AX Operations"),
                "businessOwner": f.get("axContext", {}).get("businessOwner", "Unknown"),
                "approvalPath": f.get("changeReadiness", {}).get("approvalPath", "Review"),
                "nextGate": next_gate,
                "successMetric": f.get("validation", {}).get("successMetric", ""),
                "rollback": f.get("validation", {}).get("rollback", ""),
                "acceptedBy": saved.get("acceptedBy", ""),
                "implementedAt": saved.get("implementedAt", ""),
                "verifiedAt": saved.get("verifiedAt", ""),
                "auditKey": _hash_payload({"id": f["id"], "title": f["title"], "evidence": f.get("evidence", [])}),
            }
        )
    counts = Counter(item["state"] for item in states)
    workflow = ["proposed", "accepted", "needs_evidence", "in_test", "ready_for_test", "approved", "implemented", "verified", "deferred", "rejected"]
    transitions = {
        "proposed": ["accepted", "deferred", "rejected"],
        "accepted": ["needs_evidence", "in_test", "approved"],
        "needs_evidence": ["in_test", "deferred"],
        "in_test": ["approved", "rejected"],
        "ready_for_test": ["in_test", "deferred"],
        "approved": ["implemented", "deferred"],
        "implemented": ["verified", "rejected"],
        "verified": [],
        "deferred": ["accepted", "rejected"],
        "rejected": [],
    }
    return {"stateCounts": dict(counts), "items": states[:250], "workflow": workflow, "transitions": transitions, "stateFile": str(state_path) if state_path else ""}


def incident_replay_timeline(evidence: str | Path, findings: list[dict[str, Any]]) -> dict[str, Any]:
    root = Path(evidence)
    events = []
    metadata = {}
    if (root / "metadata.json").exists():
        try:
            metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            metadata = {}
    if metadata:
        events.append({"time": metadata.get("pipelineUpdatedAt") or metadata.get("collectedAt") or "", "type": "collector", "severity": "info", "title": "Collector snapshot", "detail": f"{metadata.get('sqlServer') or metadata.get('server')} / {metadata.get('axDatabase') or metadata.get('database')}"})
    waits = _read_csv(root / "sql_wait_stats_delta.csv") or _read_csv(root / "sql_wait_stats.csv")
    for row in sorted(waits, key=lambda r: _num(r.get("wait_time_ms") or r.get("delta_wait_time_ms")), reverse=True)[:10]:
        wait = row.get("wait_type") or row.get("waitType") or "wait"
        events.append({"time": metadata.get("pipelineUpdatedAt") or "", "type": "wait-spike", "severity": "medium", "title": f"SQL wait spike {wait}", "detail": f"wait_ms={row.get('wait_time_ms') or row.get('delta_wait_time_ms')} signal_ms={row.get('signal_wait_time_ms') or row.get('delta_signal_wait_time_ms')}"})
    for row in _read_csv(root / "batch_tasks.csv"):
        start = parse_ax_datetime(row.get("start_time"))
        if start:
            events.append({"time": start.isoformat(), "type": "batch", "severity": "info", "title": row.get("caption") or row.get("task_id"), "detail": f"group={row.get('batch_group')} duration={row.get('duration_seconds')}s"})
    for row in _read_csv(root / "ax_live_blocking.csv"):
        blocked = str(row.get("blocking_session_id") or "").lower() not in {"", "0", "n/a", "none"}
        ts = row.get("check_time") or row.get("sample_time") or ""
        if blocked:
            events.append({"time": ts, "type": "blocking", "severity": "high", "title": f"Blocked AX session {row.get('session_id')}", "detail": f"blocker={row.get('blocking_session_id')} wait={row.get('wait_type')} {row.get('wait_time_ms')}ms"})
    for row in _read_csv(root / "query_store_runtime.csv")[:25]:
        ts = row.get("start_time") or row.get("end_time") or ""
        events.append({"time": ts, "type": "query-store", "severity": "medium", "title": f"Query Store query {row.get('query_id')}", "detail": f"avg_duration={row.get('avg_duration_ms')}ms reads={row.get('avg_logical_io_reads')}"})
    for f in _top(findings, 15):
        events.append({"time": f.get("audit", {}).get("analysisTimestamp", ""), "type": "finding", "severity": f.get("severity"), "title": f.get("title"), "detail": f.get("recommendation", {}).get("playbook", "")})
    events = sorted(events, key=lambda x: str(x.get("time", "")))[:500]
    lanes = [{"name": name, "count": count} for name, count in Counter(e["type"] for e in events).most_common()]
    commander_steps = []
    for idx, cause in enumerate(summarize_root_causes(findings)[:6], start=1):
        commander_steps.append({"step": idx, "prove": cause.get("title") or cause.get("name") or "Root cause", "evidenceFirst": cause.get("evidence") or "Review linked findings and source rows.", "then": "Validate with batch, wait, blocking and query evidence in the same time window."})
    return {"eventCount": len(events), "events": events, "lanes": lanes, "rootCauseChain": summarize_root_causes(findings)[:10], "aiIncidentCommander": commander_steps}


def query_plan_diff(evidence: str | Path, trend_db: str | Path | None = None) -> dict[str, Any]:
    root = Path(evidence)
    plan_rows = _read_csv(root / "plan_xml_inventory.csv")
    qs_rows = _read_csv(root / "query_store_runtime.csv")
    by_query = defaultdict(set)
    for row in plan_rows:
        by_query[row.get("query_hash") or "unknown"].add(row.get("plan_hash") or "")
    for row in qs_rows:
        by_query[str(row.get("query_id") or "unknown")].add(str(row.get("plan_id") or ""))
    candidates = []
    for query, plans in by_query.items():
        plans = {p for p in plans if p}
        if len(plans) > 1:
            candidates.append({"query": query, "planCount": len(plans), "plans": sorted(plans)[:10], "risk": "plan-variance", "changeType": "multiple-current-plans"})
    operator_flags = []
    for row in plan_rows[:20]:
        xml = str(row.get("query_plan") or "").upper()
        flags = [flag for flag in ["INDEX SCAN", "TABLE SCAN", "KEY LOOKUP", "HASH MATCH", "SORT", "PARALLELISM"] if flag in xml]
        if flags:
            operator_flags.append({"queryHash": row.get("query_hash"), "planHash": row.get("plan_hash"), "flags": flags, "durationMs": row.get("total_duration_ms")})
    qs_regressions = []
    for row in qs_rows:
        duration = _num(row.get("avg_duration_ms") or row.get("avg_duration"))
        reads = _num(row.get("avg_logical_io_reads") or row.get("avg_logical_reads"))
        if duration > 1000 or reads > 100000:
            qs_regressions.append({"queryId": row.get("query_id"), "planId": row.get("plan_id"), "avgDurationMs": duration, "avgReads": reads, "risk": "query-store-hotspot"})
    historical = {"available": False, "newPlans": [], "changedOperators": [], "regressions": []}
    if trend_db and Path(trend_db).exists():
        with sqlite3.connect(trend_db) as conn:
            conn.row_factory = sqlite3.Row
            try:
                recent_runs = [r[0] for r in conn.execute("SELECT run_id FROM runs ORDER BY rowid DESC LIMIT 2").fetchall()]
                if len(recent_runs) >= 2:
                    current, previous = recent_runs[0], recent_runs[1]
                    current_plans = [dict(r) for r in conn.execute("SELECT * FROM plan_history WHERE run_id = ?", (current,)).fetchall()]
                    previous_keys = {tuple(r) for r in conn.execute("SELECT query_hash, plan_hash, operator_signature FROM plan_history WHERE run_id = ?", (previous,)).fetchall()}
                    previous_perf = {tuple(r[:2]): r for r in conn.execute("SELECT query_hash, plan_hash, duration_ms, reads FROM plan_history WHERE run_id = ?", (previous,)).fetchall()}
                    new_plans = []
                    changed = []
                    regressions = []
                    for row in current_plans:
                        key = (row.get("query_hash"), row.get("plan_hash"), row.get("operator_signature"))
                        if key not in previous_keys:
                            new_plans.append(row)
                        perf_key = (row.get("query_hash"), row.get("plan_hash"))
                        old = previous_perf.get(perf_key)
                        if old and (_num(row.get("duration_ms")) > _num(old[2]) * 1.5 or _num(row.get("reads")) > _num(old[3]) * 1.5):
                            regressions.append({"queryHash": row.get("query_hash"), "planHash": row.get("plan_hash"), "durationBefore": old[2], "durationAfter": row.get("duration_ms"), "readsBefore": old[3], "readsAfter": row.get("reads")})
                    seen_ops: dict[str, set] = defaultdict(set)
                    for row in current_plans:
                        seen_ops[row.get("query_hash")].add(row.get("operator_signature"))
                    changed = [{"queryHash": q, "signatureCount": len(sigs)} for q, sigs in seen_ops.items() if len(sigs) > 1]
                    historical = {"available": True, "currentRun": current, "previousRun": previous, "newPlans": new_plans[:50], "changedOperators": changed[:50], "regressions": regressions[:50]}
            except sqlite3.OperationalError:
                historical = {"available": False, "newPlans": [], "changedOperators": [], "regressions": [], "reason": "plan_history table not available yet"}
    return {
        "planRows": len(plan_rows),
        "queryStoreRows": len(qs_rows),
        "planVarianceCandidates": candidates[:50],
        "operatorFlags": operator_flags,
        "newPlanSignals": candidates[:20],
        "newScanSignals": [x for x in operator_flags if any("SCAN" in f for f in x.get("flags", []))],
        "newLookupSignals": [x for x in operator_flags if any("LOOKUP" in f for f in x.get("flags", []))],
        "newParallelismSignals": [x for x in operator_flags if any("PARALLELISM" in f for f in x.get("flags", []))],
        "queryStoreRegressions": qs_regressions[:50],
        "historicalDiff": historical,
    }


def deadlock_graph(evidence: str | Path) -> dict[str, Any]:
    rows = _read_csv(Path(evidence) / "deadlocks.csv")
    graphs = []
    for idx, row in enumerate(rows[:20], start=1):
        xml = str(row.get("deadlock_xml") or "")
        victim = "unknown"
        nodes = []
        edges = []
        resources = []
        try:
            root = ET.fromstring(xml)
            victim_node = root.find(".//victimProcess")
            if victim_node is not None:
                victim = victim_node.attrib.get("id", "unknown")
            for proc in root.findall(".//process"):
                pid = proc.attrib.get("id") or f"process-{len(nodes)+1}"
                nodes.append({"id": pid, "type": "process", "spid": proc.attrib.get("spid"), "hostname": proc.attrib.get("hostname"), "loginname": proc.attrib.get("loginname"), "waitresource": proc.attrib.get("waitresource"), "victim": pid == victim})
            for res in root.findall(".//resource-list/*"):
                rid = res.attrib.get("objectname") or res.attrib.get("hobtid") or res.tag
                resources.append({"id": rid, "type": res.tag, "mode": res.attrib.get("mode"), "object": res.attrib.get("objectname")})
                for owner in res.findall(".//owner"):
                    edges.append({"from": owner.attrib.get("id"), "to": rid, "type": "owns", "mode": owner.attrib.get("mode")})
                for waiter in res.findall(".//waiter"):
                    edges.append({"from": waiter.attrib.get("id"), "to": rid, "type": "waits", "mode": waiter.attrib.get("mode")})
        except ET.ParseError:
            if "victim" in xml.lower():
                victim = "xml-victim-detected"
        graphs.append({"id": f"deadlock-{idx}", "eventTime": row.get("event_time"), "victim": victim, "nodes": nodes, "resources": resources, "edges": edges, "xmlBytes": len(xml), "nextAction": "Review victim/owner/waiter chain and correlate SPID to AX session."})
    return {"deadlockCount": len(rows), "graphs": graphs, "available": bool(rows)}


def aos_topology(evidence: str | Path) -> dict[str, Any]:
    root = Path(evidence)
    sessions = _read_csv(root / "user_sessions.csv")
    batches = _read_csv(root / "batch_tasks.csv")
    blocking = _read_csv(root / "ax_live_blocking.csv")
    nodes: dict[str, dict[str, Any]] = {}
    for row in sessions:
        aos = row.get("aos") or row.get("host_name") or "unknown"
        nodes.setdefault(aos, {"aos": aos, "sessions": 0, "batchTasks": 0, "blockedRows": 0, "groups": Counter()})
        nodes[aos]["sessions"] += 1
    for row in batches:
        aos = row.get("aos") or "unknown"
        nodes.setdefault(aos, {"aos": aos, "sessions": 0, "batchTasks": 0, "blockedRows": 0, "groups": Counter()})
        nodes[aos]["batchTasks"] += 1
        nodes[aos]["groups"][row.get("batch_group") or "unknown"] += 1
    for row in blocking:
        aos = row.get("host_name") or row.get("aos") or "unknown"
        nodes.setdefault(aos, {"aos": aos, "sessions": 0, "batchTasks": 0, "blockedRows": 0, "groups": Counter()})
        if str(row.get("blocking_session_id") or "").lower() not in {"", "0", "n/a", "none"}:
            nodes[aos]["blockedRows"] += 1
            nodes[aos].setdefault("waits", Counter())
            nodes[aos]["waits"][row.get("wait_type") or "unknown"] += 1
    out = []
    for item in nodes.values():
        item["groups"] = dict(item["groups"].most_common(8))
        item["waits"] = dict(item.get("waits", Counter()).most_common(8))
        item["pressure"] = int(item["sessions"]) + int(item["batchTasks"]) * 2 + int(item["blockedRows"]) * 25
        item["risk"] = "high" if item["blockedRows"] or item["batchTasks"] > 100 else "medium" if item["batchTasks"] > 30 else "low"
        out.append(item)
    edges = []
    for item in out:
        for group, count in item.get("groups", {}).items():
            edges.append({"from": item["aos"], "to": group, "type": "runs-batch-group", "weight": count})
        for wait, count in item.get("waits", {}).items():
            edges.append({"from": item["aos"], "to": wait, "type": "has-wait-pressure", "weight": count})
    return {"nodeCount": len(out), "nodes": sorted(out, key=lambda x: (x["pressure"], x["batchTasks"]), reverse=True), "edges": edges}


def scheduler_hardening(manifest_path: str | Path | None, output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else None
    lock_path = out / ".axpa-pipeline.lock" if out else None
    checks = {
        "lockFile": {"status": "ok" if lock_path and lock_path.exists() else "configured", "path": str(lock_path) if lock_path else "", "recommendation": "Use the lock file path to prevent overlapping scheduled runs."},
        "retention": {"status": "configured", "recommendation": "Keep latest 30 trend runs and rotate evidence/output by age in scheduler."},
        "retry": {"status": "configured", "recommendation": "Retry collectors once, keep failed-run manifest, never suppress non-zero exit codes."},
        "exitCodeMonitoring": {"status": "configured", "recommendation": "Pipeline manifest records every step status, exit code, stdout and stderr tail."},
        "lastSuccessfulRun": {"status": "unknown", "recommendation": "Use manifest finishedAt when status is ok."},
        "healthcheck": {"status": "partial", "recommendation": "Use pipeline manifest status and last successful run age."},
    }
    manifest = {}
    if manifest_path and Path(manifest_path).exists():
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8-sig"))
        checks["healthcheck"]["status"] = "ok" if manifest.get("status") == "ok" else "failed"
        checks["lastSuccessfulRun"]["status"] = "ok" if manifest.get("status") == "ok" else "failed"
    return {"checks": checks, "manifestStatus": manifest.get("status", "unknown"), "lastRun": manifest.get("finishedAt", ""), "lockFile": str(lock_path) if lock_path else ""}


def productive_push_readiness(evidence: str | Path, findings: list[dict[str, Any]]) -> dict[str, Any]:
    top = _top(findings, 20)
    targets = {
        "powerBi": ["AXPA_POWERBI_WORKSPACE_ID", "AXPA_POWERBI_DATASET_ID", "AXPA_POWERBI_TOKEN"],
        "teams": ["AXPA_TEAMS_WEBHOOK_URL"],
        "azureDevOps": ["AXPA_ADO_ORG", "AXPA_ADO_PROJECT", "AXPA_ADO_TOKEN"],
        "jira": ["AXPA_JIRA_BASE_URL", "AXPA_JIRA_PROJECT", "AXPA_JIRA_TOKEN"],
        "serviceNow": ["AXPA_SN_INSTANCE_URL", "AXPA_SN_TOKEN"],
    }
    out = {}
    for target, envs in targets.items():
        missing = [name for name in envs if not __import__("os").environ.get(name)]
        records = len(findings) if target == "powerBi" else len(top)
        dedupe = [_hash_payload({"target": target, "finding": f["id"], "title": f["title"]}) for f in top[:20]]
        out[target] = {
            "status": "ready-to-push" if not missing else "payload-ready",
            "missing": missing,
            "records": records,
            "dedupeKeys": dedupe,
            "audit": {"generatedAt": _utc_now(), "sourceEvidence": str(evidence), "approvalRequired": True},
            "mapping": {"title": "finding.title", "severity": "finding.severity", "owner": "finding.recommendation.owner", "evidence": "finding.evidence"},
        }
    return {
        "mode": "push-capable-with-env-auth",
        **out,
    }


def xpp_attribution(evidence: str | Path, findings: list[dict[str, Any]]) -> dict[str, Any]:
    root = Path(evidence)
    trace = _read_csv(root / "trace_parser.csv") + _read_csv(root / "dynamicsperf.csv")
    ax_model = _read_csv(root / "ax_model_mapping.csv") + _read_csv(root / "ax_sql_to_xpp_mapping.csv")
    mappings = []
    for f in _top(findings, 30):
        tables = f.get("axContext", {}).get("tables") or f.get("sqlContext", {}).get("objects") or []
        candidates = []
        model_hits = []
        for row in trace[:1000]:
            text = json.dumps(row).upper()
            if any(str(table).upper().replace("DBO.", "") in text for table in tables):
                candidates.append(row)
        for row in ax_model[:1000]:
            text = json.dumps(row).upper()
            if any(str(table).upper().replace("DBO.", "") in text for table in tables):
                model_hits.append(row)
        confidence = "high" if candidates else "medium" if model_hits else "low"
        mappings.append({
            "findingId": f["id"],
            "title": f["title"],
            "queryHash": f.get("sqlContext", {}).get("queryHash", ""),
            "tables": tables,
            "traceCandidateCount": len(candidates),
            "modelCandidateCount": len(model_hits),
            "candidateClasses": list({str(r.get("class") or r.get("class_name") or r.get("Class") or "") for r in candidates + model_hits if str(r.get("class") or r.get("class_name") or r.get("Class") or "")})[:10],
            "candidateMethods": list({str(r.get("method") or r.get("method_name") or r.get("Method") or "") for r in candidates + model_hits if str(r.get("method") or r.get("method_name") or r.get("Method") or "")})[:10],
            "batchOrUser": f.get("axContext", {}).get("batchJobs") or f.get("businessImpact", {}).get("usersAffected", ""),
            "businessProcess": f.get("businessImpact", {}).get("process", ""),
            "confidence": confidence,
            "nextEvidence": "Collect Trace Parser call tree and AX model mapping for exact class/method." if confidence == "low" else "Review candidate call stacks and confirm in TEST trace.",
        })
    return {"traceRows": len(trace), "modelRows": len(ax_model), "mappings": mappings, "mapperInputs": ["query text/hash", "AX tables", "Trace Parser", "DynamicsPerf", "AX model mapping", "Batch/User context"]}


def environment_drift_guard(evidence: str | Path) -> dict[str, Any]:
    root = Path(evidence)
    rows = []
    core_files = ["query_store_status.csv", "statistics_age.csv", "missing_indexes.csv", "batch_tasks.csv", "source_status.csv", "file_latency.csv", "index_fragmentation.csv", "sql_top_queries.csv", "user_sessions.csv"]
    for file in core_files:
        path = root / file
        rows.append({"source": file, "present": path.exists(), "bytes": path.stat().st_size if path.exists() else 0, "driftRisk": "high" if not path.exists() or path.stat().st_size == 0 else "observable"})
    dimensions = {
        "indexes": {"source": "index_fragmentation.csv", "rows": len(_read_csv(root / "index_fragmentation.csv")), "compare": "index name, table, fragmentation, page count"},
        "queryStore": {"source": "query_store_runtime.csv", "rows": len(_read_csv(root / "query_store_runtime.csv")), "compare": "query id, plan id, duration, reads, executions"},
        "batchConfig": {"source": "batch_tasks.csv", "rows": len(_read_csv(root / "batch_tasks.csv")), "compare": "batch group, class, schedule window, AOS"},
        "aosAssignment": {"source": "user_sessions.csv", "rows": len(_read_csv(root / "user_sessions.csv")), "compare": "AOS host, session type, batch groups"},
        "sqlSettings": {"source": "query_store_status.csv", "rows": len(_read_csv(root / "query_store_status.csv")), "compare": "Query Store, compatibility level, database options"},
        "statisticsAge": {"source": "statistics_age.csv", "rows": len(_read_csv(root / "statistics_age.csv")), "compare": "table, statistic, rows, modification percent"},
        "dataVolume": {"source": "statistics_age.csv", "rows": len(_read_csv(root / "statistics_age.csv")), "compare": "table rows and modification pattern"},
    }
    comparisons = []
    siblings = [p for p in root.parent.iterdir() if p.is_dir() and p != root] if root.parent.exists() else []
    for other in siblings[:8]:
        diff = {"environment": other.name, "dimensions": {}}
        for name, meta in dimensions.items():
            this_rows = _read_csv(root / meta["source"])
            other_rows = _read_csv(other / meta["source"])
            this_keys = {_hash_payload(row) for row in this_rows[:2000]}
            other_keys = {_hash_payload(row) for row in other_rows[:2000]}
            diff["dimensions"][name] = {
                "thisRows": len(this_rows),
                "otherRows": len(other_rows),
                "onlyHere": len(this_keys - other_keys),
                "onlyThere": len(other_keys - this_keys),
                "risk": "high" if abs(len(this_rows) - len(other_rows)) > max(10, len(this_rows) * 0.25) else "medium" if this_keys != other_keys else "low",
            }
        comparisons.append(diff)
    return {"sources": rows, "dimensions": dimensions, "comparisons": comparisons, "recommendation": "Run the same pipeline on TEST and PROD, then compare indexes, Query Store, batch config, AOS assignment, SQL settings, statistics age and data volume."}


def ai_decision_cockpit(findings: list[dict[str, Any]], evidence: str | Path | None = None) -> dict[str, Any]:
    high = [f for f in findings if f.get("severity") in {"critical", "high"}]
    playbooks = Counter(f.get("recommendation", {}).get("playbook", "review") for f in findings)
    top = _top(findings, 10)
    confidence_ladder = []
    for f in top:
        finding_evidence = f.get("evidence", [])
        confidence_ladder.append({
            "findingId": f["id"],
            "assumption": f.get("likelyCause", ""),
            "existingEvidence": [f"{e.get('source')}:{e.get('metric')}={e.get('value')}" for e in finding_evidence[:4]],
            "missingEvidence": "Trace Parser/DynamicsPerf or before/after baseline" if f.get("confidence") != "high" else "Post-change validation evidence",
            "nextProof": f.get("validation", {}).get("successMetric", "Collect matching evidence in same time window."),
            "confidence": f.get("confidence", "unknown"),
        })
    process_briefs: dict[str, dict[str, Any]] = {}
    for f in findings:
        process = f.get("businessImpact", {}).get("process") or f.get("axContext", {}).get("module") or "Unknown"
        item = process_briefs.setdefault(process, {"process": process, "findings": 0, "high": 0, "topRisks": Counter(), "brief": ""})
        item["findings"] += 1
        if f.get("severity") in {"critical", "high"}:
            item["high"] += 1
        item["topRisks"][f.get("recommendation", {}).get("playbook", "review")] += 1
    for item in process_briefs.values():
        risks = ", ".join(k for k, _ in item["topRisks"].most_common(3))
        item["topRisks"] = risks
        item["brief"] = f"{item['process']}: {item['high']} high risks across {item['findings']} findings; focus on {risks or 'review'}."
    batch_twin = []
    if evidence:
        try:
            batch = batch_collision_summary(load_evidence(evidence))
            for item in batch.get("groupCollisions", [])[:8]:
                reduction = min(90, max(15, int(_num(item.get("totalOverlapSeconds"))) // 60))
                batch_twin.append({
                    "scenario": f"Move one group from {item.get('groups')} outside the overlap window",
                    "groups": item.get("groups"),
                    "currentOverlapSeconds": item.get("totalOverlapSeconds"),
                    "expectedOverlapReductionPercent": reduction,
                    "validation": "Re-run collector and compare groupCollisions.totalOverlapSeconds plus peakConcurrency.",
                })
        except Exception:
            batch_twin = []
    if not batch_twin:
        batch_twin = [{"scenario": f"Move {name} group out of collision window", "expectedOverlapReductionPercent": min(80, count * 10), "validation": "Re-run collector and compare batch_collision_summary."} for name, count in playbooks.items() if "batch" in name][:5]
    evidence_coach = []
    if evidence:
        root = Path(evidence)
        expected = [
            ("Trace Parser/DynamicsPerf", ["trace_parser.csv", "dynamicsperf.csv"], "During next slow batch or blocking window", "Needed for Query-to-X++ class/method attribution."),
            ("SQL snapshot with Query Store", ["query_store_runtime.csv", "query_store_status.csv"], "Before and after TEST change", "Needed for regression watch and CAB validation."),
            ("Deadlock XML", ["deadlocks.csv"], "During blocking/deadlock windows", "Needed for victim/owner/waiter graph."),
            ("AX batch tasks", ["batch_tasks.csv"], "Daily and before/after schedule changes", "Needed for AI Batch Twin and collision validation."),
        ]
        for label, files, when, why in expected:
            present = any((root / file).exists() and (root / file).stat().st_size > 3 for file in files)
            evidence_coach.append({"collector": label, "present": present, "files": files, "when": when, "why": why})
    return {
        "cioAsk": "Approve focused TEST validation for the top evidence-backed AX/SQL risks.",
        "cabAsk": "Review high-confidence batch, statistics, plan and index-risk candidates with rollback evidence.",
        "thisWeek": [{"decision": f"Handle {name}", "findingCount": count, "why": "Dominant current risk group"} for name, count in playbooks.most_common(5)],
        "riskIfDeferred": f"{len(high)} high/critical findings remain open; recurring batch/SQL pressure may continue into business windows.",
        "nonGoals": ["No blind production index changes", "No automatic AX configuration changes", "No external transmission without credentials and approval"],
        "incidentCommander": [{"findingId": f["id"], "first": "Verify time-window correlation", "second": f.get("recommendation", {}).get("summary", ""), "third": f.get("validation", {}).get("successMetric", "")} for f in top[:5]],
        "batchTwin": batch_twin,
        "changeBoardBrief": [{"findingId": f["id"], "benefit": f.get("changeReadiness", {}).get("benefit"), "risk": f.get("changeReadiness", {}).get("technicalRisk"), "testPlan": f.get("validation", {}).get("successMetric"), "rollback": f.get("validation", {}).get("rollback")} for f in top[:8]],
        "confidenceLadder": confidence_ladder,
        "safeRemediationPlanner": [{"findingId": f["id"], "score": SEV.get(f.get("severity"), 1) * (2 if f.get("confidence") == "high" else 1), "risk": f.get("changeReadiness", {}).get("technicalRisk"), "gxpEffort": f.get("changeReadiness", {}).get("testEffort"), "rollback": f.get("changeReadiness", {}).get("rollbackComplexity")} for f in top],
        "regressionWatch": [{"findingId": f["id"], "watch": f.get("recommendation", {}).get("playbook"), "signal": f.get("validation", {}).get("successMetric")} for f in findings if "regression" in f.get("recommendation", {}).get("playbook", "") or "plan" in f.get("recommendation", {}).get("playbook", "")][:10],
        "processOwnerBriefings": list(process_briefs.values())[:20],
        "evidenceQualityCoach": evidence_coach or [{"collector": "Trace Parser/DynamicsPerf", "when": "During next slow batch or blocking window", "why": "Needed for Query-to-X++ class/method attribution."}, {"collector": "SQL snapshot with Query Store", "when": "Before and after TEST change", "why": "Needed for regression watch and CAB validation."}],
        "modernizationSignal": {"tuneNow": len([f for f in findings if f.get("classification") == "tune-now"]), "structuralModernization": len([f for f in findings if f.get("dataGrowth", {}).get("archiveCandidate") or f.get("recommendation", {}).get("playbook") in {"data-growth", "sql2016-support-risk"}]), "message": "Tune high-confidence operational issues first; use recurring data-growth/support-risk signals for D365, archiving or platform modernization decisions."},
    }


def live_batch_collision_watch(evidence: str | Path) -> dict[str, Any]:
    summary = batch_collision_summary(load_evidence(evidence))
    alerts = []
    for item in summary.get("groupCollisions", [])[:20]:
        severity = "critical" if _num(item.get("totalOverlapSeconds")) >= 3600 else "high" if _num(item.get("totalOverlapSeconds")) >= 900 else "medium"
        alerts.append({
            "severity": severity,
            "groups": item.get("groups"),
            "collisions": item.get("collisions"),
            "totalOverlapSeconds": item.get("totalOverlapSeconds"),
            "message": f"Batch groups {item.get('groups')} overlap {item.get('collisions')} times; monitor live blocking during this window.",
            "nextCheck": "Refresh batch_tasks.csv and ax_live_blocking.csv every 1-5 minutes during peak.",
        })
    return {
        "mode": "evidence-watch",
        "collisionCount": summary.get("collisionCount", 0),
        "peakConcurrency": summary.get("peakConcurrency", 0),
        "peakWindow": summary.get("peakWindow", ""),
        "alerts": alerts,
    }


def batch_reschedule_calendar(evidence: str | Path) -> dict[str, Any]:
    root = Path(evidence)
    tasks = []
    for row in _read_csv(root / "batch_tasks.csv"):
        start = parse_ax_datetime(row.get("start_time"))
        end = parse_ax_datetime(row.get("end_time"))
        if not start or not end:
            continue
        tasks.append({
            "taskId": row.get("task_id"),
            "caption": row.get("caption") or row.get("task_id"),
            "group": row.get("batch_group") or "unknown",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "durationSeconds": int(_num(row.get("duration_seconds"))),
            "hour": start.strftime("%H:00"),
        })
    by_hour = Counter(t["hour"] for t in tasks)
    load_by_hour = {f"{hour:02d}:00": by_hour.get(f"{hour:02d}:00", 0) for hour in range(24)}
    group_by_hour: dict[str, Counter] = defaultdict(Counter)
    tasks_by_hour_group: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for task in tasks:
        group_by_hour[task["hour"]][task["group"]] += 1
        tasks_by_hour_group[(task["hour"], task["group"])].append(task)

    def target_slot(source_hour: str, avoid_group: str) -> tuple[str, int]:
        source_num = int(source_hour.split(":")[0])
        candidates = []
        for hour, load in load_by_hour.items():
            hour_num = int(hour.split(":")[0])
            if hour == source_hour:
                continue
            # Prefer nearby night/early-morning windows, but avoid moving into the same group's existing peak.
            distance = min((hour_num - source_num) % 24, (source_num - hour_num) % 24)
            same_group_penalty = group_by_hour.get(hour, Counter()).get(avoid_group, 0) * 3
            business_penalty = 3 if 7 <= hour_num <= 18 else 0
            candidates.append((load + same_group_penalty + business_penalty, distance, hour))
        best = min(candidates, default=(0, 0, source_hour))
        return best[2], int(best[0])

    proposals = []
    for hour, count in by_hour.most_common(12):
        if count < 2:
            continue
        groups = [t["group"] for t in tasks if t["hour"] == hour]
        move_group = Counter(groups).most_common(1)[0][0]
        target, target_score = target_slot(hour, move_group)
        move_tasks = sorted(tasks_by_hour_group[(hour, move_group)], key=lambda t: (t["durationSeconds"], t["caption"]), reverse=True)
        move_count = len(move_tasks)
        current_group_mix = group_by_hour[hour].most_common(5)
        after_peak = max(0, count - move_count)
        reduction = round((count - after_peak) / max(1, count) * 100)
        target_task_count = load_by_hour.get(target, 0)
        target_group_count = group_by_hour.get(target, Counter()).get(move_group, 0)
        group_share = round(move_count / max(1, count) * 100)
        dominant_text = ", ".join(f"{group}={tasks_count}" for group, tasks_count in current_group_mix)
        named_examples = [t["caption"] for t in move_tasks if t.get("caption")][:5]
        business_window = "business-hour" if 7 <= int(hour.split(":")[0]) <= 18 else "off-hour"
        target_window = "business-hour" if 7 <= int(target.split(":")[0]) <= 18 else "off-hour"
        decision = (
            f"{move_group} is the largest contributor in the {hour} peak ({move_count}/{count} tasks, {group_share}%). "
            f"The target {target} currently has {target_task_count} task(s) and {target_group_count} task(s) from the same group, "
            f"so it is less likely to recreate the same collision pattern."
        )
        proposals.append({
            "currentHour": hour,
            "taskCount": count,
            "moveGroup": move_group,
            "moveTaskCount": move_count,
            "targetHour": target,
            "targetTaskCount": target_task_count,
            "targetLoadScore": target_score,
            "targetSameGroupTasks": target_group_count,
            "groupSharePercent": group_share,
            "currentPeakAfterMove": after_peak,
            "sourceWindowType": business_window,
            "targetWindowType": target_window,
            "currentGroupMix": [{"group": group, "tasks": tasks_count} for group, tasks_count in current_group_mix],
            "exampleTasks": [{"taskId": t["taskId"], "caption": t["caption"], "durationSeconds": t["durationSeconds"]} for t in move_tasks[:8]],
            "proposal": f"Move {move_count} task(s) from batch group {move_group} out of {hour} to {target}.",
            "expectedOverlapReductionPercent": min(90, max(5, reduction)),
            "reason": f"{hour} has {count} batch task(s); group mix is {dominant_text}. {decision}",
            "decisionRationale": decision,
            "expectedEffect": f"Peak task count in {hour} would drop from {count} to about {after_peak}; calculated reduction is {min(90, max(5, reduction))}%.",
            "riskNote": f"Check dependencies for {move_group}, especially downstream jobs after {target}; target slot is {target_window} and source slot is {business_window}.",
            "implementationHint": f"In TEST, move only the recurrence/start time for batch group {move_group} from {hour} to {target}; do not change class, company, parameters or AOS assignment in the first test.",
            "validation": "After the TEST run compare: peak concurrency in source/target hour, batch duration p95, blocking rows, Query Store reads and business completion time.",
            "rollback": f"Restore original {hour} schedule for group {move_group} if SLA, downstream dependency, blocking or business completion metrics regress.",
            "changeCandidate": f"Candidate change: {move_group} {hour} -> {target}; examples: {', '.join(named_examples) if named_examples else 'no captions available'}.",
        })
    return {
        "taskCount": len(tasks),
        "calendar": [{"hour": hour, "taskCount": count, "groups": [{"group": group, "tasks": tasks_count} for group, tasks_count in group_by_hour.get(hour, Counter()).most_common(5)]} for hour, count in sorted(by_hour.items())],
        "proposals": proposals,
        "lowLoadSlots": [{"hour": hour, "taskCount": count} for hour, count in sorted(load_by_hour.items(), key=lambda x: (x[1], x[0]))[:8]],
        "peakSlots": [{"hour": hour, "taskCount": count, "dominantGroup": group_by_hour.get(hour, Counter()).most_common(1)[0][0] if group_by_hour.get(hour) else "unknown"} for hour, count in by_hour.most_common(8)],
    }


def batch_dependency_graph(evidence: str | Path) -> dict[str, Any]:
    root = Path(evidence)
    jobs = {str(row.get("job_id") or row.get("RECID") or ""): row for row in _read_csv(root / "batch_jobs.csv")}
    tasks_by_job: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _read_csv(root / "batch_tasks.csv"):
        job_id = str(row.get("job_id") or row.get("BATCHJOBID") or "")
        start = parse_ax_datetime(row.get("start_time"))
        end = parse_ax_datetime(row.get("end_time"))
        if not job_id or not start:
            continue
        tasks_by_job[job_id].append({
            "taskId": row.get("task_id"),
            "jobId": job_id,
            "caption": row.get("caption") or row.get("task_id"),
            "group": row.get("batch_group") or "unknown",
            "start": start,
            "end": end or start,
            "durationSeconds": int(_num(row.get("duration_seconds"))),
        })
    chains = []
    edge_counter: Counter[tuple[str, str]] = Counter()
    reschedule_risks = []
    for job_id, tasks in tasks_by_job.items():
        ordered = sorted(tasks, key=lambda t: (t["start"], t["end"], str(t["taskId"])))
        groups = [task["group"] for task in ordered]
        unique_groups = list(dict.fromkeys(groups))
        duration = sum(task["durationSeconds"] for task in ordered)
        transitions = []
        for left, right in zip(ordered, ordered[1:]):
            if left["group"] != right["group"]:
                edge_counter[(left["group"], right["group"])] += 1
                transitions.append({"fromGroup": left["group"], "toGroup": right["group"], "fromTask": left["caption"], "toTask": right["caption"]})
        risk = "high" if len(unique_groups) > 1 and duration >= 1800 else "medium" if len(unique_groups) > 1 else "low"
        chains.append({
            "jobId": job_id,
            "jobName": jobs.get(job_id, {}).get("job_name") or ordered[0]["caption"],
            "taskCount": len(ordered),
            "groups": unique_groups,
            "durationSeconds": duration,
            "risk": risk,
            "transitions": transitions,
            "firstStart": ordered[0]["start"].isoformat(),
            "lastEnd": ordered[-1]["end"].isoformat(),
        })
        for group in unique_groups:
            dependent = [g for g in unique_groups if g != group]
            if dependent:
                reschedule_risks.append({
                    "jobId": job_id,
                    "jobName": jobs.get(job_id, {}).get("job_name") or ordered[0]["caption"],
                    "moveGroup": group,
                    "dependentGroups": dependent,
                    "risk": f"Moving {group} without {', '.join(dependent)} can split job chain {job_id}.",
                    "validation": "Confirm predecessor/successor order and business cutoff before changing recurrence.",
                })
    edges = [{"fromGroup": left, "toGroup": right, "count": count} for (left, right), count in edge_counter.most_common()]
    return {
        "chainCount": len(chains),
        "edgeCount": len(edges),
        "chains": sorted(chains, key=lambda x: (SEV.get(x["risk"], 0), x["durationSeconds"], x["taskCount"]), reverse=True)[:50],
        "edges": edges[:50],
        "rescheduleRisks": reschedule_risks[:50],
        "recommendation": "Use this graph before accepting Batch Reschedule Calendar moves; move dependent groups together or validate downstream cutoffs in TEST.",
    }


def sql_blocking_chain_recorder(evidence: str | Path) -> dict[str, Any]:
    rows = _read_csv(Path(evidence) / "ax_live_blocking.csv") + _read_csv(Path(evidence) / "blocking.csv")
    sessions: dict[str, dict[str, Any]] = {}
    victims_by_blocker: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        sid = str(row.get("session_id") or row.get("SessionId") or "")
        blocker = str(row.get("blocking_session_id") or row.get("BlockingSessionId") or "").lower()
        if not sid:
            continue
        sessions[sid] = {
            "sessionId": sid,
            "blocker": "" if blocker in {"", "0", "n/a", "none"} else blocker,
            "user": row.get("user_id") or row.get("UserId") or "",
            "host": row.get("host_name") or row.get("HostName") or "",
            "waitType": row.get("wait_type") or row.get("waitType") or "",
            "waitMs": _num(row.get("wait_time_ms") or row.get("waitMs")),
            "query": row.get("statement_text") or row.get("Query") or "",
            "checkTime": row.get("check_time") or row.get("CheckDate") or "",
        }
        if sessions[sid]["blocker"]:
            victims_by_blocker[sessions[sid]["blocker"]].append(sid)
    chains = []
    for blocker, victims in victims_by_blocker.items():
        chains.append({
            "rootBlocker": blocker,
            "victimCount": len(victims),
            "victims": victims[:25],
            "totalWaitMs": sum(sessions[v].get("waitMs", 0) for v in victims if v in sessions),
            "rootKnown": blocker in sessions,
        })
    return {"sampleCount": len(rows), "chainCount": len(chains), "chains": sorted(chains, key=lambda x: x["totalWaitMs"], reverse=True)[:50], "sessions": list(sessions.values())[:200]}


def ax_business_process_sla(findings: list[dict[str, Any]]) -> dict[str, Any]:
    processes: dict[str, dict[str, Any]] = {}
    for f in findings:
        process = f.get("businessImpact", {}).get("process") or f.get("axContext", {}).get("module") or "Unknown"
        item = processes.setdefault(process, {"process": process, "findings": 0, "high": 0, "riskPoints": 0, "status": "green", "topPlaybooks": Counter()})
        item["findings"] += 1
        item["riskPoints"] += SEV.get(f.get("severity"), 1)
        item["topPlaybooks"][f.get("recommendation", {}).get("playbook", "review")] += 1
        if f.get("severity") in {"critical", "high"}:
            item["high"] += 1
    rows = []
    for item in processes.values():
        item["status"] = "red" if item["high"] >= 3 else "amber" if item["high"] or item["riskPoints"] >= 10 else "green"
        item["topPlaybooks"] = ", ".join(k for k, _ in item["topPlaybooks"].most_common(3))
        rows.append(item)
    return {"processCount": len(rows), "items": sorted(rows, key=lambda x: (x["status"] == "red", x["riskPoints"]), reverse=True)}


def evidence_gap_assistant(evidence: str | Path, findings: list[dict[str, Any]]) -> dict[str, Any]:
    root = Path(evidence)
    required = [
        {"capability": "X++ Attribution Deep Mode", "files": ["trace_parser.csv", "dynamicsperf.csv", "ax_model_mapping.csv"], "collector": "collect_trace_parser_or_dynamicsperf", "when": "during the slow batch or blocking window"},
        {"capability": "Deadlock Graph Visualizer", "files": ["deadlocks.csv"], "collector": "collect_sql_snapshot.ps1 -IncludeDeadlocks", "when": "during deadlock incidents"},
        {"capability": "Deployment Regression Guard", "files": ["query_store_runtime.csv", "plan_xml_inventory.csv"], "collector": "collect_sql_snapshot.ps1 before and after deployment", "when": "before and after every AX/SQL change"},
        {"capability": "Live Blocking Chain Recorder", "files": ["ax_live_blocking.csv", "blocking.csv"], "collector": "collect_ax_db_snapshot.ps1 -IncludeLiveBlocking", "when": "every 1-5 minutes during peak"},
        {"capability": "Batch Reschedule Simulator", "files": ["batch_tasks.csv"], "collector": "collect_ax_db_snapshot.ps1 -IncludeBatchTasks", "when": "daily and around overnight batch windows"},
    ]
    gaps = []
    for item in required:
        present = [file for file in item["files"] if (root / file).exists() and (root / file).stat().st_size > 3]
        missing = [file for file in item["files"] if file not in present]
        gaps.append({**item, "present": present, "missing": missing, "status": "ok" if not missing else "partial" if present else "missing"})
    low_conf = sum(1 for f in findings if f.get("confidence") != "high")
    return {"gapCount": sum(1 for g in gaps if g["status"] != "ok"), "lowConfidenceFindings": low_conf, "gaps": gaps}


def deployment_regression_guard(evidence: str | Path, trend_db: str | Path | None) -> dict[str, Any]:
    plan = query_plan_diff(evidence, trend_db)
    root = Path(evidence)
    qs = _read_csv(root / "query_store_runtime.csv")
    top_runtime = sorted(qs, key=lambda r: _num(r.get("avg_duration_ms")), reverse=True)[:15]
    return {
        "status": "active" if qs or plan.get("historicalDiff", {}).get("available") else "needs-baseline",
        "queryStoreRows": len(qs),
        "planDiffAvailable": plan.get("historicalDiff", {}).get("available", False),
        "newPlanCount": len(plan.get("historicalDiff", {}).get("newPlans", [])) + len(plan.get("newPlanSignals", [])),
        "regressionCount": len(plan.get("historicalDiff", {}).get("regressions", [])) + len(plan.get("queryStoreRegressions", [])),
        "topRuntimeQueries": [{"queryId": r.get("query_id"), "planId": r.get("plan_id"), "avgDurationMs": r.get("avg_duration_ms"), "avgReads": r.get("avg_logical_io_reads")} for r in top_runtime],
    }


def admin_remediation_workbench(findings: list[dict[str, Any]]) -> dict[str, Any]:
    actions = []
    for f in _top(findings, 25):
        playbook = f.get("recommendation", {}).get("playbook", "review")
        actions.append({
            "findingId": f["id"],
            "title": f["title"],
            "playbook": playbook,
            "mode": "admin-review-script",
            "scriptType": "sql-review" if any(token in playbook for token in ["index", "statistics", "query", "blocking", "tempdb"]) else "ax-review",
            "allowedAction": "Generate review/validation script; execution requires admin confirmation outside read-only advisor.",
            "validation": f.get("validation", {}).get("successMetric", "Compare before/after evidence."),
            "rollback": f.get("validation", {}).get("rollback", "Restore previous configuration or disable change."),
        })
    return {"actionCount": len(actions), "actions": actions}


def alerting_rules(findings: list[dict[str, Any]], evidence: str | Path) -> dict[str, Any]:
    root = Path(evidence)
    rules = [
        {"rule": "blocking_over_5_minutes", "enabled": bool(_read_csv(root / "ax_live_blocking.csv") or _read_csv(root / "blocking.csv")), "target": "Teams/Email/Webhook", "condition": "blocking wait or elapsed time > 300000 ms"},
        {"rule": "batch_collision_peak", "enabled": bool(_read_csv(root / "batch_tasks.csv")), "target": "Teams/Email/Webhook", "condition": "batch collision count or peak concurrency exceeds baseline"},
        {"rule": "query_store_regression", "enabled": bool(_read_csv(root / "query_store_runtime.csv")), "target": "Teams/Email/Webhook", "condition": "duration/read p95 exceeds self-calibrated threshold"},
        {"rule": "tempdb_pressure", "enabled": bool(_read_csv(root / "tempdb_usage.csv")), "target": "Teams/Email/Webhook", "condition": "TempDB usage or latch/wait finding high"},
        {"rule": "health_score_drop", "enabled": True, "target": "Teams/Email/Webhook", "condition": "health score drops versus previous trend run"},
    ]
    active = [f for f in findings if f.get("severity") in {"critical", "high"}]
    return {"ruleCount": len(rules), "enabledCount": sum(1 for r in rules if r["enabled"]), "rules": rules, "currentHighRiskSignals": len(active)}


def ai_incident_commander(evidence: str | Path, findings: list[dict[str, Any]]) -> dict[str, Any]:
    replay = incident_replay_timeline(evidence, findings)
    chain = []
    for idx, event in enumerate(replay.get("events", [])[:40], start=1):
        if event.get("type") in {"collector", "batch", "blocking", "wait-spike", "query-store", "finding"}:
            chain.append({"step": idx, "time": event.get("time"), "signal": event.get("type"), "statement": event.get("title"), "verifyNext": "Check same time window across Batch, Blocking, Waits and Query Store."})
    return {"eventChainLength": len(chain), "probableChain": chain[:20], "firstProof": "Confirm the peak batch window and root blocker before tuning SQL objects."}


def ai_root_cause_confidence_ladder(findings: list[dict[str, Any]]) -> dict[str, Any]:
    items = []
    for f in _top(findings, 20):
        existing = [f"{e.get('source')}:{e.get('metric')}={e.get('value')}" for e in f.get("evidence", [])[:5]]
        items.append({"findingId": f["id"], "hypothesis": f.get("likelyCause", f.get("title")), "existingEvidence": existing, "missingEvidence": "Post-change validation or X++ trace" if f.get("confidence") != "high" else "Verification run after remediation", "nextProof": f.get("validation", {}).get("successMetric", "Collect matching evidence."), "confidence": f.get("confidence", "unknown")})
    return {"items": items}


def ai_safe_remediation_planner(findings: list[dict[str, Any]]) -> dict[str, Any]:
    items = []
    for f in _top(findings, 30):
        risk = f.get("changeReadiness", {}).get("technicalRisk", "medium")
        benefit = SEV.get(f.get("severity"), 1) * (2 if f.get("confidence") == "high" else 1)
        effort_penalty = 2 if risk == "high" else 1
        items.append({"findingId": f["id"], "priorityScore": round(benefit / effort_penalty, 2), "benefit": benefit, "risk": risk, "downtime": f.get("changeReadiness", {}).get("downtime", "unknown"), "rollbackComplexity": f.get("changeReadiness", {}).get("rollbackComplexity", "medium"), "recommendedLane": "TEST first" if risk != "low" else "standard maintenance"})
    return {"items": sorted(items, key=lambda x: x["priorityScore"], reverse=True)}


def ai_batch_twin(evidence: str | Path) -> dict[str, Any]:
    calendar = batch_reschedule_calendar(evidence)
    return {"scenarioCount": len(calendar.get("proposals", [])), "scenarios": calendar.get("proposals", []), "validation": "Run the same evidence collector after schedule change and compare peakConcurrency/collisionCount."}


def ai_change_board_brief(findings: list[dict[str, Any]]) -> dict[str, Any]:
    briefs = []
    for f in _top(findings, 12):
        briefs.append({"findingId": f["id"], "decision": f"Approve TEST validation for {f['title']}", "businessImpact": f.get("businessImpact", {}).get("summary", ""), "technicalEvidence": [e.get("source") for e in f.get("evidence", [])[:4]], "risk": f.get("changeReadiness", {}).get("technicalRisk"), "testPlan": f.get("validation", {}).get("successMetric"), "rollback": f.get("validation", {}).get("rollback")})
    return {"briefCount": len(briefs), "briefs": briefs}


def ai_safe_features_bundle(evidence: str | Path, findings: list[dict[str, Any]], trend_db: str | Path | None) -> dict[str, Any]:
    return {
        "incidentCommander": ai_incident_commander(evidence, findings),
        "rootCauseConfidenceLadder": ai_root_cause_confidence_ladder(findings),
        "safeRemediationPlanner": ai_safe_remediation_planner(findings),
        "batchTwin": ai_batch_twin(evidence),
        "changeBoardBrief": ai_change_board_brief(findings),
        "regressionWatch": deployment_regression_guard(evidence, trend_db),
    }


def gap_closure(evidence: str | Path, output_dir: str | Path, findings: list[dict[str, Any]], trend_db: str | Path | None, manifest: str | Path | None) -> dict[str, Any]:
    root = Path(evidence)
    out = Path(output_dir)
    deadlocks = _read_csv(root / "deadlocks.csv")
    source_status = _read_csv(root / "source_status.csv")
    retail_path = root / "retail_load.csv"
    trace_rows = _read_csv(root / "trace_parser.csv")
    dynperf_rows = _read_csv(root / "dynamicsperf.csv")
    xpp_rows = _read_csv(root / "ax_sql_to_xpp_mapping.csv") + _read_csv(root / "ax_model_mapping.csv")
    batch_calendar = batch_reschedule_calendar(root)
    lifecycle = recommendation_lifecycle(findings, out / "recommendation-lifecycle-state.json")
    trend = trend_dashboard(root, trend_db)
    manifest_path = Path(manifest) if manifest else out / ".axpa-pipeline-manifest.json"
    trend_runs = int(trend.get("runCount") or 0)
    trace_available = bool(trace_rows or dynperf_rows or xpp_rows)
    push_targets = ["teams", "ado", "jira", "servicenow", "powerbi"]
    missing_push_env = {
        "teams": ["AXPA_TEAMS_WEBHOOK_URL"],
        "ado": ["AXPA_ADO_ORG", "AXPA_ADO_PROJECT", "AXPA_ADO_PAT"],
        "jira": ["AXPA_JIRA_URL", "AXPA_JIRA_PROJECT", "AXPA_JIRA_TOKEN"],
        "servicenow": ["AXPA_SERVICENOW_URL", "AXPA_SERVICENOW_TOKEN"],
        "powerbi": ["AXPA_POWERBI_WORKSPACE_ID", "AXPA_POWERBI_DATASET_ID", "AXPA_POWERBI_TOKEN"],
    }
    return {
        "deadlockCapture": {
            "status": "active" if deadlocks else "collector-needed",
            "evidenceRows": len(deadlocks),
            "collectorCommand": "sqlcmd -S <server> -E -i scripts/setup_deadlock_capture.sql",
            "readCommand": "powershell scripts/collect_sql_snapshot.ps1 -IncludeDeadlocks -ConnectionString <read-only connection>",
            "dashboardEffect": "Deadlock Graph Visualizer will render victim/owner/waiter once xml_deadlock_report rows exist.",
        },
        "xppTraceAttribution": {
            "status": "active" if trace_available else "trace-needed",
            "traceParserRows": len(trace_rows),
            "dynamicsPerfRows": len(dynperf_rows),
            "modelMappingRows": len(xpp_rows),
            "collectorCommand": "Export Trace Parser call tree or DynamicsPerf query history to trace_parser.csv/dynamicsperf.csv during the slow batch window.",
            "mappingRule": "SQL query/table -> Trace Parser call tree -> AX class/method -> batch job/user -> business process.",
        },
        "retailLoadStatus": {
            "status": "has-data" if retail_path.exists() and retail_path.stat().st_size > 3 else "empty-or-not-used",
            "bytes": retail_path.stat().st_size if retail_path.exists() else 0,
            "sourceStatus": next((r.get("status") for r in source_status if r.get("source") == "RETAILTRANSACTIONTABLE"), "unknown"),
            "recommendation": "If Retail is in scope, validate RETAILTRANSACTIONTABLE date predicates and store/company filters; otherwise mark Retail as not used in metadata.",
        },
        "productivePushExecution": {
            "status": "dry-run-ready",
            "targets": push_targets,
            "dryRunCommand": f"python scripts/push_integrations.py --evidence {root} --targets {','.join(push_targets)} --audit-db {out / 'push-audit.sqlite'} --dry-run",
            "missingEnvironmentVariables": {target: [name for name in names if not os.environ.get(name)] for target, names in missing_push_env.items()},
            "dedupe": "Finding hash + target system + title prevents duplicate tickets/messages.",
        },
        "adminExecutionGate": {
            "status": "review-gated",
            "workflow": lifecycle.get("workflow", []),
            "requiredState": "approved",
            "executionRule": "Only TEST execution after approval reference, matching confirmation token, generated script review and before/after evidence plan.",
            "blockedInProdByDefault": True,
        },
        "schedulerInstall": {
            "status": "install-script-needed" if not manifest_path.exists() else "manifest-present",
            "installCommand": f"powershell scripts/install_windows_task.ps1 -Environment <env> -Server <server> -Database <db> -Evidence {root} -Out {out}",
            "healthcheck": "Scheduled run must update pipeline manifest, remove stale lock, record exit code and retain latest successful run timestamp.",
            "retention": "Keep latest 30 outputs and evidence runs; archive or delete older local run folders after review.",
        },
        "trendRunQuality": {
            "status": "good" if trend_runs >= 10 else "needs-more-runs",
            "runCount": trend_runs,
            "quality": "High" if trend_runs >= 10 else "Medium" if trend_runs >= 3 else "Low",
            "nextStep": "Schedule recurring snapshots so health score, high findings, Query Store risk and batch peak trends become statistically useful.",
        },
        "batchDependencyAwareReschedule": {
            "status": "active" if batch_calendar.get("proposals") else "needs-batch-history",
            "proposalCount": len(batch_calendar.get("proposals", [])),
            "dependencies": [{"group": p.get("moveGroup"), "from": p.get("currentHour"), "to": p.get("targetHour"), "risk": p.get("riskNote"), "validation": p.get("validation")} for p in batch_calendar.get("proposals", [])[:10]],
            "nextStep": "Add explicit predecessor/successor metadata from AX batch recurrence/config exports to prevent moving dependent jobs across cutoffs.",
        },
        "llmRagCopilot": {
            "status": "optional-local-context-ready",
            "contextCommand": f"python scripts/rag_qa.py --evidence {root} --question \"Warum ist AX langsam?\"",
            "guardrails": ["Use anonymized/masked evidence packs", "Cite source CSV rows/files", "Never execute changes from chat output"],
            "missingForLiveLlm": ["LLM provider config", "data masking approval", "prompt/evidence retention policy"],
        },
        "githubReleaseReadiness": {
            "status": "needs-final-review",
            "releaseChecklist": [
                "Run pytest and dashboard browser audit",
                "Review git status and separate generated evidence from source changes",
                "Refresh README quickstart and operations guide",
                "Add anonymized sample evidence or document how to generate it",
                "Create release notes for collectors, dashboard, platform extensions and known limitations",
            ],
            "githubFiles": ["README.md", "LICENSE", ".gitignore", "docs/operations-guide.md", "docs/platform-extensions.md"],
            "actionPack": str(out / "gap-closure-actions.md"),
        },
    }


def write_gap_closure_actions(out: Path, gaps: dict[str, Any]) -> None:
    actions = {
        "generatedAt": _utc_now(),
        "items": [
            {"feature": feature, "status": detail.get("status", "unknown"), "actions": {k: v for k, v in detail.items() if k != "status"}}
            for feature, detail in gaps.items()
        ],
    }
    write_json(out / "gap-closure-actions.json", actions)
    lines = ["# AXPA Gap Closure Actions", ""]
    title_map = {
        "deadlockCapture": "Deadlock capture",
        "xppTraceAttribution": "X++ trace attribution",
        "retailLoadStatus": "Retail load status",
        "productivePushExecution": "Productive push execution",
        "adminExecutionGate": "Admin execution gate",
        "schedulerInstall": "Scheduler install",
        "trendRunQuality": "Trend run quality",
        "batchDependencyAwareReschedule": "Batch dependency-aware reschedule",
        "llmRagCopilot": "LLM/RAG copilot",
        "githubReleaseReadiness": "GitHub release readiness",
    }
    for feature, detail in gaps.items():
        lines.append(f"## {title_map.get(feature, feature)}")
        lines.append("")
        lines.append(f"Status: `{detail.get('status', 'unknown')}`")
        lines.append("")
        for key, value in detail.items():
            if key == "status":
                continue
            rendered = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
            lines.append(f"- **{key}:** {rendered}")
        lines.append("")
    (out / "gap-closure-actions.md").write_text("\n".join(lines), encoding="utf-8")


def strategic_usp_pack(evidence: str | Path, findings: list[dict[str, Any]], trend_db: str | Path | None = None) -> dict[str, Any]:
    root = Path(evidence)
    dependency = batch_dependency_graph(root)
    batch_calendar = batch_reschedule_calendar(root)
    deadlocks = deadlock_graph(root)
    aos = aos_topology(root)
    evidence_health = evidence_gap_assistant(root, findings)
    stats = _read_csv(root / "statistics_age.csv")
    known_patterns = {
        "batch-collision": "AX 2012 batch window collision pattern",
        "blocking": "AX worker blocking / long transaction pattern",
        "index-risk-review": "AX index/statistics review pattern",
        "deployment-regression": "Query Store regression pattern",
        "data-growth": "AX table growth / archiving pressure pattern",
    }

    contracts = []
    for proposal in batch_calendar.get("proposals", [])[:12]:
        contracts.append({
            "batchGroup": proposal.get("moveGroup"),
            "targetWindow": proposal.get("targetHour"),
            "latestFinish": proposal.get("targetHour"),
            "businessOwner": "process owner required",
            "escalation": "Escalate if batch p95, blocking rows or business completion time regress after TEST move.",
            "validation": proposal.get("validation"),
        })

    deadlock_attribution = []
    for graph in deadlocks.get("graphs", [])[:10]:
        objects = [r.get("object") for r in graph.get("resources", []) if r.get("object")]
        deadlock_attribution.append({
            "deadlockId": graph.get("id"),
            "victim": graph.get("victim"),
            "tables": objects,
            "axProcess": "batch/user attribution requires matching ax_live_blocking or Trace Parser window",
            "confidence": "medium" if objects else "low",
        })

    affinity = []
    for node in aos.get("nodes", [])[:12]:
        pressure = _num(node.get("pressure"))
        affinity.append({
            "aos": node.get("aos"),
            "sessions": node.get("sessions"),
            "batchTasks": node.get("batchTasks"),
            "blockedRows": node.get("blockedRows"),
            "recommendation": "Keep heavy batch groups away from this AOS during peak." if pressure > 10 else "Candidate for low-risk batch affinity after TEST validation.",
            "risk": node.get("risk"),
        })

    growth_candidates = []
    for row in sorted(stats, key=lambda r: _num(r.get("rows")), reverse=True)[:15]:
        table = row.get("object_name") or row.get("table_name") or row.get("name") or "unknown"
        rows = int(_num(row.get("rows")))
        mods = int(_num(row.get("modification_counter")))
        growth_candidates.append({
            "table": table,
            "rows": rows,
            "modifications": mods,
            "roi": "archive-first" if rows > 10_000_000 else "tune-first",
            "reason": "Large table footprint can create recurring stats, IO and index maintenance debt.",
        })

    simulations = []
    top_findings = _top(findings, 8)
    for idx, proposal in enumerate(batch_calendar.get("proposals", [])[:5]):
        linked = top_findings[idx % len(top_findings)] if top_findings else {}
        simulations.append({
            "scenario": f"{proposal.get('moveGroup')} {proposal.get('currentHour')} -> {proposal.get('targetHour')} + {linked.get('recommendation', {}).get('playbook', 'top finding review')}",
            "expectedEffect": proposal.get("expectedEffect"),
            "risk": proposal.get("riskNote"),
            "validation": "Run TEST snapshot before/after and compare Health Score, batch peak, blocking rows and Query Store reads.",
        })

    evidence_score = max(0, 100 - evidence_health.get("gapCount", 0) * 8 - evidence_health.get("lowConfidenceFindings", 0))
    matched = []
    for finding in findings[:50]:
        playbook = finding.get("recommendation", {}).get("playbook", "")
        for token, pattern in known_patterns.items():
            if token in playbook or token in finding.get("classification", "") or token in finding.get("likelyCause", ""):
                matched.append({"findingId": finding.get("id"), "pattern": pattern, "confidence": finding.get("confidence", "medium"), "nextAction": finding.get("recommendation", {}).get("summary", "")})
                break

    maturity_components = {
        "monitoring": 20 if (root / "sql_wait_stats.csv").exists() and (root / "query_store_runtime.csv").exists() else 10,
        "batch": 20 if batch_calendar.get("proposals") and dependency.get("chains") else 10,
        "sql": 20 if (root / "plan_xml_inventory.csv").exists() and (root / "statistics_age.csv").exists() else 10,
        "governance": 20 if evidence_health.get("gapCount", 99) < 3 else 10,
        "automation": 20 if trend_dashboard(root, trend_db).get("runCount", 0) >= 5 else 10,
    }
    maturity_score = sum(maturity_components.values())
    structural = len([c for c in growth_candidates if c["roi"] == "archive-first"]) + len([f for f in findings if f.get("recommendation", {}).get("playbook") in {"sql2016-support-risk", "data-growth"}])
    tune = len([f for f in findings if f.get("confidence") == "high" and f.get("severity") in {"critical", "high"}])
    return {
        "batchDependencyGraph": dependency,
        "batchSlaContractManager": {"contractCount": len(contracts), "contracts": contracts, "defaultRule": "Every shifted group needs target window, owner, latest finish, escalation and rollback."},
        "deadlockToAxProcessAttribution": {"deadlockCount": deadlocks.get("deadlockCount", 0), "items": deadlock_attribution, "nextEvidence": "Collect deadlock XML plus matching ax_live_blocking and Trace Parser rows."},
        "aosAffinityAdvisor": {"nodeCount": aos.get("nodeCount", 0), "recommendations": affinity},
        "dataGrowthArchivingRoi": {"candidateCount": len(growth_candidates), "candidates": growth_candidates},
        "changeSimulationQueue": {"simulationCount": len(simulations), "simulations": simulations},
        "evidenceSla": {"score": evidence_score, "status": "green" if evidence_score >= 80 else "amber" if evidence_score >= 55 else "red", "gapCount": evidence_health.get("gapCount", 0), "lowConfidenceFindings": evidence_health.get("lowConfidenceFindings", 0), "requiredForCab": ["before snapshot", "after TEST snapshot", "rollback evidence", "owner approval"]},
        "knownIssueMatcher": {"matchCount": len(matched), "matches": matched[:20], "patternCount": len(known_patterns)},
        "operationalMaturityScore": {"score": maturity_score, "components": maturity_components, "grade": "A" if maturity_score >= 85 else "B" if maturity_score >= 70 else "C"},
        "d365MigrationSignalDashboard": {"decision": "modernize-and-archive" if structural > tune else "tune-first", "structuralSignals": structural, "tuningSignals": tune, "message": "Use recurring growth/support-risk signals for D365 or archiving decisions; tune high-confidence operational issues first."},
    }


def generate_platform_extensions(evidence: str | Path, output_dir: str | Path | None = None, trend_db: str | Path | None = None, manifest: str | Path | None = None, state_file: str | Path | None = None) -> dict[str, Any]:
    findings = analyze_evidence(evidence)
    root = Path(evidence)
    out = Path(output_dir) if output_dir else root
    out.mkdir(parents=True, exist_ok=True)
    payload = {
        "trendDashboard": trend_dashboard(evidence, trend_db),
        "recommendationLifecycle": recommendation_lifecycle(findings, state_file or (out / "recommendation-lifecycle-state.json")),
        "incidentReplay": incident_replay_timeline(evidence, findings),
        "queryPlanDiff": query_plan_diff(evidence, trend_db),
        "deadlockGraph": deadlock_graph(evidence),
        "aosTopology": aos_topology(evidence),
        "schedulerHardening": scheduler_hardening(manifest, out),
        "productivePushReadiness": productive_push_readiness(evidence, findings),
        "xppAttribution": xpp_attribution(evidence, findings),
        "environmentDriftGuard": environment_drift_guard(evidence),
        "aiDecisionCockpit": ai_decision_cockpit(findings, evidence),
        "liveBatchCollisionWatch": live_batch_collision_watch(evidence),
        "batchRescheduleCalendar": batch_reschedule_calendar(evidence),
        "batchDependencyGraph": batch_dependency_graph(evidence),
        "sqlBlockingChainRecorder": sql_blocking_chain_recorder(evidence),
        "axBusinessProcessSla": ax_business_process_sla(findings),
        "evidenceGapAssistant": evidence_gap_assistant(evidence, findings),
        "deploymentRegressionGuard": deployment_regression_guard(evidence, trend_db),
        "adminRemediationWorkbench": admin_remediation_workbench(findings),
        "alertingRules": alerting_rules(findings, evidence),
        "aiSafeFeatures": ai_safe_features_bundle(evidence, findings, trend_db),
        "strategicUspPack": strategic_usp_pack(evidence, findings, trend_db),
    }
    payload["gapClosure"] = gap_closure(evidence, out, findings, trend_db, manifest)
    write_gap_closure_actions(out, payload["gapClosure"])
    write_json(out / "platform-extensions.json", payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AXPA platform extension artifacts.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--trend-db")
    parser.add_argument("--manifest")
    parser.add_argument("--state-file")
    args = parser.parse_args()
    payload = generate_platform_extensions(args.evidence, args.output_dir, args.trend_db, args.manifest, args.state_file)
    print(f"Wrote platform extensions with {len(payload)} sections to {Path(args.output_dir) / 'platform-extensions.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
