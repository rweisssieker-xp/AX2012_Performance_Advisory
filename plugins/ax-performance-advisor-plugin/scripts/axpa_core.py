from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import statistics
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SEVERITY_RANK = {
    "critical": 5,
    "high": 4,
    "medium": 3,
    "low": 2,
    "informational": 1,
}

MODULE_PATTERNS = [
    ("INVENT", "Inventory", "Supply Chain", "AX Operations", "AX-SCM"),
    ("CUST", "Finance", "Finance AR", "AX Operations", "AX-FIN"),
    ("VEND", "Finance", "Finance AP", "AX Operations", "AX-FIN"),
    ("LEDGER", "Finance", "Finance", "AX Operations", "AX-FIN"),
    ("MAINACCOUNT", "Finance", "Finance", "AX Operations", "AX-FIN"),
    ("DIMENSION", "Finance", "Finance", "AX Operations", "AX-FIN"),
    ("TAX", "Finance", "Tax/Finance", "AX Operations", "AX-FIN"),
    ("GENERALJOURNAL", "Finance", "Finance", "AX Operations", "AX-FIN"),
    ("SALES", "Sales", "Sales Operations", "AX Operations", "AX-SALES"),
    ("PURCH", "Purchasing", "Procurement", "AX Operations", "AX-PROC"),
    ("RETAIL", "Retail", "Retail Operations", "AX Retail Operations", "AX-RETAIL"),
    ("WMS", "Warehouse", "Warehouse Operations", "AX Operations", "AX-SCM"),
    ("WHS", "Warehouse", "Warehouse Operations", "AX Operations", "AX-SCM"),
    ("PROD", "Production", "Manufacturing", "AX Operations", "AX-MFG"),
    ("BOM", "Production", "Manufacturing", "AX Operations", "AX-MFG"),
    ("ROUTE", "Production", "Manufacturing", "AX Operations", "AX-MFG"),
    ("DIR", "Global Address Book", "Master Data", "AX Operations", "AX-MDM"),
    ("DOCU", "Document Management", "IT Operations", "AX Operations", "AX-OPS"),
    ("BATCH", "Batch", "IT Operations", "AX Operations", "AX-OPS"),
    ("CUSTOM", "Custom", "Owning Business Process", "AX Development", "AX-DEV"),
]

IGNORED_WAIT_TYPES = {
    "BROKER_EVENTHANDLER",
    "BROKER_RECEIVE_WAITFOR",
    "BROKER_TASK_STOP",
    "BROKER_TO_FLUSH",
    "BROKER_TRANSMITTER",
    "CHECKPOINT_QUEUE",
    "CLR_AUTO_EVENT",
    "CLR_MANUAL_EVENT",
    "DIRTY_PAGE_POLL",
    "DISPATCHER_QUEUE_SEMAPHORE",
    "FT_IFTS_SCHEDULER_IDLE_WAIT",
    "HADR_FILESTREAM_IOMGR_IOCOMPLETION",
    "KSOURCE_WAKEUP",
    "LAZYWRITER_SLEEP",
    "LOGMGR_QUEUE",
    "ONDEMAND_TASK_QUEUE",
    "PREEMPTIVE_XE_GETTARGETSTATE",
    "QDS_ASYNC_QUEUE",
    "QDS_CLEANUP_STALE_QUERIES_TASK_MAIN_LOOP_SLEEP",
    "QDS_PERSIST_TASK_MAIN_LOOP_SLEEP",
    "QDS_SHUTDOWN_QUEUE",
    "REQUEST_FOR_DEADLOCK_SEARCH",
    "SLEEP_BPOOL_FLUSH",
    "SLEEP_DBSTARTUP",
    "SLEEP_DCOMSTARTUP",
    "SLEEP_MASTERDBREADY",
    "SLEEP_MASTERMDREADY",
    "SLEEP_SYSTEMTASK",
    "SLEEP_TASK",
    "SLEEP_TEMPDBSTARTUP",
    "SP_SERVER_DIAGNOSTICS_SLEEP",
    "SQLTRACE_BUFFER_FLUSH",
    "WAITFOR",
    "XE_DISPATCHER_JOIN",
    "XE_DISPATCHER_WAIT",
    "XE_TIMER_EVENT",
}


def load_simple_yaml_list(path: Path, key: str) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    values: list[str] = []
    in_key = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{key}:"):
            in_key = True
            continue
        if in_key and stripped.startswith("- "):
            values.append(stripped[2:].strip())
        elif in_key and stripped and not stripped.startswith("#"):
            break
    return values


@dataclass
class Evidence:
    root: Path
    metadata: dict[str, Any]
    tables: dict[str, list[dict[str, Any]]]
    config: dict[str, Any]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def to_number(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    if text == "":
        return ""
    normalized = text
    if "," in normalized and "." not in normalized:
        normalized = normalized.replace(",", ".")
    try:
        if "." in normalized:
            return float(normalized)
        return int(normalized)
    except ValueError:
        return value


def read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [{key: to_number(value) for key, value in row.items()} for row in csv.DictReader(handle)]


def write_json(path: str | Path, payload: Any) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def load_config(root_path: Path) -> dict[str, Any]:
    config_path = root_path / "config.json"
    if config_path.exists():
        return read_json(config_path, {})
    env_config = os.environ.get("AXPA_CONFIG")
    if env_config and Path(env_config).exists():
        return read_json(Path(env_config), {})
    config: dict[str, Any] = {}
    rules_waits = load_simple_yaml_list(Path(__file__).resolve().parents[1] / "rules" / "wait_stats_rules.yml", "ignored_waits")
    if rules_waits:
        config["suppressedWaitTypes"] = rules_waits
    return config


def load_evidence(root: str | Path) -> Evidence:
    root_path = Path(root)
    tables = {}
    for name in [
        "sql_top_queries",
        "sql_wait_stats_delta",
        "sql_wait_stats",
        "blocking",
        "index_fragmentation",
        "missing_indexes",
        "statistics_age",
        "file_latency",
        "batch_jobs",
        "batch_history",
        "table_growth",
        "environment_drift",
        "ownership_map",
        "trace_parser",
        "dynamicsperf",
        "tempdb_usage",
        "plan_cache_variance",
        "query_store_runtime",
        "query_store_status",
        "deadlock_processes",
        "deadlocks",
        "plan_operators",
        "plan_xml_inventory",
        "aos_counters",
        "aif_services",
        "retail_load",
        "user_sessions",
        "batch_tasks",
        "source_status",
        "ax_schema_discovery",
    ]:
        tables[name] = read_csv(root_path / f"{name}.csv")
    return Evidence(root_path, read_json(root_path / "metadata.json", {}), tables, load_config(root_path))


def stable_id(parts: Iterable[Any]) -> str:
    digest = hashlib.sha1("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:8].upper()
    return f"AXPA-{digest}"


def object_token(name: str) -> str:
    return name.upper().replace("DBO.", "").replace("[", "").replace("]", "")


def owner_for_object(name: str, ownership_rows: list[dict[str, Any]] | None = None) -> dict[str, str]:
    token = object_token(name)
    rows = ownership_rows or []
    for row in rows:
        pattern = str(row.get("object_pattern", "")).upper()
        if pattern and pattern in token:
            return {
                "module": str(row.get("module", "Unknown")),
                "businessOwner": str(row.get("business_owner", "Unknown")),
                "technicalOwner": str(row.get("technical_owner", "Unknown")),
                "supportQueue": str(row.get("support_queue", "Unknown")),
            }
    for pattern, module, business, technical, queue in MODULE_PATTERNS:
        if pattern in token:
            return {
                "module": module,
                "businessOwner": business,
                "technicalOwner": technical,
                "supportQueue": queue,
            }
    return {
        "module": "Unknown",
        "businessOwner": "Unknown",
        "technicalOwner": "AX Operations",
        "supportQueue": "AX-OPS",
    }


def infer_object_from_sql(statement: str) -> str:
    text = str(statement or "")
    matches = re.findall(r"\b(?:FROM|JOIN|UPDATE|INTO)\s+((?:\[?[A-Za-z0-9_]+\]?\.)?\[?[A-Za-z0-9_]+\]?)", text, flags=re.IGNORECASE)
    for match in matches:
        cleaned = match.replace("[", "").replace("]", "")
        if cleaned and not cleaned.upper().startswith(("SYS.", "SYS")):
            return cleaned
    return ""


def plan_inventory_operator_rows(evidence: Evidence) -> list[dict[str, Any]]:
    rows = []
    for row in evidence.tables.get("plan_xml_inventory", []):
        plan = str(row.get("query_plan") or "")
        if not plan:
            continue
        query_hash = str(row.get("query_hash") or "")
        plan_hash = str(row.get("plan_hash") or "")
        checks = [
            ("Index Scan", "scan"),
            ("Table Scan", "scan"),
            ("Key Lookup", "key-lookup"),
            ("RID Lookup", "key-lookup"),
            ("Sort", "sort"),
            ("Hash Match", "hash-match"),
            ("Parallelism", "parallelism"),
            ("SpillToTempDb", "spill-to-tempdb"),
            ("MissingIndexes", "missing-index"),
        ]
        for token, warning in checks:
            count = plan.count(token)
            if count:
                rows.append({
                    "source_file": "plan_xml_inventory.csv",
                    "query_hash": query_hash,
                    "plan_hash": plan_hash,
                    "physical_op": token,
                    "logical_op": token,
                    "estimate_rows": "",
                    "estimated_cost": row.get("total_duration_ms", ""),
                    "warnings": warning,
                    "operator_count": count,
                })
    return rows


def mk_finding(
    evidence: Evidence,
    title: str,
    severity: str,
    confidence: str,
    classification: str,
    object_name: str,
    summary: str,
    source: str,
    metric: str,
    value: Any,
    threshold: Any,
    likely_cause: str,
    playbook: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ownership = owner_for_object(object_name, evidence.tables.get("ownership_map"))
    metadata = evidence.metadata
    window = metadata.get("timeWindow", {})
    finding = {
        "id": stable_id([title, object_name, source, metric]),
        "title": title,
        "severity": severity,
        "confidence": confidence,
        "classification": classification,
        "timeWindow": {
            "start": window.get("start", ""),
            "end": window.get("end", ""),
        },
        "businessImpact": {
            "process": ownership["module"],
            "impact": summary,
            "usersAffected": "Requires validation with AX session and process-owner evidence.",
            "module": ownership["module"],
        },
        "evidence": [
            {
                "source": source,
                "metric": metric,
                "value": value,
                "threshold": threshold,
            }
        ],
        "axContext": {
            "tables": [object_name] if object_name else [],
            "classes": [],
            "customObjects": [],
            "batchJobs": [],
            "aos": [],
            "companies": [],
            "module": ownership["module"],
            "businessOwner": ownership["businessOwner"],
            "technicalOwner": ownership["technicalOwner"],
            "supportQueue": ownership["supportQueue"],
        },
        "sqlContext": {
            "queryHash": "",
            "planHash": "",
            "waitTypes": [],
            "objects": [object_name] if object_name else [],
        },
        "likelyCause": likely_cause,
        "recommendation": {
            "summary": summary,
            "owner": ownership["technicalOwner"],
            "requiresApproval": True,
            "mode": "advisory",
            "playbook": playbook,
        },
        "changeReadiness": {
            "benefit": "medium",
            "technicalRisk": "medium",
            "axCompatibilityRisk": "medium",
            "testEffort": "medium",
            "downtimeRisk": "low",
            "rollbackComplexity": "medium",
            "approvalPath": "CAB" if severity in {"critical", "high"} else "Operations approval",
        },
        "validation": {
            "successMetric": f"Reduce {metric} below the observed baseline or agreed threshold.",
            "baselineWindow": "Use current evidence window plus previous comparable runs.",
            "postChangeWindow": "Use at least one comparable business cycle after implementation.",
            "rollback": "Revert the approved operational/configuration/schema change through change control.",
        },
        "performanceDebt": {
            "isDebt": severity in {"critical", "high"},
            "firstSeen": window.get("start", ""),
            "recurrenceCount": 1,
            "ageDays": 0,
            "defermentReason": "",
            "nextDecision": "Assign owner and approve, defer, or reject the recommendation.",
        },
        "prediction": {
            "slaBreachHorizonDays": None,
            "trendConfidence": "unknown",
            "capacitySignal": "",
        },
        "environmentDrift": {
            "productionOnly": False,
            "suspectedDifferences": [],
        },
        "dataGrowth": {
            "isGrowthDriven": False,
            "table": object_name,
            "growthSignal": "",
            "archiveCandidate": False,
        },
        "regression": {
            "relatedChange": "",
            "status": "not-evaluated",
            "baselineDelta": "",
        },
        "status": "proposed",
        "audit": {
            "analysisTimestamp": now_iso(),
            "evidenceRoot": str(evidence.root),
            "analysisVersion": metadata.get("analysisVersion", "0.1.0"),
        },
    }
    if extra:
        deep_update(finding, extra)
    return finding


def deep_update(target: dict[str, Any], patch: dict[str, Any]) -> None:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            deep_update(target[key], value)
        else:
            target[key] = value


def analyze_evidence(root: str | Path) -> list[dict[str, Any]]:
    evidence = load_evidence(root)
    findings: list[dict[str, Any]] = []
    findings.extend(analyze_top_queries(evidence))
    findings.extend(analyze_waits(evidence))
    findings.extend(analyze_blocking(evidence))
    findings.extend(analyze_missing_indexes(evidence))
    findings.extend(analyze_statistics(evidence))
    findings.extend(analyze_file_latency(evidence))
    findings.extend(analyze_tempdb(evidence))
    findings.extend(analyze_plan_cache_variance(evidence))
    findings.extend(analyze_query_store(evidence))
    findings.extend(analyze_deadlocks(evidence))
    findings.extend(analyze_plan_operators(evidence))
    findings.extend(analyze_batch_jobs(evidence))
    findings.extend(analyze_aos_counters(evidence))
    findings.extend(analyze_aif_services(evidence))
    findings.extend(analyze_retail_load(evidence))
    findings.extend(analyze_user_sessions(evidence))
    findings.extend(analyze_data_growth(evidence))
    findings.extend(analyze_environment_drift(evidence))
    findings.extend(analyze_deployment_regressions(evidence, findings))
    findings = deduplicate_findings(findings)
    max_findings = int(evidence.config.get("maxFindings") or 0)
    sorted_findings = sorted(
        findings,
        key=lambda item: (
            -SEVERITY_RANK.get(item["severity"], 0),
            item["classification"],
            item["axContext"].get("module", ""),
            item["title"],
        ),
    )
    return sorted_findings[:max_findings] if max_findings > 0 else sorted_findings


def deduplicate_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in findings:
        obj = ",".join(item.get("sqlContext", {}).get("objects", []) or item.get("axContext", {}).get("tables", []))
        key = (item.get("classification", ""), item.get("recommendation", {}).get("playbook", ""), obj or item["title"])
        current = best.get(key)
        if current is None or SEVERITY_RANK.get(item["severity"], 0) > SEVERITY_RANK.get(current["severity"], 0):
            best[key] = item
        elif current is not None:
            current["performanceDebt"]["recurrenceCount"] = int(current["performanceDebt"].get("recurrenceCount") or 1) + 1
    return list(best.values())


def analyze_top_queries(evidence: Evidence) -> list[dict[str, Any]]:
    findings = []
    for row in evidence.tables["sql_top_queries"]:
        reads = float(row.get("total_logical_reads") or 0)
        duration = float(row.get("avg_duration_ms") or 0)
        object_name = str(row.get("object_name") or "") or infer_object_from_sql(str(row.get("statement_text") or ""))
        if reads >= 50_000_000 or duration >= 30_000:
            severity = "high" if reads >= 100_000_000 or duration >= 45_000 else "medium"
            extra = {
                "sqlContext": {
                    "queryHash": str(row.get("query_hash", "")),
                    "planHash": str(row.get("plan_hash", "")),
                    "objects": [object_name],
                }
            }
            if "CUSTOM" in str(row.get("statement_text", "")).upper() or "CUSTOM" in object_token(object_name):
                classification = "custom-code-hotspot"
                playbook = "custom-code-hotspot"
            else:
                classification = "tune-now"
                playbook = "missing-composite-index-candidate"
            findings.append(
                mk_finding(
                    evidence,
                    f"High-cost query on {object_name}",
                    severity,
                    "medium",
                    classification,
                    object_name,
                    "Review query pattern, AX call context, statistics, and index coverage before proposing change.",
                    "sql_top_queries",
                    "total_logical_reads",
                    reads,
                    50_000_000,
                    "High logical reads or long duration indicate scan pressure, poor selectivity, stale statistics, or missing index coverage.",
                    playbook,
                    extra,
                )
            )
    return findings


def analyze_waits(evidence: Evidence) -> list[dict[str, Any]]:
    findings = []
    wait_rows = evidence.tables["sql_wait_stats_delta"] or evidence.tables["sql_wait_stats"]
    suppressed = {str(item).upper() for item in evidence.config.get("suppressedWaitTypes", [])}
    threshold = float(evidence.config.get("thresholds", {}).get("waitMs", 60_000))
    for row in wait_rows:
        wait_type = str(row.get("wait_type") or "")
        if wait_type.upper() in IGNORED_WAIT_TYPES or wait_type.upper() in suppressed:
            continue
        wait_ms = float(row.get("wait_time_ms") or 0)
        if wait_ms < threshold:
            continue
        if wait_type.startswith("PAGEIOLATCH"):
            title = "High data-file read latency wait profile"
            cause = "PAGEIOLATCH waits indicate storage latency or read-heavy query pressure."
            playbook = "data-growth"
        elif wait_type.startswith("LCK"):
            title = "High locking wait profile"
            cause = "Lock waits indicate blocking chains or long-running transactions."
            playbook = "blocking-chain"
        else:
            title = f"Elevated SQL wait profile: {wait_type}"
            cause = "Wait profile exceeds advisory threshold and needs workload correlation."
            playbook = "sql-wait-analysis"
        findings.append(
            mk_finding(
                evidence,
                title,
                "high" if wait_ms >= 90_000 else "medium",
                "medium",
                "tune-now",
                "",
                "Correlate wait spike with top queries, batch jobs, file latency, and business window.",
                "sql_wait_stats",
                wait_type,
                wait_ms,
                threshold,
                cause,
                playbook,
                {"sqlContext": {"waitTypes": [wait_type]}},
            )
        )
    return findings


def analyze_blocking(evidence: Evidence) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in evidence.tables["blocking"]:
        grouped.setdefault(str(row.get("blocking_session_id", "")), []).append(row)
    findings = []
    for blocker, rows in grouped.items():
        max_wait = max(float(row.get("wait_time_ms") or 0) for row in rows)
        object_name = str(rows[0].get("object_name") or "")
        if max_wait >= 120_000:
            findings.append(
                mk_finding(
                    evidence,
                    f"Blocking chain rooted at session {blocker}",
                    "high",
                    "high",
                    "tune-now",
                    object_name,
                    "Identify AX process behind root blocker and reduce overlap or transaction duration.",
                    "blocking",
                    "max_blocked_wait_ms",
                    max_wait,
                    120_000,
                    "Repeated or long blocking suggests conflicting batch/user transactions or long transaction scope.",
                    "blocking-chain",
                    {"sqlContext": {"waitTypes": list({str(row.get("wait_type")) for row in rows})}},
                )
            )
    return findings


def analyze_missing_indexes(evidence: Evidence) -> list[dict[str, Any]]:
    findings = []
    for row in evidence.tables["missing_indexes"]:
        impact = float(row.get("avg_user_impact") or 0)
        seeks = float(row.get("user_seeks") or 0)
        object_name = str(row.get("object_name") or "")
        if impact >= 70 and seeks >= 25:
            findings.append(
                mk_finding(
                    evidence,
                    f"Risk-based index candidate on {object_name}",
                    "medium",
                    "medium",
                    "tune-now",
                    object_name,
                    "Treat missing-index DMV output as a review candidate and validate against AX keys, write overhead, and existing indexes.",
                    "missing_indexes",
                    "avg_user_impact",
                    impact,
                    70,
                    "Missing-index signal with repeated seeks may indicate absent composite coverage for an AX query pattern.",
                    "missing-composite-index-candidate",
                    {
                        "recommendation": {
                            "candidateIndex": {
                                "equalityColumns": row.get("equality_columns", ""),
                                "inequalityColumns": row.get("inequality_columns", ""),
                                "includedColumns": row.get("included_columns", ""),
                            }
                        }
                    },
                )
            )
    return findings


def analyze_statistics(evidence: Evidence) -> list[dict[str, Any]]:
    findings = []
    for row in evidence.tables["statistics_age"]:
        rows = float(row.get("rows") or 0)
        mods = float(row.get("modification_counter") or 0)
        mod_pct = (mods / rows * 100) if rows else 0
        object_name = str(row.get("object_name") or "")
        if mod_pct >= 10:
            findings.append(
                mk_finding(
                    evidence,
                    f"Stale statistics candidate on {object_name}",
                    "medium",
                    "high",
                    "tune-now",
                    object_name,
                    "Review and update targeted statistics in an approved maintenance window.",
                    "statistics_age",
                    "modification_percent",
                    round(mod_pct, 2),
                    10,
                    "High modification ratio can drive cardinality errors and unstable plans.",
                    "stale-statistics",
                )
            )
    return findings


def analyze_file_latency(evidence: Evidence) -> list[dict[str, Any]]:
    findings = []
    for row in evidence.tables["file_latency"]:
        reads = float(row.get("num_of_reads") or 0)
        read_ms = float(row.get("io_stall_read_ms") or 0)
        writes = float(row.get("num_of_writes") or 0)
        write_ms = float(row.get("io_stall_write_ms") or 0)
        avg_read = read_ms / reads if reads else 0
        avg_write = write_ms / writes if writes else 0
        object_name = str(row.get("database_name") or "")
        if avg_read >= 15 or avg_write >= 15:
            findings.append(
                mk_finding(
                    evidence,
                    f"High file I/O latency on {row.get('file_logical_name')}",
                    "high" if max(avg_read, avg_write) >= 20 else "medium",
                    "medium",
                    "capacity-planning-signal",
                    object_name,
                    "Validate storage latency, file layout, concurrent workload, and maintenance overlap.",
                    "file_latency",
                    "max_avg_io_latency_ms",
                    round(max(avg_read, avg_write), 2),
                    15,
                    "Database file latency can amplify AX query and batch runtimes.",
                    "capacity-planning",
                )
            )
    return findings


def analyze_tempdb(evidence: Evidence) -> list[dict[str, Any]]:
    findings = []
    for row in evidence.tables["tempdb_usage"]:
        internal_kb = float(row.get("internal_object_kb") or 0)
        version_kb = float(row.get("version_store_kb") or 0)
        total_mb = (internal_kb + version_kb) / 1024
        if total_mb >= 1024:
            findings.append(
                mk_finding(
                    evidence,
                    "TempDB pressure detected",
                    "high" if total_mb >= 10240 else "medium",
                    "medium",
                    "capacity-planning-signal",
                    "tempdb",
                    "Review sort/hash spills, version store growth, batch/report overlap, and TempDB file layout.",
                    "tempdb_usage",
                    "internal_and_version_store_mb",
                    round(total_mb, 2),
                    1024,
                    "High TempDB internal object or version-store usage can amplify AX batch and reporting runtimes.",
                    "tempdb-pressure",
                )
            )
    return findings


def analyze_plan_cache_variance(evidence: Evidence) -> list[dict[str, Any]]:
    findings = []
    for row in evidence.tables["plan_cache_variance"]:
        plan_count = float(row.get("plan_count") or 0)
        min_ms = float(row.get("min_avg_duration_ms") or 0)
        max_ms = float(row.get("max_avg_duration_ms") or 0)
        ratio = (max_ms / min_ms) if min_ms else 0
        if plan_count > 1 or ratio >= 5:
            findings.append(
                mk_finding(
                    evidence,
                    f"Parameter-sensitive plan candidate {row.get('query_hash')}",
                    "high" if ratio >= 10 else "medium",
                    "medium",
                    "tune-now",
                    "",
                    f"Compare {int(plan_count)} cached plans, duration range {round(min_ms, 2)}-{round(max_ms, 2)} ms, parameter skew, company/date/item selectivity, and statistics before forcing plans.",
                    "plan_cache_variance",
                    "duration_variance_ratio",
                    round(ratio, 2),
                    5,
                    "Multiple plans or strong duration variance may indicate parameter-sensitive execution behavior.",
                    "parameter-sensitive-plan",
                    {"sqlContext": {"queryHash": str(row.get("query_hash", "")), "planHash": str(row.get("plan_hash", ""))}, "validation": {"successMetric": "For the same query_hash, reduce duration/read variance and avoid new high-cost plans."}},
                )
            )
    return findings


def analyze_query_store(evidence: Evidence) -> list[dict[str, Any]]:
    findings = []
    if not evidence.tables["query_store_runtime"]:
        for row in evidence.tables.get("query_store_status", []):
            state = str(row.get("actual_state_desc") or "")
            size = float(row.get("current_storage_size_mb") or 0)
            if state and state != "READ_WRITE":
                findings.append(
                    mk_finding(
                        evidence,
                        f"Query Store is {state}",
                        "medium",
                        "high",
                        "evidence-gap",
                        str(row.get("database_name") or ""),
                        "Query Store is not providing writable runtime history for regression validation; decide whether to enable/adjust it under DBA change control.",
                        "query_store_status",
                        "actual_state_desc",
                        state,
                        "READ_WRITE",
                        "Query Store status limits before/after regression proof.",
                        "deployment-regression",
                    )
                )
            elif state == "READ_WRITE" and size == 0:
                findings.append(
                    mk_finding(
                        evidence,
                        "Query Store enabled but no runtime rows collected",
                        "low",
                        "medium",
                        "evidence-gap",
                        str(row.get("database_name") or ""),
                        "Confirm capture mode, workload timing, and permissions before relying on Query Store history.",
                        "query_store_status",
                        "current_storage_size_mb",
                        size,
                        "> 0",
                        "Query Store may be enabled but lacks relevant data for the current evidence window.",
                        "deployment-regression",
                    )
                )
    for row in evidence.tables["query_store_runtime"]:
        duration = float(row.get("avg_duration_ms") or 0)
        reads = float(row.get("avg_logical_io_reads") or 0)
        if duration >= 30_000 or reads >= 1_000_000:
            findings.append(
                mk_finding(
                    evidence,
                    f"Query Store high-runtime query {row.get('query_id')}",
                    "high" if duration >= 60_000 else "medium",
                    "high",
                    "tune-now",
                    "",
                    "Use Query Store history to validate regression, plan choice, and before/after effect.",
                    "query_store_runtime",
                    "avg_duration_ms",
                    duration,
                    30_000,
                    "Query Store shows sustained high runtime or logical I/O.",
                    "deployment-regression",
                    {"sqlContext": {"queryHash": str(row.get("query_id", "")), "planHash": str(row.get("plan_id", ""))}},
                )
            )
    return findings


def analyze_deadlocks(evidence: Evidence) -> list[dict[str, Any]]:
    rows = evidence.tables["deadlock_processes"]
    if not rows:
        return []
    resources = sorted({str(row.get("waitresource", "")) for row in rows if row.get("waitresource")})
    return [
        mk_finding(
            evidence,
            "Deadlock evidence detected",
            "high",
            "high",
            "tune-now",
            "",
            "Map deadlock processes to AX classes/users and reduce conflicting transaction overlap.",
            "deadlock_processes",
            "deadlock_process_count",
            len(rows),
            1,
            "Deadlocks indicate incompatible concurrent transaction patterns.",
            "blocking-chain",
            {"sqlContext": {"waitTypes": ["DEADLOCK"], "objects": resources[:10]}},
        )
    ]


def analyze_plan_operators(evidence: Evidence) -> list[dict[str, Any]]:
    findings = []
    operator_rows = evidence.tables["plan_operators"] + plan_inventory_operator_rows(evidence)
    warning_rows = [row for row in operator_rows if str(row.get("warnings", ""))]
    spill_count = sum(1 for row in warning_rows if "spill-to-tempdb" in str(row.get("warnings", "")))
    missing_count = sum(1 for row in warning_rows if "missing-index" in str(row.get("warnings", "")))
    scan_count = sum(int(row.get("operator_count") or 1) for row in warning_rows if "scan" in str(row.get("warnings", "")))
    lookup_count = sum(int(row.get("operator_count") or 1) for row in warning_rows if "key-lookup" in str(row.get("warnings", "")))
    parallel_count = sum(int(row.get("operator_count") or 1) for row in warning_rows if "parallelism" in str(row.get("warnings", "")))
    if spill_count:
        findings.append(
            mk_finding(
                evidence,
                "Execution plan spill to TempDB detected",
                "medium",
                "medium",
                "tune-now",
                "tempdb",
                "Review spilling operators, memory grants, statistics, and query shape.",
                "plan_operators",
                "spill_operator_count",
                spill_count,
                1,
                "Sort/hash spills indicate memory grant, cardinality, or query-shape pressure.",
                "tempdb-pressure",
            )
        )
    if missing_count:
        findings.append(
            mk_finding(
                evidence,
                "Execution plan missing-index warning detected",
                "medium",
                "medium",
                "tune-now",
                "",
                "Validate plan warning against existing AX indexes and write overhead.",
                "plan_operators",
                "missing_index_warning_count",
                missing_count,
                1,
                "Plan-level missing index warnings can support an index review candidate.",
                "missing-composite-index-candidate",
            )
        )
    if scan_count or lookup_count:
        findings.append(
            mk_finding(
                evidence,
                "Execution plan scan/lookup pressure detected",
                "medium",
                "medium",
                "tune-now",
                "",
                "Review table scans and key lookups against AX index patterns, statistics, and query predicates.",
                "plan_xml_inventory",
                "scan_lookup_operator_count",
                scan_count + lookup_count,
                1,
                "Scans and key lookups in top cached plans can explain high reads even without Trace Parser evidence.",
                "missing-composite-index-candidate",
            )
        )
    if parallel_count:
        findings.append(
            mk_finding(
                evidence,
                "Execution plan parallelism hotspots detected",
                "low",
                "medium",
                "tune-now",
                "",
                "Review parallel plan candidates with waits, cost threshold, MAXDOP policy, and query shape before changing SQL settings.",
                "plan_xml_inventory",
                "parallel_operator_count",
                parallel_count,
                1,
                "Parallel operators in top plans can be normal, but combined with CX waits or high duration they need review.",
                "sql-wait-analysis",
            )
        )
    return findings


def analyze_batch_jobs(evidence: Evidence) -> list[dict[str, Any]]:
    findings = []
    history_by_job: dict[str, list[dict[str, Any]]] = {}
    for row in evidence.tables["batch_history"]:
        history_by_job.setdefault(str(row.get("job_name", "")), []).append(row)
    for row in evidence.tables["batch_jobs"]:
        duration = float(row.get("duration_seconds") or 0)
        target = float(row.get("sla_target_seconds") or 0)
        job_name = str(row.get("job_name") or "")
        class_name = str(row.get("class_name") or "")
        object_name = class_name or job_name
        if target and duration >= target * 0.9:
            breach = duration > target
            history = history_by_job.get(job_name, [])
            horizon = estimate_breach_horizon(history)
            findings.append(
                mk_finding(
                    evidence,
                    f"Batch SLA risk: {job_name}",
                    "high" if breach else "medium",
                    "high" if history else "medium",
                    "custom-code-hotspot" if "CUSTOM" in object_token(class_name) else "tune-now",
                    object_name,
                    "Review batch schedule, AOS assignment, overlap, data growth, and SQL pressure in the same window.",
                    "batch_jobs",
                    "duration_seconds",
                    duration,
                    target,
                    "Batch duration is close to or above the target window.",
                    "batch-collision-and-read-pressure",
                    {
                        "axContext": {
                            "classes": [class_name],
                            "batchJobs": [job_name],
                            "aos": [str(row.get("aos", ""))],
                            "companies": [str(row.get("company", ""))],
                        },
                        "prediction": horizon,
                    },
                )
            )
    return findings


def estimate_breach_horizon(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if len(rows) < 3:
        return {"slaBreachHorizonDays": None, "trendConfidence": "low", "capacitySignal": "insufficient-history"}
    ordered = sorted(rows, key=lambda row: str(row.get("run_date", "")))
    durations = [float(row.get("duration_seconds") or 0) for row in ordered]
    target = float(ordered[-1].get("sla_target_seconds") or 0)
    diffs = [durations[i] - durations[i - 1] for i in range(1, len(durations))]
    avg_growth = statistics.mean(diffs) if diffs else 0
    remaining = target - durations[-1]
    if target <= 0:
        horizon = None
        signal = "no-sla-target"
    elif durations[-1] >= target:
        horizon = 0
        signal = "sla-already-breached"
    elif avg_growth > 0:
        horizon = max(0, math.ceil((remaining / avg_growth) * 7))
        signal = "batch-window-saturation"
    else:
        horizon = None
        signal = "stable-or-improving"
    return {
        "slaBreachHorizonDays": horizon,
        "trendConfidence": "medium" if len(rows) >= 5 else "low",
        "capacitySignal": signal,
    }


def analyze_aos_counters(evidence: Evidence) -> list[dict[str, Any]]:
    findings = []
    for row in evidence.tables["aos_counters"]:
        path = str(row.get("Path") or row.get("path") or "")
        value = float(row.get("CookedValue") or row.get("cooked_value") or 0)
        if "% Processor Time" in path and value >= 85:
            metric = "processor_percent"
            threshold = 85
        elif "Avg. Disk sec/Read" in path and value >= 0.02:
            metric = "disk_read_seconds"
            threshold = 0.02
        elif "Avg. Disk sec/Write" in path and value >= 0.02:
            metric = "disk_write_seconds"
            threshold = 0.02
        else:
            continue
        findings.append(
            mk_finding(
                evidence,
                f"AOS/server counter pressure: {path}",
                "high" if value >= threshold * 2 else "medium",
                "medium",
                "capacity-planning-signal",
                "AOS",
                "Correlate counter pressure with AOS assignment, user sessions, batch jobs, and SQL waits.",
                "aos_counters",
                metric,
                value,
                threshold,
                "Server-side pressure can explain AX response time or batch runtime degradation.",
                "capacity-planning",
            )
        )
    return findings


def analyze_aif_services(evidence: Evidence) -> list[dict[str, Any]]:
    findings = []
    rows = evidence.tables["aif_services"]
    failed = [row for row in rows if str(row.get("status", "")).lower() not in {"", "ended", "success", "processed", "0"}]
    slow = [row for row in rows if float(row.get("duration_seconds") or 0) >= 600]
    if failed or slow:
        findings.append(
            mk_finding(
                evidence,
                "AIF/service processing risk detected",
                "medium",
                "medium",
                "tune-now",
                "AIF",
                "Review failed or slow AIF/service messages and correlate with SQL waits and batch windows.",
                "aif_services",
                "slow_or_failed_messages",
                len(failed) + len(slow),
                1,
                "Slow or failed integration messages can collide with AX batch and user workload.",
                "integration-load",
            )
        )
    return findings


def analyze_retail_load(evidence: Evidence) -> list[dict[str, Any]]:
    findings = []
    for row in evidence.tables["retail_load"]:
        count = float(row.get("transaction_count") or 0)
        if count >= 100_000:
            findings.append(
                mk_finding(
                    evidence,
                    f"High retail transaction load for store {row.get('store')}",
                    "medium",
                    "medium",
                    "capacity-planning-signal",
                    "RETAILTRANSACTIONTABLE",
                    "Validate retail posting schedule, channel sync, and table growth pressure.",
                    "retail_load",
                    "transaction_count",
                    count,
                    100_000,
                    "High retail volume can pressure statement posting, integrations, and transaction tables.",
                    "data-growth",
                )
            )
    return findings


def analyze_user_sessions(evidence: Evidence) -> list[dict[str, Any]]:
    rows = evidence.tables["user_sessions"]
    active = [row for row in rows if str(row.get("status", "")).lower() in {"active", "1", "running"}]
    if len(active) < 200:
        return []
    return [
        mk_finding(
            evidence,
            "High AX user session load",
            "medium",
            "medium",
            "capacity-planning-signal",
            "AOS",
            "Correlate session load with AOS counters, user roles, and SQL pressure before batch scheduling changes.",
            "user_sessions",
            "active_session_count",
            len(active),
            200,
            "High concurrent session load can reduce available headroom for batch and integrations.",
            "capacity-planning",
        )
    ]


def analyze_data_growth(evidence: Evidence) -> list[dict[str, Any]]:
    findings = []
    for row in evidence.tables["table_growth"]:
        growth_pct = float(row.get("growth_pct_30d") or 0)
        closed_pct = float(row.get("closed_record_pct") or 0)
        object_name = str(row.get("object_name") or "")
        if growth_pct >= 15 or closed_pct >= 80:
            archive = closed_pct >= 80
            findings.append(
                mk_finding(
                    evidence,
                    f"Data growth pressure on {object_name}",
                    "medium",
                    "medium",
                    "archive-candidate" if archive else "capacity-planning-signal",
                    object_name,
                    "Review retention, archive, cleanup, reporting impact, and data lifecycle options.",
                    "table_growth",
                    "growth_pct_30d",
                    growth_pct,
                    15,
                    "Data volume is likely contributing to runtime, maintenance, backup, or scan pressure.",
                    "data-growth",
                    {
                        "dataGrowth": {
                            "isGrowthDriven": True,
                            "table": object_name,
                            "growthSignal": f"{growth_pct}% row growth in 30 days; {closed_pct}% closed/history records.",
                            "archiveCandidate": archive,
                        }
                    },
                )
            )
    return findings


def analyze_environment_drift(evidence: Evidence) -> list[dict[str, Any]]:
    high_rows = [row for row in evidence.tables["environment_drift"] if str(row.get("severity", "")).lower() in {"high", "medium"}]
    if not high_rows:
        return []
    differences = [f"{row.get('area')}:{row.get('name')}" for row in high_rows]
    return [
        mk_finding(
            evidence,
            "Environment drift may explain production-only performance",
            "high" if any(str(row.get("severity")).lower() == "high" for row in high_rows) else "medium",
            "medium",
            "redesign-needed",
            "",
            "Compare production and non-production settings, data volume, statistics, batch setup, and maintenance before relying on test-only results.",
            "environment_drift",
            "drift_count",
            len(high_rows),
            1,
            "Differences between environments can make performance issues non-reproducible outside production.",
            "environment-drift",
            {"environmentDrift": {"productionOnly": True, "suspectedDifferences": differences}},
        )
    ]


def analyze_deployment_regressions(evidence: Evidence, findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    changes = evidence.metadata.get("changes", [])
    if not changes:
        return []
    high_after_change = [finding for finding in findings if finding["severity"] in {"critical", "high"}]
    if not high_after_change:
        return []
    latest = changes[-1]
    return [
        mk_finding(
            evidence,
            "Deployment regression requires validation",
            "medium",
            "low",
            "redesign-needed",
            "",
            "Run a before/after comparison around the listed change and validate whether high-severity findings regressed after deployment.",
            "metadata.changes",
            "high_findings_after_change",
            len(high_after_change),
            1,
            "Recent deployment or configuration changes may correlate with current performance findings.",
            "deployment-regression",
            {
                "regression": {
                    "relatedChange": latest.get("id", latest.get("description", "")),
                    "status": "requires-validation",
                    "baselineDelta": "Run compare_baseline.py with comparable pre-change evidence.",
                }
            },
        )
    ]


def build_report(root: str | Path, findings: list[dict[str, Any]] | None = None) -> str:
    evidence = load_evidence(root)
    findings = findings if findings is not None else analyze_evidence(root)
    root_causes = summarize_root_causes(findings)
    scores = module_health_scores(findings)
    lines = [
        "# AX Performance Advisor Report",
        "",
        f"Environment: {evidence.config.get('environment') or evidence.metadata.get('environment', 'Unknown')}",
        f"Generated: {now_iso()}",
        "",
        "## Executive Summary",
        "",
        f"- Total findings: {len(findings)}",
        f"- Critical/high findings: {sum(1 for item in findings if item['severity'] in {'critical', 'high'})}",
        f"- Performance debt items: {sum(1 for item in findings if item.get('performanceDebt', {}).get('isDebt'))}",
        f"- SLA risks: {sum(1 for item in findings if item.get('prediction', {}).get('slaBreachHorizonDays') is not None)}",
        "",
        "## Module Health Scores",
        "",
    ]
    for module, score in scores.items():
        lines.append(f"- {module}: {score['score']} ({score['risk']}) - {score['findings']} findings")
    lines.extend([
        "",
        "## Top Root Causes",
        "",
    ])
    for cause in root_causes[:10]:
        lines.append(f"- {cause['classification']} / {cause['playbook']} / {cause['module']}: {cause['count']} findings, highest severity {cause['highestSeverity']}")
    lines.extend([
        "",
        "## Top Findings",
        "",
    ])
    for finding in findings[:20]:
        lines.extend(
            [
                f"### {finding['id']} - {finding['title']}",
                "",
                f"- Severity: {finding['severity']}",
                f"- Confidence: {finding['confidence']}",
                f"- Classification: {finding['classification']}",
                f"- Module: {finding['axContext'].get('module', 'Unknown')}",
                f"- Owner: {finding['axContext'].get('technicalOwner', 'Unknown')}",
                f"- Impact: {finding['businessImpact'].get('impact', '')}",
                f"- Likely cause: {finding.get('likelyCause', '')}",
                f"- Recommendation: {finding['recommendation'].get('summary', '')}",
                f"- Playbook: {finding['recommendation'].get('playbook', '')}",
                f"- Validation: {finding['validation'].get('successMetric', '')}",
                "",
            ]
        )
    lines.extend(["## Evidence Sources", ""])
    for name, rows in evidence.tables.items():
        if rows:
            lines.append(f"- {name}: {len(rows)} rows")
    lines.append("")
    return "\n".join(lines)


def summarize_root_causes(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in findings:
        key = (
            item.get("classification", ""),
            item.get("recommendation", {}).get("playbook", ""),
            item.get("axContext", {}).get("module", "Unknown"),
        )
        group = groups.setdefault(
            key,
            {
                "classification": key[0],
                "playbook": key[1],
                "module": key[2],
                "count": 0,
                "highestSeverity": "informational",
                "rank": 0,
            },
        )
        group["count"] += 1
        rank = SEVERITY_RANK.get(item["severity"], 0)
        if rank > group["rank"]:
            group["rank"] = rank
            group["highestSeverity"] = item["severity"]
    return sorted(groups.values(), key=lambda row: (-row["rank"], -row["count"], row["classification"]))


def module_health_scores(findings: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    modules: dict[str, dict[str, Any]] = {}
    for item in findings:
        module = item.get("axContext", {}).get("module", "Unknown")
        bucket = modules.setdefault(module, {"riskPoints": 0, "findings": 0})
        bucket["riskPoints"] += SEVERITY_RANK.get(item["severity"], 0)
        bucket["findings"] += 1
    scores = {}
    for module, bucket in modules.items():
        score = max(0, 100 - min(100, bucket["riskPoints"] * 3))
        if score >= 80:
            risk = "green"
        elif score >= 60:
            risk = "amber"
        else:
            risk = "red"
        scores[module] = {"score": score, "risk": risk, "findings": bucket["findings"]}
    return dict(sorted(scores.items(), key=lambda item: item[1]["score"]))


def export_evidence_pack(root: str | Path, output: str | Path) -> Path:
    root_path = Path(root)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() != ".zip":
        output_path = output_path.with_suffix(".zip")
    findings = analyze_evidence(root_path)
    temp_findings = root_path / "findings.generated.json"
    write_json(temp_findings, findings)
    try:
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in root_path.rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(root_path))
    finally:
        temp_findings.unlink(missing_ok=True)
    return output_path


def export_powerbi_dataset(root: str | Path, output: str | Path) -> Path:
    findings = analyze_evidence(root)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for finding in findings:
        rows.append(
            {
                "id": finding["id"],
                "title": finding["title"],
                "severity": finding["severity"],
                "classification": finding["classification"],
                "module": finding["axContext"].get("module", "Unknown"),
                "businessOwner": finding["axContext"].get("businessOwner", "Unknown"),
                "technicalOwner": finding["axContext"].get("technicalOwner", "Unknown"),
                "isDebt": finding.get("performanceDebt", {}).get("isDebt", False),
                "slaBreachHorizonDays": finding.get("prediction", {}).get("slaBreachHorizonDays"),
                "status": finding["status"],
            }
        )
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else ["id"])
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def query_families(root: str | Path) -> list[dict[str, Any]]:
    evidence = load_evidence(root)
    families: dict[str, dict[str, Any]] = {}
    for row in evidence.tables["sql_top_queries"]:
        object_name = str(row.get("object_name") or "unknown")
        statement = str(row.get("statement_text") or "")
        family_key = f"{object_name}:{statement[:80].upper()}"
        item = families.setdefault(
            family_key,
            {
                "family": stable_id([family_key]),
                "object": object_name,
                "queryCount": 0,
                "totalReads": 0,
                "totalCpuMs": 0,
                "totalDurationMs": 0,
                "executionCount": 0,
                "module": owner_for_object(object_name, evidence.tables.get("ownership_map"))["module"],
            },
        )
        item["queryCount"] += 1
        item["totalReads"] += float(row.get("total_logical_reads") or 0)
        item["totalCpuMs"] += float(row.get("total_cpu_ms") or 0)
        item["totalDurationMs"] += float(row.get("total_duration_ms") or 0)
        item["executionCount"] += float(row.get("execution_count") or 0)
    return sorted(families.values(), key=lambda item: item["totalReads"], reverse=True)


def table_heatmap(root: str | Path) -> list[dict[str, Any]]:
    evidence = load_evidence(root)
    tables: dict[str, dict[str, Any]] = {}
    def bucket(name: str) -> dict[str, Any]:
        owner = owner_for_object(name, evidence.tables.get("ownership_map"))
        return tables.setdefault(name, {"table": name, "module": owner["module"], "reads": 0, "growthPct30d": 0, "missingIndexSignals": 0, "staleStatsSignals": 0, "blockingSignals": 0, "riskScore": 0})
    for row in evidence.tables["sql_top_queries"]:
        item = bucket(str(row.get("object_name") or "unknown"))
        item["reads"] += float(row.get("total_logical_reads") or 0)
    for row in evidence.tables["table_growth"]:
        item = bucket(str(row.get("object_name") or "unknown"))
        item["growthPct30d"] = max(item["growthPct30d"], float(row.get("growth_pct_30d") or 0))
    for row in evidence.tables["missing_indexes"]:
        bucket(str(row.get("object_name") or "unknown"))["missingIndexSignals"] += 1
    for row in evidence.tables["statistics_age"]:
        rows = float(row.get("rows") or 0)
        mods = float(row.get("modification_counter") or 0)
        if rows and mods / rows >= 0.1:
            bucket(str(row.get("object_name") or "unknown"))["staleStatsSignals"] += 1
    for row in evidence.tables["blocking"]:
        bucket(str(row.get("object_name") or "unknown"))["blockingSignals"] += 1
    for item in tables.values():
        item["riskScore"] = min(100, int(item["reads"] / 10_000_000) + int(item["growthPct30d"]) + item["missingIndexSignals"] * 10 + item["staleStatsSignals"] * 5 + item["blockingSignals"] * 15)
    return sorted(tables.values(), key=lambda item: item["riskScore"], reverse=True)


def workload_fingerprint(root: str | Path) -> dict[str, Any]:
    evidence = load_evidence(root)
    text = " ".join(
        [str(row.get("job_name", "")) + " " + str(row.get("class_name", "")) for row in evidence.tables["batch_jobs"]]
        + [str(row.get("object_name", "")) + " " + str(row.get("statement_text", "")) for row in evidence.tables["sql_top_queries"]]
    ).upper()
    patterns = {
        "month-end-close": ["LEDGER", "GENERALJOURNAL", "CUSTTRANS", "VENDTRANS", "SETTLEMENT"],
        "mrp-master-planning": ["REQ", "MRP", "MASTERPLAN", "INVENT"],
        "retail-posting": ["RETAIL", "STATEMENT"],
        "integration-window": ["AIF", "EDI", "STAGING", "IMPORT", "EXPORT", "CUSTOM"],
        "reporting-peak": ["REPORT", "SSRS", "SELECT *"],
    }
    scores = {name: sum(token in text for token in tokens) for name, tokens in patterns.items()}
    best = max(scores.items(), key=lambda item: item[1]) if scores else ("unknown", 0)
    return {"fingerprint": best[0] if best[1] else "unknown", "scores": scores, "confidence": "medium" if best[1] >= 2 else "low"}


def root_cause_confidence(root: str | Path) -> list[dict[str, Any]]:
    findings = analyze_evidence(root)
    causes = summarize_root_causes(findings)
    total = max(1, sum(cause["count"] for cause in causes))
    for cause in causes:
        severity_weight = SEVERITY_RANK.get(cause["highestSeverity"], 1) / 5
        frequency_weight = cause["count"] / total
        cause["confidencePercent"] = min(95, round((severity_weight * 0.65 + frequency_weight * 0.35) * 100, 1))
    return causes


def auto_triage(root: str | Path) -> list[dict[str, Any]]:
    actions = []
    for item in analyze_evidence(root):
        if item["severity"] in {"critical", "high"}:
            lane = "treat-immediately"
        elif item.get("performanceDebt", {}).get("isDebt"):
            lane = "next-maintenance-window"
        elif item["classification"] in {"capacity-planning-signal", "migration-signal"}:
            lane = "architecture-topic"
        else:
            lane = "observe"
        actions.append({"id": item["id"], "title": item["title"], "severity": item["severity"], "lane": lane, "owner": item["axContext"].get("technicalOwner")})
    return actions


def performance_budgets(root: str | Path) -> list[dict[str, Any]]:
    evidence = load_evidence(root)
    budgets = evidence.config.get("performanceBudgets", {"batchDurationSeconds": 3600, "queryAvgDurationMs": 2000})
    rows = []
    for row in evidence.tables["batch_jobs"]:
        duration = float(row.get("duration_seconds") or 0)
        budget = float(row.get("sla_target_seconds") or budgets.get("batchDurationSeconds", 3600))
        rows.append({"type": "batch", "name": row.get("job_name", ""), "actual": duration, "budget": budget, "status": "breach" if budget and duration > budget else "ok"})
    for row in evidence.tables["sql_top_queries"]:
        duration = float(row.get("avg_duration_ms") or 0)
        budget = float(budgets.get("queryAvgDurationMs", 2000))
        rows.append({"type": "query", "name": row.get("object_name", ""), "actual": duration, "budget": budget, "status": "breach" if duration > budget else "ok"})
    return rows


def index_governance(root: str | Path) -> list[dict[str, Any]]:
    evidence = load_evidence(root)
    rows = []
    for row in evidence.tables["missing_indexes"]:
        object_name = str(row.get("object_name") or "")
        impact = float(row.get("avg_user_impact") or 0)
        seeks = float(row.get("user_seeks") or 0)
        rows.append({
            "id": stable_id(["index", object_name, row.get("equality_columns"), row.get("inequality_columns")]),
            "object": object_name,
            "module": owner_for_object(object_name, evidence.tables.get("ownership_map"))["module"],
            "impact": impact,
            "seeks": seeks,
            "status": "candidate-review",
            "risk": "high" if "INVENTTRANS" in object_token(object_name) else "medium",
            "nextStep": "Validate existing index overlap, write overhead, deployment path, and rollback.",
        })
    return sorted(rows, key=lambda item: (item["status"], -item["impact"], -item["seeks"]))


def executive_risk_narrative(root: str | Path) -> str:
    findings = analyze_evidence(root)
    causes = summarize_root_causes(findings)
    scores = module_health_scores(findings)
    top = causes[0] if causes else {"classification": "none", "playbook": "none", "module": "Unknown", "count": 0}
    worst_module = next(iter(scores.items()), ("Unknown", {"score": 100, "risk": "green"}))
    return (
        "# Executive Risk Narrative\n\n"
        f"The current AX performance risk is concentrated in `{worst_module[0]}` with a health score of {worst_module[1]['score']} ({worst_module[1]['risk']}). "
        f"The leading root-cause group is `{top['classification']} / {top['playbook']}` with {top['count']} related findings. "
        "Recommended decision: assign owners for high-severity findings, validate evidence in the next operational window, and approve low-risk remediation through change control.\n"
    )


def ax_performance_slos(root: str | Path) -> list[dict[str, Any]]:
    evidence = load_evidence(root)
    slos = evidence.config.get("slos", {
        "batch_default_seconds": 3600,
        "query_default_ms": 2000,
        "high_findings_budget": 5,
    })
    rows: list[dict[str, Any]] = []
    high_count = sum(1 for item in analyze_evidence(root) if item["severity"] in {"high", "critical"})
    rows.append({"slo": "high-risk-finding-budget", "actual": high_count, "target": slos["high_findings_budget"], "status": "breach" if high_count > slos["high_findings_budget"] else "ok"})
    for row in evidence.tables["batch_jobs"]:
        actual = float(row.get("duration_seconds") or 0)
        target = float(row.get("sla_target_seconds") or slos["batch_default_seconds"])
        rows.append({"slo": f"batch:{row.get('job_name')}", "actual": actual, "target": target, "status": "breach" if target and actual > target else "ok"})
    for family in query_families(root)[:20]:
        avg = family["totalDurationMs"] / max(1, family["executionCount"])
        target = float(slos["query_default_ms"])
        rows.append({"slo": f"query-family:{family['object']}:{family['family']}", "actual": round(avg, 2), "target": target, "status": "breach" if avg > target else "ok"})
    return rows


def anomaly_detection(root: str | Path, trend_db: str | Path | None = None) -> list[dict[str, Any]]:
    findings = analyze_evidence(root)
    current = {
        "finding_count": len(findings),
        "high_count": sum(1 for f in findings if f["severity"] in {"high", "critical"}),
        "risk_score": sum(SEVERITY_RANK.get(f["severity"], 0) for f in findings),
    }
    baseline = {"finding_count": 0, "high_count": 0, "risk_score": 0}
    if trend_db and Path(trend_db).exists():
        import sqlite3
        conn = sqlite3.connect(trend_db)
        try:
            rows = conn.execute("SELECT finding_count, high_count FROM runs ORDER BY run_id DESC LIMIT 20").fetchall()
            if rows:
                baseline["finding_count"] = statistics.mean(row[0] for row in rows)
                baseline["high_count"] = statistics.mean(row[1] for row in rows)
                baseline["risk_score"] = baseline["finding_count"] * 3
        finally:
            conn.close()
    anomalies = []
    for key, value in current.items():
        base = baseline[key]
        if base and value > base * 1.5:
            anomalies.append({"metric": key, "actual": value, "baseline": round(base, 2), "status": "anomaly", "ratio": round(value / base, 2)})
        elif not base:
            anomalies.append({"metric": key, "actual": value, "baseline": None, "status": "baseline-required", "ratio": None})
    return anomalies


def release_gate(before: str | Path, after: str | Path) -> dict[str, Any]:
    comparison = compare_baseline(before, after)
    after_findings = analyze_evidence(after)
    blockers = [f for f in after_findings if f["severity"] in {"critical", "high"}]
    gate = "fail" if comparison["result"] == "regressed" or len(blockers) > 0 else "pass"
    return {"gate": gate, "comparison": comparison, "blockerCount": len(blockers), "blockers": blockers[:10]}


def plan_regression_watcher(root: str | Path) -> list[dict[str, Any]]:
    evidence = load_evidence(root)
    rows = []
    for row in evidence.tables["plan_cache_variance"]:
        min_ms = float(row.get("min_avg_duration_ms") or 0)
        max_ms = float(row.get("max_avg_duration_ms") or 0)
        ratio = (max_ms / min_ms) if min_ms else 0
        if ratio >= 2 or float(row.get("plan_count") or 0) > 1:
            rows.append({"queryHash": row.get("query_hash"), "planCount": row.get("plan_count"), "minAvgMs": min_ms, "maxAvgMs": max_ms, "regressionRatio": round(ratio, 2), "recommendation": "Compare plans and validate Query Store runtime before forcing or clearing plans."})
    for row in evidence.tables["query_store_runtime"]:
        if float(row.get("avg_duration_ms") or 0) >= 30_000:
            rows.append({"queryId": row.get("query_id"), "planId": row.get("plan_id"), "avgDurationMs": row.get("avg_duration_ms"), "recommendation": "Review Query Store plan history and baseline against prior intervals."})
    return rows


def custom_code_ownership_graph(root: str | Path) -> dict[str, Any]:
    evidence = load_evidence(root)
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, str]] = []
    def node(name: str, kind: str) -> None:
        nodes.setdefault(name, {"id": name, "kind": kind})
    for row in evidence.tables["batch_jobs"] + evidence.tables["batch_tasks"]:
        job = str(row.get("job_name") or row.get("caption") or row.get("job_id") or row.get("task_id") or "")
        klass = str(row.get("class_name") or row.get("class_number") or "")
        if job:
            node(job, "batch")
        if klass:
            node(klass, "xpp-class")
            edges.append({"from": job, "to": klass, "type": "executes"})
    for finding in analyze_evidence(root):
        node(finding["id"], "finding")
        for table in finding["axContext"].get("tables", []):
            node(table, "table")
            edges.append({"from": finding["id"], "to": table, "type": "affects"})
    return {"nodes": list(nodes.values()), "edges": edges}


def cost_of_delay(root: str | Path) -> list[dict[str, Any]]:
    evidence = load_evidence(root)
    rates = evidence.config.get("costModel", {"userWaitHourCost": 75, "batchDelayHourCost": 250, "highFindingDailyRiskCost": 500})
    rows = []
    for finding in analyze_evidence(root):
        severity_factor = SEVERITY_RANK.get(finding["severity"], 1)
        daily = severity_factor * float(rates["highFindingDailyRiskCost"])
        if "batch" in finding["recommendation"].get("playbook", ""):
            daily += float(rates["batchDelayHourCost"])
        rows.append({"id": finding["id"], "title": finding["title"], "severity": finding["severity"], "estimatedDailyCost": round(daily, 2), "owner": finding["axContext"].get("technicalOwner")})
    return rows


def evidence_quality_grades(root: str | Path) -> list[dict[str, Any]]:
    grades = []
    for finding in analyze_evidence(root):
        sources = {ev.get("source") for ev in finding.get("evidence", [])}
        has_ax = bool(finding["axContext"].get("batchJobs") or finding["axContext"].get("classes"))
        has_sql = bool(finding["sqlContext"].get("queryHash") or finding["sqlContext"].get("waitTypes") or finding["sqlContext"].get("objects"))
        if has_ax and has_sql:
            grade = "A"
            meaning = "direct AX and SQL evidence"
        elif has_sql and sources:
            grade = "B"
            meaning = "direct SQL evidence with inferred AX context"
        elif sources:
            grade = "C"
            meaning = "single-source evidence"
        else:
            grade = "D"
            meaning = "weak heuristic"
        grades.append({"id": finding["id"], "title": finding["title"], "grade": grade, "meaning": meaning})
    return grades


def recommendation_scenarios(root: str | Path) -> list[dict[str, Any]]:
    rows = []
    for finding in analyze_evidence(root)[:50]:
        playbook = finding["recommendation"].get("playbook", "")
        options = []
        if "index" in playbook:
            options.append({"scenario": "index-review", "benefit": "medium-high", "risk": "medium-high"})
        if "statistics" in playbook:
            options.append({"scenario": "targeted-statistics-update", "benefit": "medium", "risk": "low"})
        if "batch" in playbook:
            options.append({"scenario": "batch-reschedule", "benefit": "medium", "risk": "low"})
        if "data-growth" in playbook:
            options.append({"scenario": "archive-cleanup-assessment", "benefit": "high", "risk": "high"})
        if not options:
            options.append({"scenario": "observe-and-collect-delta", "benefit": "low", "risk": "low"})
        rows.append({"id": finding["id"], "title": finding["title"], "options": options})
    return rows


def compliance_mode_check(root: str | Path) -> list[dict[str, Any]]:
    required = ["businessOwner", "technicalOwner"]
    rows = []
    for finding in analyze_evidence(root):
        missing = []
        for field in required:
            if not finding["axContext"].get(field) or finding["axContext"].get(field) == "Unknown":
                missing.append(field)
        if not finding["validation"].get("rollback"):
            missing.append("rollback")
        if not finding["validation"].get("successMetric"):
            missing.append("successMetric")
        rows.append({"id": finding["id"], "status": "complete" if not missing else "incomplete", "missing": missing})
    return rows


def chain_of_custody(root: str | Path) -> dict[str, Any]:
    root_path = Path(root)
    files = []
    for path in sorted(root_path.rglob("*")):
        if path.is_file():
            files.append({"path": str(path.relative_to(root_path)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size})
    manifest = {"createdAt": now_iso(), "root": str(root_path), "fileCount": len(files), "files": files}
    manifest["manifestSha256"] = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    return manifest


def workload_calendar_map(root: str | Path) -> list[dict[str, Any]]:
    evidence = load_evidence(root)
    calendar = evidence.metadata.get("businessCalendar", []) or evidence.config.get("businessCalendar", [])
    rows = []
    for finding in analyze_evidence(root):
        rows.append({"id": finding["id"], "title": finding["title"], "matchedWindows": [item.get("name") for item in calendar], "windowCount": len(calendar)})
    return rows


def capacity_exhaustion_forecast(root: str | Path) -> list[dict[str, Any]]:
    evidence = load_evidence(root)
    rows = []
    for row in evidence.tables["table_growth"]:
        growth_pct = float(row.get("growth_pct_30d") or 0)
        size = float(row.get("size_mb") or 0)
        if growth_pct > 0:
            months_to_double = round(100 / growth_pct, 1)
            rows.append({"resource": row.get("object_name"), "currentSizeMb": size, "growthPct30d": growth_pct, "monthsToDouble": months_to_double})
    for row in evidence.tables["file_latency"]:
        reads = float(row.get("num_of_reads") or 0)
        latency = (float(row.get("io_stall_read_ms") or 0) / reads) if reads else 0
        if latency >= 15:
            rows.append({"resource": row.get("file_logical_name"), "avgReadLatencyMs": round(latency, 2), "forecast": "already-above-threshold"})
    return rows


def retention_policy_advisor(root: str | Path) -> list[dict[str, Any]]:
    policies = []
    for row in load_evidence(root).tables["table_growth"]:
        table = str(row.get("object_name") or "")
        closed = float(row.get("closed_record_pct") or 0)
        if "BATCH" in object_token(table):
            retention = "90 days"
        elif "RETAIL" in object_token(table):
            retention = "30-180 days depending on audit/reporting"
        elif closed >= 80:
            retention = "archive closed records after business/legal approval"
        else:
            retention = "monitor"
        policies.append({"table": table, "closedRecordPct": closed, "proposedRetention": retention, "requiresApproval": True})
    return policies


def knowledge_feedback(root: str | Path, output: str | Path, resolution: str = "unresolved") -> Path:
    rows = []
    out = Path(output)
    if out.exists():
        rows = read_json(out, [])
    for finding in analyze_evidence(root):
        rows.append({"findingId": finding["id"], "title": finding["title"], "playbook": finding["recommendation"].get("playbook"), "resolution": resolution, "capturedAt": now_iso()})
    write_json(out, rows)
    return out


def fleet_view(evidence_dirs: list[str | Path]) -> list[dict[str, Any]]:
    rows = []
    for directory in evidence_dirs:
        evidence = load_evidence(directory)
        findings = analyze_evidence(directory)
        rows.append({
            "environment": evidence.config.get("environment") or evidence.metadata.get("environment") or str(directory),
            "evidence": str(directory),
            "findings": len(findings),
            "highCritical": sum(1 for f in findings if f["severity"] in {"high", "critical"}),
            "healthScores": module_health_scores(findings),
        })
    return rows


def runbook_generator(root: str | Path) -> str:
    lines = ["# AX Performance Runbook", ""]
    for cause in summarize_root_causes(analyze_evidence(root))[:12]:
        lines.extend([
            f"## {cause['classification']} / {cause['playbook']} / {cause['module']}",
            "",
            "1. Confirm the evidence source and time window.",
            "2. Validate AX owner and affected business process.",
            "3. Run generated validation scripts where available.",
            "4. Select low-risk remediation or prepare CAB package.",
            "5. Re-measure with the same evidence window.",
            "",
        ])
    return "\n".join(lines)


def sql_agent_correlation(root: str | Path) -> list[dict[str, Any]]:
    evidence = load_evidence(root)
    jobs = evidence.tables.get("sql_agent_jobs", [])
    batch = evidence.tables["batch_jobs"]
    rows = []
    for job in jobs:
        for batch_job in batch:
            rows.append({"sqlAgentJob": job.get("job_name"), "axBatchJob": batch_job.get("job_name"), "correlation": "requires-time-window-validation"})
    return rows


def aos_topology_advisor(root: str | Path) -> list[dict[str, Any]]:
    evidence = load_evidence(root)
    by_aos: dict[str, int] = {}
    for row in evidence.tables["batch_jobs"]:
        aos = str(row.get("aos") or "unknown")
        by_aos[aos] = by_aos.get(aos, 0) + 1
    rows = [{"aos": aos, "batchJobs": count, "recommendation": "consider separating batch/services/user load" if count > 5 or aos == "unknown" else "balanced"} for aos, count in by_aos.items()]
    if not rows:
        rows.append({"aos": "unknown", "batchJobs": 0, "recommendation": "collect AOS assignment and counter evidence"})
    return rows


def archiving_impact_sandbox(root: str | Path, archive_percent: float = 50.0) -> list[dict[str, Any]]:
    rows = []
    for item in table_heatmap(root):
        reduction = archive_percent / 100
        rows.append({"table": item["table"], "currentRiskScore": item["riskScore"], "archivePercent": archive_percent, "estimatedRiskScoreAfter": max(0, round(item["riskScore"] * (1 - reduction), 1)), "estimatedReadReduction": f"{archive_percent}% if archived rows match hot scan range"})
    return rows


def ai_root_cause_narrative(root: str | Path) -> str:
    findings = analyze_evidence(root)
    causes = root_cause_confidence(root)[:5]
    lines = ["# Root Cause Narrative", ""]
    if not findings:
        return "# Root Cause Narrative\n\nNo findings were generated.\n"
    lines.append("The evidence indicates several related performance pressure areas rather than a single isolated metric.")
    for cause in causes:
        lines.append(f"- `{cause['playbook']}` in `{cause['module']}` has {cause['count']} findings and confidence {cause.get('confidencePercent')}%.")
    lines.append("")
    lines.append("Recommended next action: validate the highest-confidence root cause with read-only scripts, assign the owner, and re-measure after any approved change.")
    return "\n".join(lines) + "\n"


def performance_digital_twin(root: str | Path) -> dict[str, Any]:
    evidence = load_evidence(root)
    return {
        "environment": evidence.config.get("environment") or evidence.metadata.get("environment"),
        "aosNodes": sorted({str(r.get("aos")) for r in evidence.tables["batch_jobs"] if r.get("aos")}),
        "databases": sorted({str(r.get("database_name")) for r in evidence.tables["file_latency"] if r.get("database_name")}),
        "batchJobs": len(evidence.tables["batch_jobs"]),
        "queryFamilies": query_families(root)[:20],
        "hotTables": table_heatmap(root)[:20],
        "businessCalendar": evidence.metadata.get("businessCalendar", []) or evidence.config.get("businessCalendar", []),
    }


def causal_graph(root: str | Path) -> dict[str, Any]:
    nodes, edges = {}, []
    def node(node_id: str, kind: str, label: str | None = None):
        nodes.setdefault(node_id, {"id": node_id, "kind": kind, "label": label or node_id})
    for f in analyze_evidence(root):
        node(f["id"], "finding", f["title"])
        playbook = f["recommendation"].get("playbook", "unknown")
        node(playbook, "root-cause")
        edges.append({"from": playbook, "to": f["id"], "type": "explains"})
        for wt in f["sqlContext"].get("waitTypes", []):
            node(wt, "wait")
            edges.append({"from": wt, "to": f["id"], "type": "evidence"})
        for obj in f["sqlContext"].get("objects", []):
            node(obj, "table")
            edges.append({"from": f["id"], "to": obj, "type": "affects"})
    return {"nodes": list(nodes.values()), "edges": edges}


def autonomous_evidence_plan(root: str | Path) -> list[dict[str, Any]]:
    existing = load_evidence(root).tables
    plan = []
    required = {
        "blocking": "Collect blocking snapshot during reported slow window.",
        "deadlock_processes": "Parse deadlock XML or enable system_health extraction.",
        "trace_parser": "Import Trace Parser export to link SQL to X++ call stacks.",
        "aos_counters": "Collect AOS/performance counters during the incident window.",
        "sql_wait_stats_delta": "Collect wait deltas with -WaitDeltaSeconds for current pressure.",
    }
    for name, action in required.items():
        if not existing.get(name):
            plan.append({"missingEvidence": name, "action": action, "risk": "read-only"})
    return plan


def confidence_drilldown(root: str | Path) -> list[dict[str, Any]]:
    rows = []
    for f in analyze_evidence(root):
        if f["confidence"] in {"low", "medium"}:
            steps = ["collect wait delta", "capture execution plan", "map AX owner"]
            if not f["axContext"].get("classes"):
                steps.append("import Trace Parser or DynamicsPerf call stack")
            rows.append({"id": f["id"], "confidence": f["confidence"], "nextChecks": steps})
    return rows


def performance_contracts(root: str | Path) -> list[dict[str, Any]]:
    evidence = load_evidence(root)
    contracts = evidence.config.get("contracts", {"maxHighFindings": 5, "maxQueryAvgMs": 5000, "maxBatchSeconds": 3600})
    rows = []
    findings = analyze_evidence(root)
    rows.append({"contract": "maxHighFindings", "actual": sum(1 for f in findings if f["severity"] in {"high","critical"}), "target": contracts["maxHighFindings"]})
    for q in evidence.tables["sql_top_queries"]:
        rows.append({"contract": f"query:{q.get('object_name')}", "actual": q.get("avg_duration_ms"), "target": contracts["maxQueryAvgMs"]})
    for b in evidence.tables["batch_jobs"]:
        rows.append({"contract": f"batch:{b.get('job_name')}", "actual": b.get("duration_seconds"), "target": b.get("sla_target_seconds") or contracts["maxBatchSeconds"]})
    for r in rows:
        r["status"] = "pass" if float(r.get("actual") or 0) <= float(r.get("target") or 0) else "fail"
    return rows


def query_to_xpp_trace(root: str | Path) -> list[dict[str, Any]]:
    evidence = load_evidence(root)
    traces = evidence.tables["trace_parser"] + evidence.tables["dynamicsperf"]
    if not traces:
        raise FileNotFoundError("Trace Parser or DynamicsPerf evidence is required for Query-to-X++ trace linking.")
    rows = []
    for q in evidence.tables["sql_top_queries"]:
        sql = str(q.get("statement_text", "")).upper()
        for t in traces:
            t_sql = str(t.get("sql_text") or t.get("query_hash") or "").upper()
            if t_sql and (t_sql[:40] in sql or str(q.get("query_hash", "")) == str(t.get("query_hash", ""))):
                rows.append({"queryHash": q.get("query_hash"), "object": q.get("object_name"), "class": t.get("class_name", ""), "method": t.get("method_name", ""), "source": "trace"})
    return rows


def change_blast_radius(root: str | Path, target: str) -> dict[str, Any]:
    findings = analyze_evidence(root)
    affected = [f for f in findings if target.upper() in json.dumps(f).upper()]
    return {"target": target, "affectedFindings": len(affected), "modules": sorted({f["axContext"].get("module","Unknown") for f in affected}), "findings": affected[:25]}


def temporal_hotspot_map(root: str | Path) -> list[dict[str, Any]]:
    evidence = load_evidence(root)
    rows = []
    for source in ("sql_top_queries", "batch_jobs"):
        for r in evidence.tables[source]:
            ts = str(r.get("last_execution_time") or r.get("start_time") or "")
            hour = ts[11:13] if len(ts) >= 13 else "unknown"
            rows.append({"hour": hour, "source": source, "object": r.get("object_name") or r.get("job_name"), "pressure": r.get("total_logical_reads") or r.get("duration_seconds") or 1})
    return rows


def debt_interest(root: str | Path) -> list[dict[str, Any]]:
    rows = []
    for f in analyze_evidence(root):
        debt = f.get("performanceDebt", {})
        age = float(debt.get("ageDays") or 0)
        recurrence = float(debt.get("recurrenceCount") or 1)
        severity = SEVERITY_RANK.get(f["severity"], 1)
        rows.append({"id": f["id"], "title": f["title"], "interestScore": round(severity * (1 + age / 30) * recurrence, 2), "nextDecision": debt.get("nextDecision")})
    return sorted(rows, key=lambda r: r["interestScore"], reverse=True)


def remediation_portfolio(root: str | Path) -> list[dict[str, Any]]:
    scenarios = recommendation_scenarios(root)
    portfolio = []
    for item in scenarios:
        for option in item["options"]:
            risk = {"low": 1, "medium": 2, "medium-high": 3, "high": 4}.get(option["risk"], 2)
            benefit = {"low": 1, "medium": 2, "medium-high": 3, "high": 4}.get(option["benefit"], 2)
            portfolio.append({"findingId": item["id"], **option, "portfolioScore": round(benefit / risk, 2)})
    return sorted(portfolio, key=lambda r: r["portfolioScore"], reverse=True)


def validation_orchestrator(before: str | Path, after: str | Path, output_dir: str | Path) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    comparison = compare_baseline(before, after)
    write_json(out / "validation-comparison.json", comparison)
    (out / "validation-summary.md").write_text("# Validation Summary\n\n" + json.dumps(comparison, indent=2), encoding="utf-8")
    return {"outputDir": str(out), "comparison": comparison}


def aging_risk_index(root: str | Path) -> dict[str, Any]:
    findings = analyze_evidence(root)
    high = sum(1 for f in findings if f["severity"] in {"high","critical"})
    growth = sum(float(r.get("growth_pct_30d") or 0) for r in load_evidence(root).tables["table_growth"])
    score = min(100, 20 + high * 5 + growth)
    return {"agingRiskIndex": round(score, 1), "drivers": {"highFindings": high, "dataGrowthPctSum": round(growth, 1), "sql2016SupportRisk": "support ends 2026-07-14"}}


def d365_migration_signal(root: str | Path) -> list[dict[str, Any]]:
    rows = []
    for f in analyze_evidence(root):
        signal = "tuning"
        if f["classification"] in {"migration-signal", "redesign-needed", "capacity-planning-signal"}:
            signal = "modernization"
        if f.get("dataGrowth", {}).get("isGrowthDriven"):
            signal = "data-platform-modernization"
        rows.append({"id": f["id"], "title": f["title"], "signal": signal, "module": f["axContext"].get("module")})
    return rows


def approval_workflow(root: str | Path, output: str | Path) -> Path:
    rows = [{"id": f["id"], "title": f["title"], "state": "proposed", "owner": f["axContext"].get("technicalOwner"), "updatedAt": now_iso()} for f in analyze_evidence(root)]
    write_json(output, rows)
    return Path(output)


def explainability_scores(root: str | Path) -> list[dict[str, Any]]:
    grades = {g["id"]: g["grade"] for g in evidence_quality_grades(root)}
    grade_score = {"A": 95, "B": 80, "C": 60, "D": 35}
    return [{"id": f["id"], "title": f["title"], "explainabilityScore": grade_score.get(grades.get(f["id"], "D"), 35), "evidenceGrade": grades.get(f["id"], "D")} for f in analyze_evidence(root)]


def operator_copilot_context(root: str | Path) -> dict[str, Any]:
    findings = analyze_evidence(root)
    return {"commands": ["show-p1", "why", "evidence", "next-check", "owner", "validation"], "p1": findings[:10], "rootCauses": summarize_root_causes(findings)[:10]}


def regression_unit_tests(root: str | Path) -> str:
    lines = ["import unittest", "", "class AxPerformanceRegressionTests(unittest.TestCase):"]
    for f in analyze_evidence(root)[:20]:
        name = "".join(ch if ch.isalnum() else "_" for ch in f["id"].lower())
        lines.extend([f"    def test_{name}(self):", f"        self.assertTrue(True, 'Track regression for {f['title']}')", ""])
    return "\n".join(lines)


def sensitive_boundary_detector(root: str | Path) -> list[dict[str, Any]]:
    sensitive = []
    patterns = ["login", "user", "client", "hostname", "statement_text", "query_sql_text", "inputbuf"]
    for path in Path(root).glob("*.csv"):
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            headers = next(reader, [])
        hits = [h for h in headers if any(p in h.lower() for p in patterns)]
        if hits:
            sensitive.append({"file": str(path), "sensitiveColumns": hits, "recommendation": "Run mask_evidence.py before sharing."})
    return sensitive


def self_healing_rule_update(root: str | Path, output: str | Path) -> Path:
    rules = [{"match": f["recommendation"].get("playbook"), "classification": f["classification"], "validation": f["validation"].get("successMetric"), "sourceFinding": f["id"]} for f in analyze_evidence(root)]
    write_json(output, rules)
    return Path(output)


def anonymized_pattern_export(root: str | Path, output: str | Path) -> Path:
    rows = []
    for f in analyze_evidence(root):
        rows.append({"classification": f["classification"], "playbook": f["recommendation"].get("playbook"), "severity": f["severity"], "module": f["axContext"].get("module"), "evidenceGrade": "anonymized"})
    write_json(output, rows)
    return Path(output)


def compare_baseline(before: str | Path, after: str | Path) -> dict[str, Any]:
    before_findings = analyze_evidence(before)
    after_findings = analyze_evidence(after)
    before_score = sum(SEVERITY_RANK.get(item["severity"], 0) for item in before_findings)
    after_score = sum(SEVERITY_RANK.get(item["severity"], 0) for item in after_findings)
    if after_score < before_score:
        result = "improved"
    elif after_score > before_score:
        result = "regressed"
    else:
        result = "unchanged"
    return {
        "beforeFindingCount": len(before_findings),
        "afterFindingCount": len(after_findings),
        "beforeRiskScore": before_score,
        "afterRiskScore": after_score,
        "result": result,
    }


def cmd_analyze(args: argparse.Namespace) -> int:
    findings = analyze_evidence(args.evidence)
    write_json(args.output, findings)
    print(f"Wrote {len(findings)} findings to {args.output}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    report = build_report(args.evidence)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(report, encoding="utf-8")
    print(f"Wrote report to {args.output}")
    return 0


def cmd_pack(args: argparse.Namespace) -> int:
    path = export_evidence_pack(args.evidence, args.output)
    print(f"Wrote evidence pack to {path}")
    return 0


def cmd_powerbi(args: argparse.Namespace) -> int:
    path = export_powerbi_dataset(args.evidence, args.output)
    print(f"Wrote Power BI CSV dataset to {path}")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    write_json(args.output, compare_baseline(args.before, args.after))
    print(f"Wrote comparison to {args.output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AX Performance Advisor tools")
    sub = parser.add_subparsers(dest="command", required=True)
    analyze = sub.add_parser("analyze")
    analyze.add_argument("--evidence", required=True)
    analyze.add_argument("--output", required=True)
    analyze.set_defaults(func=cmd_analyze)
    report = sub.add_parser("report")
    report.add_argument("--evidence", required=True)
    report.add_argument("--output", required=True)
    report.set_defaults(func=cmd_report)
    pack = sub.add_parser("pack")
    pack.add_argument("--evidence", required=True)
    pack.add_argument("--output", required=True)
    pack.set_defaults(func=cmd_pack)
    powerbi = sub.add_parser("powerbi")
    powerbi.add_argument("--evidence", required=True)
    powerbi.add_argument("--output", required=True)
    powerbi.set_defaults(func=cmd_powerbi)
    compare = sub.add_parser("compare")
    compare.add_argument("--before", required=True)
    compare.add_argument("--after", required=True)
    compare.add_argument("--output", required=True)
    compare.set_defaults(func=cmd_compare)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
