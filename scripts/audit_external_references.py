from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import zipfile
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXTERNAL_DIR = ROOT / "external (2)" / "external"
DEFAULT_OUTPUT_DIR = ROOT / "review_workspace" / "external2_analysis" / "phase2e"
AUDIT_TIMESTAMP = "2026-06-16T00:00:00+00:00"

TEXT_EXTENSIONS = {
    ".c",
    ".cc",
    ".cfg",
    ".conf",
    ".cpp",
    ".cs",
    ".css",
    ".csv",
    ".go",
    ".h",
    ".hpp",
    ".html",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".mdx",
    ".mjs",
    ".py",
    ".rs",
    ".sh",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}

TEXT_BASENAMES = {
    "license",
    "license.md",
    "license.txt",
    "licence",
    "copying",
    "notice",
    "readme",
    "readme.md",
    "package.json",
    "pyproject.toml",
    "setup.py",
    "requirements.txt",
}

LICENSE_BASENAME_RE = re.compile(r"(^|/)(license|licence|copying|notice)(\.|$)", re.IGNORECASE)
METADATA_BASENAMES = {"readme.md", "package.json", "pyproject.toml", "setup.py", "cargo.toml", "go.mod"}
VENDORED_PATH_PARTS = {"node_modules", ".git", ".next", "dist", "build", "target", "__pycache__"}
LINE_INVENTORY_MAX_BYTES = 2_000_000


@dataclass(frozen=True)
class EvidenceRef:
    path: str
    line_range: str
    snippet: str


@dataclass(frozen=True)
class LicenseDecision:
    detected_license: str
    license_stance: str
    direct_source_use: bool
    evidence: list[EvidenceRef] = field(default_factory=list)
    caveat: str = ""


@dataclass(frozen=True)
class FeatureCandidate:
    external_project: str
    external_archive: str
    external_file_path: str
    line_range: str
    observed_behavior: str
    license_stance: str
    local_implementation_target: str
    required_tests: list[str]
    product_value: str
    risk_caveat: str
    evidence_snippet: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _relative_to_root(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.name


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return _relative_to_root(value)
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    return str(value)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=_json_default) + "\n", encoding="utf-8")


def _zip_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_vendored(path: str) -> bool:
    return any(part in VENDORED_PATH_PARTS for part in Path(path).parts)


def _is_text_candidate(path: str) -> bool:
    lowered = path.lower()
    basename = Path(lowered).name
    return basename in TEXT_BASENAMES or Path(lowered).suffix in TEXT_EXTENSIONS


def _read_text(zf: zipfile.ZipFile, path: str, *, max_bytes: int | None = None) -> str:
    raw = zf.read(path)
    if max_bytes is not None:
        raw = raw[:max_bytes]
    return raw.decode("utf-8", "replace")


def _clean_snippet(text: str, limit: int = 280) -> str:
    snippet = " ".join(text.replace("\x00", " ").split())
    return snippet[:limit]


def _line_ref_for_pattern(
    zf: zipfile.ZipFile,
    path: str,
    patterns: Iterable[str],
    *,
    context_before: int = 0,
    context_after: int = 2,
) -> EvidenceRef:
    names = set(zf.namelist())
    if path not in names:
        return EvidenceRef(path=path, line_range="missing", snippet="File was not present in the refreshed archive.")
    text = _read_text(zf, path, max_bytes=500_000)
    lines = text.splitlines()
    lowered_patterns = [pattern.lower() for pattern in patterns]
    match_index = 0
    for idx, line in enumerate(lines):
        line_lower = line.lower()
        if any(pattern in line_lower for pattern in lowered_patterns):
            match_index = idx
            break
    start = max(0, match_index - context_before)
    end = min(len(lines), match_index + context_after + 1)
    if not lines:
        return EvidenceRef(path=path, line_range="1-1", snippet="")
    snippet = " ".join(line.strip() for line in lines[start:end] if line.strip())
    return EvidenceRef(path=path, line_range=f"{start + 1}-{end}", snippet=_clean_snippet(snippet))


def _line_ref_for_csv_header(zf: zipfile.ZipFile, path: str) -> EvidenceRef:
    names = set(zf.namelist())
    if path not in names:
        return EvidenceRef(path=path, line_range="missing", snippet="File was not present in the refreshed archive.")
    text = _read_text(zf, path, max_bytes=20_000)
    reader = csv.reader(text.splitlines())
    header = next(reader, [])
    sample = ", ".join(header)
    return EvidenceRef(path=path, line_range="1-1", snippet=_clean_snippet(sample))


def _detect_license_from_text(path: str, text: str) -> tuple[str, str, bool, str]:
    lowered = text.lower()
    basename = Path(path).name.lower()
    is_license_body = basename.startswith(("license", "licence", "copying", "notice"))
    if "gnu affero general public license" in lowered or "agpl-3.0" in lowered:
        return (
            "AGPL-3.0",
            "behavior-only",
            False,
            "Copyleft/network-source obligations make direct source copying unsuitable for the proprietary product boundary.",
        )
    if "nasa open source agreement" in lowered:
        return (
            "NASA-1.3",
            "behavior-only",
            False,
            "NASA Open Source Agreement requires separate legal review before direct source use.",
        )
    if "apache license" in lowered or "apache-2.0" in lowered:
        return ("Apache-2.0", "direct-use-allowed", True, "Permissive license detected; still prefer native minimal adoption.")
    readme_mit_heading = bool(re.search(r"#+\s*license\s+mit\b|#+\s*license\s+this project is licensed under the mit license", lowered))
    if "mit license" in lowered or 'license = {text = "mit"}' in lowered or '"license": "mit"' in lowered or readme_mit_heading:
        if is_license_body or basename in {"package.json", "pyproject.toml", "setup.py"}:
            return ("MIT", "direct-use-allowed", True, "Permissive license detected; retain notice for direct adaptations.")
        return ("MIT-readme-only", "needs-review", False, "README mentions MIT, but no full license text was found in this archive.")
    return ("unknown", "needs-review", False, "No recognized license pattern found in this metadata file.")


def _collect_license_decision(zf: zipfile.ZipFile, names: list[str]) -> LicenseDecision:
    evidence: list[EvidenceRef] = []
    ranked: list[tuple[str, str, bool, str, EvidenceRef]] = []
    root_ranked: list[tuple[str, str, bool, str, EvidenceRef]] = []
    candidates = [
        name
        for name in names
        if not name.endswith("/")
        and not _is_vendored(name)
        and (LICENSE_BASENAME_RE.search(name) or Path(name).name.lower() in METADATA_BASENAMES)
    ]
    for path in candidates:
        try:
            text = _read_text(zf, path, max_bytes=80_000)
        except Exception:
            continue
        detected, stance, direct, caveat = _detect_license_from_text(path, text)
        if detected == "unknown" and "license" not in text.lower():
            continue
        ref = _line_ref_for_pattern(zf, path, ["license", "gnu affero", "apache", "mit", "nasa"], context_after=2)
        evidence.append(ref)
        if detected != "unknown":
            ranked.append((detected, stance, direct, caveat, ref))
            parts = Path(path).parts
            if len(parts) <= 2 and LICENSE_BASENAME_RE.search(path):
                root_ranked.append((detected, stance, direct, caveat, ref))

    priority = {
        "AGPL-3.0": 0,
        "NASA-1.3": 1,
        "Apache-2.0": 2,
        "MIT": 3,
        "MIT-readme-only": 4,
    }
    if root_ranked:
        root_ranked.sort(key=lambda item: priority.get(item[0], 99))
        detected, stance, direct, caveat, _ = root_ranked[0]
        conflicting_copyleft = sorted(
            {
                item[0]
                for item in ranked
                if item[0] in {"AGPL-3.0", "NASA-1.3"} and item[0] != detected
            }
        )
        if direct and conflicting_copyleft:
            return LicenseDecision(
                detected_license=f"{detected} root + {'/'.join(conflicting_copyleft)} subcomponent",
                license_stance="needs-review",
                direct_source_use=False,
                evidence=evidence[:12],
                caveat="Root license is permissive, but at least one subcomponent declares a restrictive license; use only behavior or separately reviewed paths.",
            )
        return LicenseDecision(detected, stance, direct, evidence[:12], caveat)

    if ranked:
        ranked.sort(key=lambda item: priority.get(item[0], 99))
        detected, stance, direct, caveat, _ = ranked[0]
        return LicenseDecision(detected, stance, direct, evidence[:12], caveat)

    return LicenseDecision(
        detected_license="missing",
        license_stance="blocked",
        direct_source_use=False,
        evidence=evidence[:12],
        caveat="No usable project license evidence found in the archive metadata; direct source copying is blocked.",
    )


def _project_name(archive_name: str) -> str:
    for suffix in ("-main.zip", "-master.zip", "-develop.zip", ".zip"):
        if archive_name.endswith(suffix):
            return archive_name[: -len(suffix)]
    return archive_name


def _candidate(
    *,
    project: str,
    archive: str,
    evidence: EvidenceRef,
    observed_behavior: str,
    license_stance: str,
    target: str,
    tests: list[str],
    value: str,
    caveat: str,
) -> FeatureCandidate:
    return FeatureCandidate(
        external_project=project,
        external_archive=archive,
        external_file_path=evidence.path,
        line_range=evidence.line_range,
        observed_behavior=observed_behavior,
        license_stance=license_stance,
        local_implementation_target=target,
        required_tests=tests,
        product_value=value,
        risk_caveat=caveat,
        evidence_snippet=evidence.snippet,
    )


def _build_feature_candidates_for_archive(
    zf: zipfile.ZipFile,
    archive_name: str,
    license_decision: LicenseDecision,
) -> list[FeatureCandidate]:
    names = set(zf.namelist())
    project = _project_name(archive_name)
    candidates: list[FeatureCandidate] = []

    def exists(path: str) -> bool:
        return path in names

    if archive_name == "FinanceDatabase-main.zip":
        candidates.append(
            _candidate(
                project=project,
                archive=archive_name,
                evidence=_line_ref_for_pattern(zf, "FinanceDatabase-main/pyproject.toml", ["description", "license"], context_after=4),
                observed_behavior="Defines a broad market reference database spanning equities, ETFs, funds, indices, currencies, cryptocurrencies, and money markets under MIT metadata.",
                license_stance="direct-use-allowed",
                target="lib/asset_universe.py, lib/api_contracts.py, static/api-fixtures/asset-universe.json, apps/web",
                tests=["tests/test_asset_universe_contracts.py", "tests/test_api_fixture_export.py", "npm --prefix apps/web test"],
                value="Adds a commercial workstation reference-universe view without claiming live market coverage.",
                caveat="Do not vendor the full external CSV database in this slice; expose native schema/readiness contracts first.",
            )
        )
        for path, label in [
            ("FinanceDatabase-main/database/equities/NMS.csv", "equity schema"),
            ("FinanceDatabase-main/database/cryptos.csv", "crypto pair schema"),
            ("FinanceDatabase-main/database/currencies.csv", "FX pair schema"),
            ("FinanceDatabase-main/database/indices.csv", "index schema"),
            ("FinanceDatabase-main/database/moneymarkets.csv", "money-market schema"),
        ]:
            if exists(path):
                candidates.append(
                    _candidate(
                        project=project,
                        archive=archive_name,
                        evidence=_line_ref_for_csv_header(zf, path),
                        observed_behavior=f"Provides {label} columns suitable for a normalized asset-universe contract.",
                        license_stance="direct-use-allowed",
                        target="lib/asset_universe.py JSON-safe schema definitions",
                        tests=["tests/test_asset_universe_contracts.py"],
                        value="Gives terminal search, watchlists, and command routing a consistent asset metadata spine.",
                        caveat="Header/schema concepts are adopted; row data is not copied into first-party fixtures.",
                    )
                )
    elif archive_name == "supabase-master.zip":
        candidates.append(
            _candidate(
                project=project,
                archive=archive_name,
                evidence=_line_ref_for_pattern(zf, "supabase-master/README.md", ["Hosted Postgres", "Authentication", "Auto-generated APIs"], context_after=6),
                observed_behavior="Frames a commercial app around hosted database, authentication/authorization, generated APIs, realtime, storage, and edge functions.",
                license_stance=license_decision.license_stance,
                target="Future account/watchlist/schema readiness surface; no hosted auth or billing added in Phase 2E.",
                tests=["tests/test_api_contracts.py", "npm --prefix apps/web test"],
                value="Clarifies the product-readiness checklist for accounts, persistence, and API surfaces.",
                caveat="Architecture reference only in this slice; do not copy Studio components or add hosted Supabase dependency.",
            )
        )
    elif archive_name == "helix-db-main.zip":
        candidates.append(
            _candidate(
                project=project,
                archive=archive_name,
                evidence=_line_ref_for_pattern(zf, "helix-db-main/README.md", ["graph-vector database", "knowledge graphs"], context_after=2),
                observed_behavior="Positions graph/vector storage as a knowledge-graph and AI-memory model.",
                license_stance=license_decision.license_stance,
                target="Future clean-room event-to-asset graph contract from War Room/news/provider payloads.",
                tests=["tests/test_api_contracts.py"],
                value="Helps convert source-backed events into linked assets, sectors, countries, commodities, and crypto exposures.",
                caveat="Graph/query behavior should be recreated natively; no Rust/SDK source is copied.",
            )
        )
    elif archive_name == "dexter-main.zip":
        candidates.append(
            _candidate(
                project=project,
                archive=archive_name,
                evidence=_line_ref_for_pattern(zf, "dexter-main/README.md", ["task planning", "self-reflection", "real-time market data"], context_after=4),
                observed_behavior="Describes a finance-focused assistant that plans tasks, checks its work, and refines answers with market data.",
                license_stance="needs-review",
                target="Future constrained command/assistant workflow shell using existing Gemini-free-first status.",
                tests=["tests/test_ai_safety.py", "tests/test_api_contracts.py"],
                value="Useful for turning terminal commands into auditable research workflows.",
                caveat="README mentions MIT but no full license file is present; keep behavior-only until license text is confirmed.",
            )
        )
    elif archive_name == "BB-Terminal-main.zip":
        candidates.extend(
            [
                _candidate(
                    project=project,
                    archive=archive_name,
                    evidence=_line_ref_for_pattern(zf, "BB-Terminal-main/app/src/components/CommandBar.tsx", ["parseCommand", "FUNCTIONS"], context_after=3),
                    observed_behavior="Command bar parses terminal-style functions and updates workspace state.",
                    license_stance="blocked",
                    target="Future clean-room terminal command parser and web command palette.",
                    tests=["tests/test_financial_terminal.py", "npm --prefix apps/web test"],
                    value="Command-first workflow is core to a serious daily-use market terminal.",
                    caveat="No usable license signal found; behavior can be reimplemented, source cannot be copied.",
                ),
                _candidate(
                    project=project,
                    archive=archive_name,
                    evidence=_line_ref_for_pattern(zf, "BB-Terminal-main/app/src/lib/signals.ts", ["heuristics", "SignalLevel"], context_after=3),
                    observed_behavior="Rule-based signal classifiers return explainable bull/bear/neutral/na levels.",
                    license_stance="blocked",
                    target="Future native lib/equity_signal_rules.py with transparent diagnostics.",
                    tests=["tests/test_fundamentals.py", "tests/test_financial_terminal.py"],
                    value="Provides explainability without making opaque trading predictions.",
                    caveat="No source copying; recreate rules from first-principles finance definitions.",
                ),
            ]
        )
    elif archive_name == "bloomberg-terminal-main.zip":
        candidates.append(
            _candidate(
                project=project,
                archive=archive_name,
                evidence=_line_ref_for_pattern(zf, "bloomberg-terminal-main/components/bloomberg/core/watchlist.tsx", ["WatchlistItem", "isSelected"], context_after=4),
                observed_behavior="Maintains selectable watchlist items inside a dense terminal UI.",
                license_stance=license_decision.license_stance,
                target="Future web watchlist/session state with source-status-aware rows.",
                tests=["npm --prefix apps/web test", "npm --prefix apps/web run build"],
                value="Dense watchlist scanning is a B2C retention feature.",
                caveat="README says MIT but no full license text was found in the archive; use UI concept only unless direct-use notice is separately retained.",
            )
        )
    elif archive_name == "OpenBB-develop.zip":
        candidates.append(
            _candidate(
                project=project,
                archive=archive_name,
                evidence=_line_ref_for_pattern(zf, "OpenBB-develop/openbb_platform/core/openbb_core/api/router/commands.py", ["command map", "Callable"], context_after=4),
                observed_behavior="Builds a command map over provider routes and callable functions.",
                license_stance="behavior-only",
                target="Optional user-installed OpenBB bridge and native route manifest extensions.",
                tests=["tests/test_api_contracts.py", "tests/test_financial_terminal.py"],
                value="Standardizes market provider command contracts.",
                caveat="AGPL source boundary; use OpenBB as optional installed package/API, never vendored source.",
            )
        )
    elif archive_name == "OpenAlice-master.zip":
        candidates.append(
            _candidate(
                project=project,
                archive=archive_name,
                evidence=_line_ref_for_pattern(zf, "OpenAlice-master/packages/opentypebb/src/core/provider/registry.ts", ["Provider Registry", "registry"], context_after=4),
                observed_behavior="Maintains a provider registry mapping available providers.",
                license_stance="behavior-only",
                target="Future provider registry/readiness parity checks.",
                tests=["tests/test_api_contracts.py"],
                value="Provider registry thinking fits the API-ready terminal contract layer.",
                caveat="AGPL license blocks direct source adoption.",
            )
        )
    elif archive_name == "osiris-master.zip":
        candidates.append(
            _candidate(
                project=project,
                archive=archive_name,
                evidence=_line_ref_for_pattern(zf, "osiris-master/src/app/api/earthquakes/route.ts", ["USGS", "No API key"], context_after=5),
                observed_behavior="Uses a no-key USGS seismic endpoint with explicit real-time event semantics.",
                license_stance=license_decision.license_stance,
                target="Existing/future native lib/osint_sources.py natural-events provider and War Room layer.",
                tests=["tests/test_feed_registry.py", "tests/test_geo_layers.py"],
                value="Adds source-backed risk-map coverage without paid credentials.",
                caveat="MIT source permits direct adaptation with notice, but current project should keep native implementation.",
            )
        )
    elif archive_name == "worldmonitor-main.zip":
        candidates.append(
            _candidate(
                project=project,
                archive=archive_name,
                evidence=_line_ref_for_pattern(zf, "worldmonitor-main/api/health.js", ["outages", "market", "climate"], context_after=5),
                observed_behavior="Aggregates health/readiness signals across many provider domains.",
                license_stance="behavior-only",
                target="Existing provider health ledger and future commercial trust center.",
                tests=["tests/test_api_contracts.py", "tests/test_goal10b_no_fake_live_data.py"],
                value="Prevents fake-live UI by surfacing provider truth.",
                caveat="AGPL source boundary; only clean-room behavior may be used.",
            )
        )
    elif archive_name == "worldview-main.zip":
        candidates.append(
            _candidate(
                project=project,
                archive=archive_name,
                evidence=_line_ref_for_pattern(zf, "worldview-main/web/js/modules/compare/util.js", ["compare", "state"], context_after=4),
                observed_behavior="Maps location parameters into compare-mode state for time/layer map comparison.",
                license_stance="behavior-only",
                target="Future War Room timeline compare controls.",
                tests=["tests/test_geo_layers.py", "npm --prefix apps/web test"],
                value="Compare windows make map risk changes more useful than static markers.",
                caveat="NASA license requires separate review before direct source use.",
            )
        )
    elif archive_name == "QuantDinger-main.zip":
        candidates.append(
            _candidate(
                project=project,
                archive=archive_name,
                evidence=_line_ref_for_pattern(zf, "QuantDinger-main/README.md", ["AI research", "Backtest", "Paper/Live"], context_after=4),
                observed_behavior="Describes a quant workflow from AI research to strategy code, backtesting, paper/live execution, and monitoring.",
                license_stance=license_decision.license_stance,
                target="Future safe quant lab workflow checklist; no autonomous live trading in current product.",
                tests=["tests/test_ai_safety.py", "tests/test_goal10b_no_recommendation_language.py"],
                value="Useful workflow language for quant diagnostics and monitoring.",
                caveat="Keep trading automation disabled unless explicit user approval and compliance gates exist.",
            )
        )
    elif archive_name == "tensortrade-master.zip":
        candidates.append(
            _candidate(
                project=project,
                archive=archive_name,
                evidence=_line_ref_for_pattern(zf, "tensortrade-master/README.md", ["trading", "environment", "reinforcement"], context_after=4),
                observed_behavior="Provides trading-environment architecture for experimentation and reinforcement-learning workflows.",
                license_stance=license_decision.license_stance,
                target="Future sandboxed research-lab environment metadata only.",
                tests=["tests/test_ai_safety.py"],
                value="Can inform simulation boundaries without turning the product into an auto-trader.",
                caveat="Do not ship trading agents or RL execution as investment advice.",
            )
        )
    elif archive_name == "Kronos-master.zip":
        candidates.append(
            _candidate(
                project=project,
                archive=archive_name,
                evidence=_line_ref_for_pattern(zf, "Kronos-master/README.md", ["time series", "forecast"], context_after=4),
                observed_behavior="Time-series forecasting reference with model/web UI materials.",
                license_stance=license_decision.license_stance,
                target="Future forecast-readiness contract with explicit uncertainty and no recommendation language.",
                tests=["tests/test_goal10b_no_recommendation_language.py"],
                value="Can improve scenario framing when paired with transparent caveats.",
                caveat="Forecasting must remain explanatory and source-quality aware.",
            )
        )
    elif archive_name == "OpenStock-main.zip":
        candidates.append(
            _candidate(
                project=project,
                archive=archive_name,
                evidence=_line_ref_for_pattern(zf, "OpenStock-main/README.md", ["stock", "market"], context_after=4),
                observed_behavior="Market app reference for stock tracking and portfolio/product UX.",
                license_stance=license_decision.license_stance,
                target="Future clean-room market app UX review only.",
                tests=["npm --prefix apps/web test"],
                value="Can inform retail market workflows after stronger license analysis.",
                caveat="Archive license is AGPL; direct code adoption is blocked.",
            )
        )
    elif archive_name == "optlib-master.zip":
        candidates.append(
            _candidate(
                project=project,
                archive=archive_name,
                evidence=_line_ref_for_pattern(zf, "optlib-master/README.md", ["option", "volatility"], context_after=4),
                observed_behavior="Small option utility reference.",
                license_stance=license_decision.license_stance,
                target="Future native option diagnostics utilities if needed.",
                tests=["tests/test_options_provider_capabilities.py"],
                value="Useful for option analytics after contract gaps are closed.",
                caveat="Prefer first-party implementation unless exact formula adaptation is justified and attributed.",
            )
        )
    elif archive_name == "quant-traderr-lab-main.zip":
        candidates.append(
            _candidate(
                project=project,
                archive=archive_name,
                evidence=_line_ref_for_pattern(zf, "quant-traderr-lab-main/README.md", ["quant", "trading", "lab"], context_after=4),
                observed_behavior="Quant research lab reference with strategy-analysis notebooks.",
                license_stance=license_decision.license_stance,
                target="Future native quant lab scenario/diagnostic contracts.",
                tests=["tests/test_factor_engine.py", "tests/test_global_volatility_monitor.py"],
                value="Supports advanced user retention through research workflows.",
                caveat="No strategy code copied; keep output diagnostic, not advice.",
            )
        )
    elif archive_name == "agent-skills-main.zip":
        candidates.append(
            _candidate(
                project=project,
                archive=archive_name,
                evidence=_line_ref_for_pattern(zf, "agent-skills-main/skills/api-and-interface-design/SKILL.md", ["Contract First", "Validate at Boundaries"], context_after=4),
                observed_behavior="Workflow guidance for contract-first API design and boundary validation.",
                license_stance=license_decision.license_stance,
                target="Phase 2E audit/product workflow reference only.",
                tests=["tests/test_external_reference_audit.py", "tests/test_api_contracts.py"],
                value="Improves process quality without runtime dependency.",
                caveat="Do not vendor or install the external workflow project.",
            )
        )

    return candidates


def _archive_inventory(zpath: Path) -> dict[str, Any]:
    with zipfile.ZipFile(zpath) as zf:
        infos = sorted(zf.infolist(), key=lambda item: item.filename)
        files = []
        extension_counts: Counter[str] = Counter()
        top_level_counts: Counter[str] = Counter()
        total_uncompressed = 0
        for info in infos:
            parts = Path(info.filename).parts
            top_level_counts[parts[0] if parts else ""] += 1
            if not info.is_dir():
                ext = Path(info.filename).suffix.lower() or "[no-extension]"
                extension_counts[ext] += 1
                total_uncompressed += info.file_size
            files.append(
                {
                    "path": info.filename,
                    "size": info.file_size,
                    "compressed_size": info.compress_size,
                    "crc": f"{info.CRC:08x}",
                    "is_dir": info.is_dir(),
                }
            )
        return {
            "archive": zpath.name,
            "zip_sha256": _zip_sha256(zpath),
            "zip_size": zpath.stat().st_size,
            "file_count": sum(1 for info in infos if not info.is_dir()),
            "directory_count": sum(1 for info in infos if info.is_dir()),
            "uncompressed_size": total_uncompressed,
            "top_level_entries": dict(sorted(top_level_counts.items())),
            "extension_counts": dict(sorted(extension_counts.items())),
            "files": files,
        }


def _archive_line_inventory(zpath: Path) -> dict[str, Any]:
    indexed_files: list[dict[str, Any]] = []
    skipped_large: list[dict[str, Any]] = []
    skipped_vendored = 0
    total_lines = 0
    with zipfile.ZipFile(zpath) as zf:
        for info in sorted(zf.infolist(), key=lambda item: item.filename):
            if info.is_dir() or not _is_text_candidate(info.filename):
                continue
            if _is_vendored(info.filename):
                skipped_vendored += 1
                continue
            if info.file_size > LINE_INVENTORY_MAX_BYTES:
                skipped_large.append({"path": info.filename, "size": info.file_size, "reason": "over_line_inventory_max_bytes"})
                continue
            try:
                raw = zf.read(info.filename)
            except Exception as exc:
                indexed_files.append({"path": info.filename, "size": info.file_size, "error": str(exc)})
                continue
            text = raw.decode("utf-8", "replace")
            line_count = 0 if not text else text.count("\n") + (0 if text.endswith("\n") else 1)
            total_lines += line_count
            indexed_files.append(
                {
                    "path": info.filename,
                    "size": info.file_size,
                    "line_count": line_count,
                    "sha256_16": hashlib.sha256(raw).hexdigest()[:16],
                }
            )
    return {
        "archive": zpath.name,
        "indexed_text_file_count": len(indexed_files),
        "total_indexed_lines": total_lines,
        "skipped_large_text_files": skipped_large,
        "skipped_vendored_text_file_count": skipped_vendored,
        "coverage_note": "Zip manifest indexes every entry; line inventory indexes non-vendored text/code files up to the configured size cap.",
        "files": indexed_files,
    }


def build_external_audit(
    external_dir: Path | str = DEFAULT_EXTERNAL_DIR,
    *,
    output_dir: Path | str | None = None,
    generated_at: str = AUDIT_TIMESTAMP,
) -> dict[str, Any]:
    external_path = Path(external_dir)
    zip_paths = sorted(external_path.glob("*.zip"))
    inventories: list[dict[str, Any]] = []
    license_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    line_rows: list[dict[str, Any]] = []

    for zpath in zip_paths:
        inventories.append(_archive_inventory(zpath))
        line_rows.append(_archive_line_inventory(zpath))
        with zipfile.ZipFile(zpath) as zf:
            names = sorted(zf.namelist())
            license_decision = _collect_license_decision(zf, names)
            license_rows.append(
                {
                    "archive": zpath.name,
                    "project": _project_name(zpath.name),
                    "detected_license": license_decision.detected_license,
                    "license_stance": license_decision.license_stance,
                    "direct_source_use": license_decision.direct_source_use,
                    "caveat": license_decision.caveat,
                    "evidence": [asdict(item) for item in license_decision.evidence],
                }
            )
            candidate_rows.extend(
                asdict(candidate)
                for candidate in _build_feature_candidates_for_archive(zf, zpath.name, license_decision)
            )

    payloads = {
        "external_zip_inventory.json": {
            "generated_at": generated_at,
            "external_dir": _relative_to_root(external_path),
            "archive_count": len(inventories),
            "archives": inventories,
        },
        "external_license_matrix.json": {
            "generated_at": generated_at,
            "external_dir": _relative_to_root(external_path),
            "archive_count": len(license_rows),
            "archives": license_rows,
            "summary": dict(sorted(Counter(row["license_stance"] for row in license_rows).items())),
        },
        "external_feature_candidates.json": {
            "generated_at": generated_at,
            "external_dir": _relative_to_root(external_path),
            "candidate_count": len(candidate_rows),
            "candidates": candidate_rows,
            "summary": dict(sorted(Counter(row["license_stance"] for row in candidate_rows).items())),
        },
        "external_line_inventory.json": {
            "generated_at": generated_at,
            "external_dir": _relative_to_root(external_path),
            "archive_count": len(line_rows),
            "line_inventory_max_bytes": LINE_INVENTORY_MAX_BYTES,
            "archives": line_rows,
        },
    }

    if output_dir is not None:
        output_path = Path(output_dir)
        for name, payload in payloads.items():
            _write_json(output_path / name, payload)

    return payloads


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit external reference zip archives for Phase 2E.")
    parser.add_argument("--external-dir", default=str(DEFAULT_EXTERNAL_DIR), help="Directory containing external reference zip files.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for deterministic audit artifacts.")
    parser.add_argument(
        "--generated-at",
        default=AUDIT_TIMESTAMP,
        help="Timestamp to embed in deterministic artifacts; defaults to the Phase 2E date.",
    )
    args = parser.parse_args(argv)
    payloads = build_external_audit(args.external_dir, output_dir=args.output_dir, generated_at=args.generated_at)
    summary = {
        "output_dir": _relative_to_root(Path(args.output_dir)),
        "archives": payloads["external_zip_inventory.json"]["archive_count"],
        "feature_candidates": payloads["external_feature_candidates.json"]["candidate_count"],
        "license_summary": payloads["external_license_matrix.json"]["summary"],
        "generated_at": args.generated_at,
    }
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
