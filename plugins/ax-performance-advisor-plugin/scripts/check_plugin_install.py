from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate AXPA Codex plugin marketplace installation.")
    parser.add_argument("--codex-home", default=str(Path.home() / ".codex"))
    parser.add_argument("--marketplace-name", default="ax-performance-advisory")
    parser.add_argument("--plugin-name", default="ax-performance-advisor-plugin")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    codex_home = Path(args.codex_home)
    marketplace_root = codex_home / "plugins" / "marketplaces" / args.marketplace_name
    plugin_root = marketplace_root / "plugins" / args.plugin_name
    config_path = codex_home / "config.toml"
    marketplace_path = marketplace_root / "marketplace.json"
    plugin_json_path = plugin_root / ".codex-plugin" / "plugin.json"
    mcp_json_path = plugin_root / ".mcp.json"
    app_json_path = plugin_root / ".app.json"
    skills_root = plugin_root / "skills"

    checks: dict[str, object] = {
        "codexHome": str(codex_home),
        "marketplaceRoot": str(marketplace_root),
        "pluginRoot": str(plugin_root),
        "configTomlExists": config_path.exists(),
        "marketplaceJsonExists": marketplace_path.exists(),
        "pluginJsonExists": plugin_json_path.exists(),
        "mcpJsonExists": mcp_json_path.exists(),
        "appJsonExists": app_json_path.exists(),
        "skillsRootExists": skills_root.exists(),
        "skillCount": len([p for p in skills_root.iterdir() if p.is_dir()]) if skills_root.exists() else 0,
        "configTomlValid": False,
        "marketplaceRegistered": False,
        "pluginEnabled": False,
        "pluginManifestNameMatches": False,
        "marketplaceEntryPresent": False,
        "mcpServerPresent": False,
        "status": "failed",
        "errors": [],
    }

    errors: list[str] = []

    if tomllib is None:
        errors.append("Python tomllib is unavailable; use Python 3.11+ for config validation.")
    elif config_path.exists():
        try:
            config = tomllib.loads(config_path.read_text(encoding="utf-8-sig"))
            checks["configTomlValid"] = True
            marketplaces = config.get("marketplaces", {})
            plugins = config.get("plugins", {})
            checks["marketplaceRegistered"] = args.marketplace_name in marketplaces
            checks["pluginEnabled"] = bool(plugins.get(f"{args.plugin_name}@{args.marketplace_name}", {}).get("enabled"))
        except Exception as exc:  # pragma: no cover - defensive CLI path
            errors.append(f"config.toml is not valid TOML: {exc}")
    else:
        errors.append(f"Missing Codex config: {config_path}")

    if marketplace_path.exists():
        try:
            marketplace = load_json(marketplace_path)
            checks["marketplaceEntryPresent"] = any(item.get("name") == args.plugin_name for item in marketplace.get("plugins", []))
        except Exception as exc:
            errors.append(f"marketplace.json is not valid JSON: {exc}")
    else:
        errors.append(f"Missing marketplace.json: {marketplace_path}")

    if plugin_json_path.exists():
        try:
            plugin = load_json(plugin_json_path)
            checks["pluginManifestNameMatches"] = plugin.get("name") == args.plugin_name
        except Exception as exc:
            errors.append(f"plugin.json is not valid JSON: {exc}")
    else:
        errors.append(f"Missing plugin.json: {plugin_json_path}")

    if mcp_json_path.exists():
        try:
            mcp = load_json(mcp_json_path)
            checks["mcpServerPresent"] = "ax-performance-advisor" in mcp.get("mcpServers", {})
        except Exception as exc:
            errors.append(f".mcp.json is not valid JSON: {exc}")

    required = [
        "configTomlValid",
        "marketplaceRegistered",
        "pluginEnabled",
        "marketplaceJsonExists",
        "marketplaceEntryPresent",
        "pluginJsonExists",
        "pluginManifestNameMatches",
        "mcpJsonExists",
        "mcpServerPresent",
        "skillsRootExists",
    ]
    checks["errors"] = errors
    checks["status"] = "ok" if not errors and all(bool(checks[name]) for name in required) else "failed"

    if args.json:
        print(json.dumps(checks, indent=2, ensure_ascii=False))
    else:
        print(f"AXPA plugin install check: {checks['status']}")
        for name in required + ["skillCount"]:
            print(f"- {name}: {checks[name]}")
        for error in errors:
            print(f"- error: {error}", file=sys.stderr)
    return 0 if checks["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
