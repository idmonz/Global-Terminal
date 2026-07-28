from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import zipfile
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from scripts.audit_external_references import (
    ROOT,
    TEXT_BASENAMES,
    TEXT_EXTENSIONS,
    _collect_license_decision,
    _is_text_candidate,
    _is_vendored,
    _project_name,
)


DEFAULT_EXTERNAL_DIR = ROOT / "external (2)" / "external"
DEFAULT_OUTPUT_CSV = ROOT / "docs" / "PHASE_5F_EXTERNAL_FULL_INVENTORY.csv"
DEFAULT_OUTPUT_JSON = ROOT / "review_workspace" / "external2_analysis" / "phase5f" / "external_full_inventory_summary.json"
SYMBOL_SCAN_LIMIT_BYTES = 2_000_000

EXTRA_TEXT_EXTENSIONS = {".astro", ".graphql", ".hcl", ".kt", ".lua", ".php", ".rb", ".scala", ".svelte", ".vue"}

PROJECT_PATTERNS: dict[str, dict[str, str]] = {
    "agent-skills": {
        "ui": "AI engineering workflow and acceptance-gate process",
        "data": "specification, evidence, validation, and shipping checklists",
        "algorithms": "task decomposition and source-driven development process",
        "ideas": "repeatable spec-to-test-to-visual-verification lifecycle",
        "target": "docs/PHASE_5F_AGENT_SKILLS_USAGE.md and future execution prompts",
    },
    "open-design": {
        "ui": "design-token systems, layout review, visual stability, redesign and taste rubrics",
        "data": "design-system manifests, tokens, component inventories, visual evidence",
        "algorithms": "visual scoring, design-system validation, screenshot baseline checks",
        "ideas": "first-party terminal design tokens and screenshot acceptance workflow",
        "target": "docs/PHASE_5F_DESIGN_SYSTEM_SPEC.md and apps/web clean-room design work",
    },
    "worldmonitor": {
        "ui": "map-first news, layer, timeline, provider-health and event inspection",
        "data": "geopolitical events, layers, feeds, source status and map markers",
        "algorithms": "event aggregation, geospatial grouping and provider readiness",
        "ideas": "War Room map/news/event fusion and source rail",
        "target": "lib/war_room_map.py, lib/map_news_event_fusion.py, apps/web War Room",
    },
    "worldview": {
        "ui": "interactive map comparison, timeline and location/layer controls",
        "data": "geospatial layers and compare-state parameters",
        "algorithms": "map state, temporal comparison and layer composition",
        "ideas": "War Room compare windows and map interaction model",
        "target": "apps/web map controls and JSON-safe compare contracts",
    },
    "openbb": {
        "ui": "provider-aware finance workspaces, widgets and command hierarchy",
        "data": "typed finance routes, provider registry and financial datasets",
        "algorithms": "provider routing, normalization and command discovery",
        "ideas": "optional provider adapters and source-aware asset workstations",
        "target": "lib/provider_router.py, lib/api_contracts.py, apps/web asset workstations",
    },
    "openstock": {
        "ui": "retail market dashboard, stock discovery and research workflow",
        "data": "market, symbol, portfolio and news records",
        "algorithms": "market aggregation and stock research composition",
        "ideas": "clean-room retail terminal navigation",
        "target": "apps/web market and asset workstations",
    },
    "financedatabase": {
        "ui": "asset universe search and taxonomy",
        "data": "equity, ETF, fund, index, FX, crypto and money-market reference schemas",
        "algorithms": "asset classification and identifier normalization",
        "ideas": "searchable first-party asset-universe contract",
        "target": "lib/asset_universe.py and symbol routing",
    },
    "helix": {
        "ui": "graph query and knowledge-navigation concepts",
        "data": "graph/vector nodes, edges and query schemas",
        "algorithms": "event-to-asset graph traversal and retrieval",
        "ideas": "clean-room event-to-asset relationship contracts",
        "target": "lib/event_asset_graph.py; persistence remains unavailable",
    },
    "supabase": {
        "ui": "commercial developer dashboard, status, auth and database readiness",
        "data": "Postgres, auth, storage, realtime and API metadata",
        "algorithms": "persistence and entitlement architecture",
        "ideas": "future accounts/watchlists/persistence readiness",
        "target": "future hosted persistence phase; no runtime dependency now",
    },
    "bb-terminal": {
        "ui": "dense keyboard-first command terminal and multi-panel asset workspace",
        "data": "quotes, charts, watchlists, news and financial panels",
        "algorithms": "command dispatch and explainable rule classification",
        "ideas": "Bloomberg-like behavior without visual cloning",
        "target": "lib/command_workspace.py and apps/web terminal workspace",
    },
    "bloomberg-terminal": {
        "ui": "dense selectable watchlist and terminal panels",
        "data": "asset, quote and watchlist records",
        "algorithms": "workspace state and command navigation",
        "ideas": "keyboard-first research workspace",
        "target": "apps/web command workspace and watchlist shell",
    },
    "dexter": {
        "ui": "AI-assisted finance research workflow",
        "data": "research context, source references and analytical responses",
        "algorithms": "context assembly and research-agent orchestration",
        "ideas": "source-bound contextual research rail",
        "target": "AI research summaries and source register",
    },
    "osiris": {
        "ui": "OSINT map/feed dashboard",
        "data": "earthquake, event and public-feed rows",
        "algorithms": "keyless event fetching and normalization",
        "ideas": "no-key source-backed map layers",
        "target": "lib/live_feeds.py and War Room layers",
    },
    "optlib": {
        "ui": "options analytics utilities",
        "data": "option contracts, volatility and pricing inputs",
        "algorithms": "option pricing and volatility calculations",
        "ideas": "options diagnostics with provider and model caveats",
        "target": "lib/options_* and options-quant workstation",
    },
    "quant-traderr": {
        "ui": "quant research lab",
        "data": "strategy, returns and diagnostics",
        "algorithms": "backtest and research diagnostics",
        "ideas": "non-advisory quant workstation",
        "target": "portfolio/strategy research labs",
    },
    "tensortrade": {
        "ui": "simulation environment reference",
        "data": "environment, feed and action state",
        "algorithms": "reinforcement-learning trading environment",
        "ideas": "governed simulation metadata only",
        "target": "action-less simulation; execution remains forbidden",
    },
    "quantdinger": {
        "ui": "quant workflow and monitoring",
        "data": "research, strategy, backtest and execution-stage metadata",
        "algorithms": "research-to-monitoring workflow",
        "ideas": "safe research lifecycle without execution",
        "target": "quant lab workflow and governance",
    },
    "kronos": {
        "ui": "forecast research interface",
        "data": "time-series model inputs and outputs",
        "algorithms": "time-series forecasting",
        "ideas": "forecast-readiness and uncertainty contracts",
        "target": "scenario diagnostics only; no directional recommendation",
    },
}


SYMBOL_PATTERNS = [
    re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)", re.MULTILINE),
    re.compile(r"^\s*class\s+([A-Za-z_]\w*)", re.MULTILINE),
    re.compile(r"\b(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)"),
    re.compile(r"\b(?:export\s+)?class\s+([A-Za-z_$][\w$]*)"),
    re.compile(r"\b(?:export\s+)?interface\s+([A-Za-z_$][\w$]*)"),
    re.compile(r"\b(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*="),
    re.compile(r"\bfn\s+([A-Za-z_]\w*)\s*\("),
    re.compile(r"\b(?:struct|enum|trait)\s+([A-Za-z_]\w*)"),
    re.compile(r"\bfunc\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)\s*\("),
    re.compile(r"\b(?:public|private|protected)?\s*(?:static\s+)?(?:class|interface|enum)\s+([A-Za-z_]\w*)"),
]


CSV_FIELDS = [
    "archive",
    "project",
    "path",
    "file_type",
    "size",
    "line_count",
    "detected_license",
    "license_stance",
    "direct_source_reuse",
    "behavior_reuse",
    "relevant_symbols",
    "ui_patterns",
    "data_patterns",
    "algorithms",
    "product_ideas",
    "legal_risk",
    "adoption_target",
    "coverage",
    "vendored",
    "sha256_16",
    "notes",
]


def _project_profile(archive_name: str) -> dict[str, str]:
    lowered = archive_name.lower()
    for token, profile in PROJECT_PATTERNS.items():
        if token in lowered:
            return profile
    return {
        "ui": "reference project UI patterns require manual review",
        "data": "reference project data structures require manual review",
        "algorithms": "reference algorithms require manual review",
        "ideas": "candidate research workflow",
        "target": "behavior-only backlog until manual and license review",
    }


def _is_text(path: str) -> bool:
    suffix = Path(path.lower()).suffix
    return _is_text_candidate(path) or suffix in EXTRA_TEXT_EXTENSIONS or Path(path.lower()).name in TEXT_BASENAMES


def _line_count(raw: bytes) -> int:
    if not raw:
        return 0
    return raw.count(b"\n") + (0 if raw.endswith(b"\n") else 1)


def _extract_symbols(raw: bytes) -> list[str]:
    text = raw[:SYMBOL_SCAN_LIMIT_BYTES].decode("utf-8", "replace")
    found: list[str] = []
    seen: set[str] = set()
    for pattern in SYMBOL_PATTERNS:
        for match in pattern.finditer(text):
            symbol = match.group(1)
            if symbol not in seen:
                found.append(symbol)
                seen.add(symbol)
            if len(found) >= 40:
                return found
    return found


def _row_for_entry(
    archive_name: str,
    info: zipfile.ZipInfo,
    *,
    license_name: str,
    license_stance: str,
    direct_source_use: bool,
    profile: dict[str, str],
    zf: zipfile.ZipFile,
) -> tuple[dict[str, Any], dict[str, int]]:
    path = info.filename
    text_candidate = _is_text(path)
    vendored = _is_vendored(path)
    raw = b""
    read_error = ""
    if text_candidate:
        try:
            raw = zf.read(info)
        except Exception as exc:  # pragma: no cover - archive-specific corruption
            read_error = str(exc)
    lines = _line_count(raw) if text_candidate and not read_error else ""
    symbols = _extract_symbols(raw) if text_candidate and not read_error else []
    coverage = "binary-manifest-only"
    if text_candidate and not read_error:
        coverage = "full-line-count+symbol-scan"
        if len(raw) > SYMBOL_SCAN_LIMIT_BYTES:
            coverage = "full-line-count+prefix-symbol-scan"
    elif read_error:
        coverage = "read-error"
    direct = "blocked"
    if direct_source_use and not vendored:
        direct = "candidate-after-path-level-review"
    risk = "low-review-required" if direct_source_use else "high-clean-room-only"
    if vendored:
        risk = "blocked-vendored-dependency"
    notes = "Automated archive inventory. Manual spot-reading is required before adoption."
    if read_error:
        notes = f"Archive read error: {read_error}"
    elif len(raw) > SYMBOL_SCAN_LIMIT_BYTES:
        notes = "Line count covers the full file; symbols are extracted from the first 2 MB. Direct adoption is blocked until manual review."
    stats = {
        "text_files": 1 if text_candidate else 0,
        "lines": int(lines) if isinstance(lines, int) else 0,
        "symbols": len(symbols),
        "vendored": 1 if vendored else 0,
        "errors": 1 if read_error else 0,
        "prefix_scans": 1 if len(raw) > SYMBOL_SCAN_LIMIT_BYTES else 0,
    }
    return (
        {
            "archive": archive_name,
            "project": _project_name(archive_name),
            "path": path,
            "file_type": Path(path).suffix.lower() or "[no-extension]",
            "size": info.file_size,
            "line_count": lines,
            "detected_license": license_name,
            "license_stance": license_stance,
            "direct_source_reuse": direct,
            "behavior_reuse": "yes-clean-room",
            "relevant_symbols": " | ".join(symbols),
            "ui_patterns": profile["ui"],
            "data_patterns": profile["data"],
            "algorithms": profile["algorithms"],
            "product_ideas": profile["ideas"],
            "legal_risk": risk,
            "adoption_target": profile["target"],
            "coverage": coverage,
            "vendored": vendored,
            "sha256_16": hashlib.sha256(raw).hexdigest()[:16] if raw else "",
            "notes": notes,
        },
        stats,
    )


def build_inventory(external_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    external_dir = external_dir.resolve()
    rows: list[dict[str, Any]] = []
    archive_summaries: list[dict[str, Any]] = []
    license_rows: list[dict[str, Any]] = []
    totals: Counter[str] = Counter()

    for archive_path in sorted(external_dir.glob("*.zip")):
        archive_stats: Counter[str] = Counter()
        with zipfile.ZipFile(archive_path) as zf:
            infos = [info for info in zf.infolist() if not info.is_dir()]
            decision = _collect_license_decision(zf, [info.filename for info in infos])
            license_rows.append(
                {
                    "archive": archive_path.name,
                    "project": _project_name(archive_path.name),
                    "detected_license": decision.detected_license,
                    "license_stance": decision.license_stance,
                    "direct_source_use": decision.direct_source_use,
                    "caveat": decision.caveat,
                    "evidence": [asdict(item) for item in decision.evidence],
                }
            )
            profile = _project_profile(archive_path.name)
            for info in infos:
                row, stats = _row_for_entry(
                    archive_path.name,
                    info,
                    license_name=decision.detected_license,
                    license_stance=decision.license_stance,
                    direct_source_use=decision.direct_source_use,
                    profile=profile,
                    zf=zf,
                )
                rows.append(row)
                archive_stats.update(stats)
                archive_stats["files"] += 1
                archive_stats["bytes"] += info.file_size
        totals.update(archive_stats)
        archive_summaries.append({"archive": archive_path.name, **dict(archive_stats)})

    root_container = ROOT / "external.zip"
    container = {
        "path": "external.zip",
        "exists": root_container.exists(),
        "size": root_container.stat().st_size if root_container.exists() else 0,
        "classification": "duplicate-container-of-external-archives",
        "double_indexed": False,
    }
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "external_dir": _display_external_dir(external_dir),
        "archive_count": len(archive_summaries),
        "totals": dict(totals),
        "archives": archive_summaries,
        "licenses": license_rows,
        "root_external_zip": container,
        "coverage": {
            "all_archive_entries_manifested": True,
            "all_text_candidates_full_line_counted": totals["errors"] == 0,
            "symbol_scan_limit_bytes": SYMBOL_SCAN_LIMIT_BYTES,
            "manual_all_lines_read": False,
            "manual_review_policy": "Direct adoption is blocked until cited path/line manual review and license verification.",
            "missing_extracted_external_root": not (ROOT / "external").exists(),
        },
    }
    return rows, summary


def _display_external_dir(external_dir: Path) -> str:
    try:
        return external_dir.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return external_dir.name


def write_outputs(rows: list[dict[str, Any]], summary: dict[str, Any], csv_path: Path, json_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the Phase 5F full external archive inventory.")
    parser.add_argument("--external-dir", default=str(DEFAULT_EXTERNAL_DIR))
    parser.add_argument("--csv", default=str(DEFAULT_OUTPUT_CSV))
    parser.add_argument("--json", default=str(DEFAULT_OUTPUT_JSON))
    args = parser.parse_args(argv)

    rows, summary = build_inventory(Path(args.external_dir))
    write_outputs(rows, summary, Path(args.csv), Path(args.json))
    print(
        json.dumps(
            {
                "archive_count": summary["archive_count"],
                "file_count": summary["totals"].get("files", 0),
                "text_file_count": summary["totals"].get("text_files", 0),
                "line_count": summary["totals"].get("lines", 0),
                "symbol_count": summary["totals"].get("symbols", 0),
                "read_errors": summary["totals"].get("errors", 0),
                "csv": str(Path(args.csv)),
                "json": str(Path(args.json)),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
