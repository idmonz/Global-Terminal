from __future__ import annotations

from typing import Any

_TOOL_SECTIONS: list[dict[str, Any]] = [
    {
        "section": "Data Provider Tools",
        "tools": [
            {"tool_name": "Run Provider Probe", "workflow_action": "RUN_PROVIDER_PROBE_DRY_RUN", "purpose": "Check configured provider availability and source metadata.", "command": "DATA PROBE", "page": "pages/17_Data_Provider_Center.py", "data_required": "provider registry", "output_type": "provider status", "caveat": "Optional keys may be missing.", "research_only": True},
            {"tool_name": "Generate Provider Health Report", "workflow_action": "GENERATE_PROVIDER_REPORT", "purpose": "Create a source-labeled provider health report.", "command": "GENERATE PROVIDER REPORT", "page": "pages/21_Report_Inbox.py", "data_required": "provider snapshots", "output_type": "report", "caveat": "Manual report generation only.", "research_only": True},
            {"tool_name": "Inspect Data Quality", "workflow_action": "INSPECT_DATA_QUALITY", "purpose": "Review freshness, gaps, and proxy labels.", "command": "DATA QUALITY REPORT", "page": "pages/21_Report_Inbox.py", "data_required": "data quality snapshots", "output_type": "diagnostic", "caveat": "Unknown freshness remains unknown.", "research_only": True},
        ],
    },
    {
        "section": "Watchlist Tools",
        "tools": [
            {"tool_name": "Quick Add Watchlist Item", "workflow_action": "ADD_WATCHLIST_ITEM", "purpose": "Create a local research watch item.", "command": "ADD WATCHLIST", "page": "pages/20_Watchlist_Alerts.py", "data_required": "symbol or topic", "output_type": "watchlist item", "caveat": "No market values are fabricated.", "research_only": True},
            {"tool_name": "Evaluate Alerts Now", "workflow_action": "EVALUATE_ALERTS_NOW", "purpose": "Manually evaluate alert conditions using supplied context.", "command": "EVALUATE ALERTS", "page": "pages/20_Watchlist_Alerts.py", "data_required": "alert rules and context", "output_type": "alert events", "caveat": "Manual evaluation only.", "research_only": True},
            {"tool_name": "Generate Watchlist Brief", "workflow_action": "GENERATE_WATCHLIST_BRIEF", "purpose": "Create a manual watchlist research brief.", "command": "GENERATE WATCHLIST BRIEF", "page": "pages/21_Report_Inbox.py", "data_required": "watchlist and linked context", "output_type": "report", "caveat": "Source caveats remain visible.", "research_only": True},
        ],
    },
    {
        "section": "Report Tools",
        "tools": [
            {"tool_name": "Generate War Room Brief", "workflow_action": "GENERATE_WAR_ROOM_BRIEF", "purpose": "Summarize supplied OSINT and region context.", "command": "GENERATE WAR ROOM BRIEF", "page": "pages/21_Report_Inbox.py", "data_required": "event context", "output_type": "report", "caveat": "Low-confidence events stay unconfirmed.", "research_only": True},
            {"tool_name": "Export Workspace JSON", "workflow_action": "EXPORT_WORKSPACE_JSON", "purpose": "Export local research workspace state.", "command": "EXPORT WORKSPACE JSON", "page": "pages/19_Research_Workspace.py", "data_required": "SQLite workspace", "output_type": "JSON", "caveat": "Private export path is local.", "research_only": True},
            {"tool_name": "Backup Workspace DB", "workflow_action": "BACKUP_WORKSPACE_DB", "purpose": "Create a local database backup.", "command": "BACKUP WORKSPACE DB", "page": "pages/19_Research_Workspace.py", "data_required": "SQLite workspace", "output_type": "DB backup", "caveat": "Release package excludes private DB files.", "research_only": True},
        ],
    },
    {
        "section": "Strategy Review Tools",
        "tools": [
            {"tool_name": "Create Strategy Commit", "workflow_action": "CREATE_STRATEGY_COMMIT", "purpose": "Record a research snapshot and guard results.", "command": "COMMIT STRATEGY", "page": "pages/22_Strategy_Decision_Log.py", "data_required": "strategy candidate notes", "output_type": "commit", "caveat": "Research record only.", "research_only": True},
            {"tool_name": "Generate Strategy Review", "workflow_action": "GENERATE_STRATEGY_REVIEW", "purpose": "Create a report from commit, guard, and tracking context.", "command": "GENERATE STRATEGY REVIEW", "page": "pages/21_Report_Inbox.py", "data_required": "strategy commits", "output_type": "report", "caveat": "Guard warnings require human review.", "research_only": True},
        ],
    },
    {
        "section": "OSINT Tools",
        "tools": [
            {"tool_name": "Build War Room Brief", "workflow_action": "BUILD_WAR_ROOM_CONTEXT", "purpose": "Transform supplied events into source-labeled briefing context.", "command": "GLOBAL WAR", "page": "pages/14_War_Room.py", "data_required": "event payloads", "output_type": "intel feed", "caveat": "No live stream claim without provider status.", "research_only": True},
            {"tool_name": "Inspect View Presets", "workflow_action": "INSPECT_VIEW_PRESETS", "purpose": "Switch region/layer presets for research dashboards.", "command": "VIEW PRESETS", "page": "pages/19_Research_Workspace.py", "data_required": "preset catalog", "output_type": "view state", "caveat": "Presets do not create data.", "research_only": True},
        ],
    },

    {
        "section": "Options & Quant Model Lab Tools",
        "tools": [
            {"tool_name": "Price Option", "workflow_action": "PRICE_OPTION", "purpose": "Calculate a local European option model value from supplied inputs.", "command": "PRICE OPTION", "page": "pages/24_Options_Quant_Model_Lab.py", "data_required": "option input payload", "output_type": "options pricing result", "caveat": "Supplied-data calculation only; no live option chain is fetched.", "research_only": True},
            {"tool_name": "Solve Implied Volatility", "workflow_action": "SOLVE_IV", "purpose": "Solve implied volatility from supplied premium and validated inputs.", "command": "SOLVE IV", "page": "pages/24_Options_Quant_Model_Lab.py", "data_required": "option input payload + premium", "output_type": "IV solver result", "caveat": "Solver returns explicit failure when no bracketed solution exists.", "research_only": True},
            {"tool_name": "Build Payoff Scenario", "workflow_action": "PAYOFF_SCENARIO", "purpose": "Build deterministic option payoff/scenario tables from supplied legs.", "command": "PAYOFF SCENARIO", "page": "pages/24_Options_Quant_Model_Lab.py", "data_required": "option legs + price grid", "output_type": "payoff table", "caveat": "Mathematical payoff profile only.", "research_only": True},
            {"tool_name": "Generate Options Report", "workflow_action": "OPTIONS_REPORT", "purpose": "Create a local source-labeled options report.", "command": "OPTIONS REPORT", "page": "pages/21_Report_Inbox.py", "data_required": "option input payload", "output_type": "report", "caveat": "Report contains research-only disclosure and provider caveats.", "research_only": True},
            {"tool_name": "Attach Options Result to Strategy Commit", "workflow_action": "ATTACH_OPTIONS_RESULT_TO_STRATEGY_COMMIT", "purpose": "Attach an options result as a Strategy-as-Git artifact.", "command": "ATTACH OPTIONS RESULT", "page": "pages/22_Strategy_Decision_Log.py", "data_required": "commit_id + options result", "output_type": "strategy artifact", "caveat": "Attachment is a review artifact, not an approval.", "research_only": True},
            {"tool_name": "Create Quant Model Snapshot", "workflow_action": "CREATE_QUANT_MODEL_SNAPSHOT", "purpose": "Create a local model snapshot payload for review.", "command": "MODEL SNAPSHOT", "page": "pages/24_Options_Quant_Model_Lab.py", "data_required": "model metadata", "output_type": "model snapshot", "caveat": "No heavy runtime, inference, or training is invoked.", "research_only": True},
            {"tool_name": "Attach Model Snapshot to Report", "workflow_action": "ATTACH_MODEL_SNAPSHOT_TO_REPORT", "purpose": "Attach a quant model snapshot to the Report Inbox.", "command": "ATTACH MODEL RESULT", "page": "pages/21_Report_Inbox.py", "data_required": "model snapshot", "output_type": "report attachment", "caveat": "Local report artifact only.", "research_only": True},

            {"tool_name": "Import Option Chain CSV", "workflow_action": "IMPORT_OPTION_CHAIN_CSV", "purpose": "Parse a user-supplied option-chain CSV into a labeled local snapshot.", "command": "OPTION CHAIN", "page": "pages/24_Options_Quant_Model_Lab.py", "data_required": "uploaded CSV text or local rows", "output_type": "option-chain snapshot", "caveat": "Supplied CSV only; no live chain fetch.", "research_only": True},
            {"tool_name": "Build Vol Surface Snapshot", "workflow_action": "BUILD_VOL_SURFACE_SNAPSHOT", "purpose": "Build a volatility surface from supplied chain IV diagnostics.", "command": "VOL SURFACE", "page": "pages/24_Options_Quant_Model_Lab.py", "data_required": "option-chain snapshot", "output_type": "vol surface snapshot", "caveat": "Surface points are supplied-chain calculations only.", "research_only": True},
            {"tool_name": "Build Option Book Risk Snapshot", "workflow_action": "BUILD_OPTION_BOOK_RISK_SNAPSHOT", "purpose": "Aggregate contract-scaled Greeks from user-supplied local positions.", "command": "OPTION BOOK", "page": "pages/24_Options_Quant_Model_Lab.py", "data_required": "local option positions", "output_type": "option-book risk snapshot", "caveat": "No portfolio advice or rebalancing output.", "research_only": True},
            {"tool_name": "Generate Options Chain Report", "workflow_action": "OPTIONS_CHAIN_REPORT", "purpose": "Create a source-labeled option-chain quality and IV report.", "command": "OPTIONS CHAIN REPORT", "page": "pages/21_Report_Inbox.py", "data_required": "option-chain snapshot", "output_type": "report", "caveat": "CSV fields are escaped for report rendering.", "research_only": True},
            {"tool_name": "Generate Vol Surface Report", "workflow_action": "SURFACE_REPORT", "purpose": "Create a supplied-chain volatility-surface report.", "command": "SURFACE REPORT", "page": "pages/21_Report_Inbox.py", "data_required": "IV snapshot", "output_type": "report", "caveat": "No forecast claim is made.", "research_only": True},
            {"tool_name": "Generate Option Book Risk Report", "workflow_action": "OPTION_BOOK_REPORT", "purpose": "Create an option-book risk aggregation report from local positions.", "command": "OPTION BOOK REPORT", "page": "pages/21_Report_Inbox.py", "data_required": "local option positions", "output_type": "report", "caveat": "Risk aggregation only; no hedge instruction.", "research_only": True},
            {"tool_name": "Run Local Quant Diagnostics", "workflow_action": "RUN_LOCAL_QUANT_DIAGNOSTICS", "purpose": "Run deterministic supplied-series diagnostics for returns, correlation, volatility, and mean reversion.", "command": "QUANT DIAGNOSTICS", "page": "pages/24_Options_Quant_Model_Lab.py", "data_required": "local price series", "output_type": "quant diagnostics", "caveat": "No prediction, alpha, or trade-signal claim.", "research_only": True},
            {"tool_name": "Build Surface QA", "workflow_action": "BUILD_SURFACE_QA", "purpose": "Build no-arbitrage and quality diagnostics for a supplied surface.", "command": "SURFACE QA", "page": "pages/24_Options_Quant_Model_Lab.py", "data_required": "surface snapshot", "output_type": "surface qa", "caveat": "Supplied surface diagnostics only.", "research_only": True},
            {"tool_name": "Build Surface Diff", "workflow_action": "BUILD_SURFACE_DIFF", "purpose": "Compare two supplied surface snapshots.", "command": "SURFACE DIFF", "page": "pages/24_Options_Quant_Model_Lab.py", "data_required": "two surface snapshots", "output_type": "surface diff", "caveat": "Snapshot comparison only.", "research_only": True},
            {"tool_name": "Build Option Book Stress", "workflow_action": "BUILD_OPTION_BOOK_STRESS", "purpose": "Run local scenario stress across supplied option-book positions.", "command": "OPTION BOOK STRESS", "page": "pages/24_Options_Quant_Model_Lab.py", "data_required": "local option positions", "output_type": "option book stress", "caveat": "Stress report only; no portfolio instruction.", "research_only": True},
            {"tool_name": "Run HRP RMT Diagnostic", "workflow_action": "RUN_HRP_RMT_DIAGNOSTIC", "purpose": "Run lightweight HRP/RMT-style diagnostics on supplied returns.", "command": "HRP RMT", "page": "pages/24_Options_Quant_Model_Lab.py", "data_required": "local price series", "output_type": "quant diagnostics", "caveat": "Diagnostic weights are not an allocation plan.", "research_only": True},
            {"tool_name": "Run Kalman GARCH Diagnostic", "workflow_action": "RUN_KALMAN_GARCH_DIAGNOSTIC", "purpose": "Run local state and volatility clustering diagnostics.", "command": "STATE DIAGNOSTICS", "page": "pages/24_Options_Quant_Model_Lab.py", "data_required": "local price series", "output_type": "quant diagnostics", "caveat": "No forecast claim is made.", "research_only": True},
            {"tool_name": "Inspect Options Provider Capability", "workflow_action": "INSPECT_OPTIONS_PROVIDER_CAPABILITY", "purpose": "Review manual/OpenBB capability caveats without adding a dependency.", "command": "INSPECT OPTIONS PROVIDER", "page": "pages/24_Options_Quant_Model_Lab.py", "data_required": "none", "output_type": "provider caveat panel", "caveat": "Missing providers are caveated, not treated as live data.", "research_only": True},
            {"tool_name": "Create Options Research Case", "workflow_action": "CREATE_OPTIONS_RESEARCH_CASE", "purpose": "Create a private local case folder for supplied option-chain, surface, book, and diagnostics artifacts.", "command": "OPTIONS CASE", "page": "pages/24_Options_Quant_Model_Lab.py", "data_required": "case title", "output_type": "options research case", "caveat": "Stored under data/private/options_cases and excluded from release.", "research_only": True},
            {"tool_name": "Save Surface QA to Review Queue", "workflow_action": "CREATE_SURFACE_REVIEW_ITEM", "purpose": "Create a review queue item for supplied surface QA diagnostics.", "command": "SURFACE REVIEW", "page": "pages/24_Options_Quant_Model_Lab.py", "data_required": "surface QA payload", "output_type": "surface review item", "caveat": "Review queue records are research audit artifacts only.", "research_only": True},
            {"tool_name": "Save Option Book Stress to Case", "workflow_action": "SAVE_OPTION_BOOK_STRESS_TO_CASE", "purpose": "Persist supplied option-book stress output into a private options case.", "command": "SAVE OPTION CASE", "page": "pages/24_Options_Quant_Model_Lab.py", "data_required": "case id and stress payload", "output_type": "case artifact", "caveat": "Private local artifact only; no execution workflow.", "research_only": True},
            {"tool_name": "Rebuild Options Case Index", "workflow_action": "REBUILD_OPTIONS_CASE_INDEX", "purpose": "Rebuild the private searchable case index from local options case manifests.", "command": "REBUILD OPTIONS CASE INDEX", "page": "pages/24_Options_Quant_Model_Lab.py", "data_required": "local case manifests", "output_type": "case index", "caveat": "Private index only; local paths redacted from exports.", "research_only": True},
            {"tool_name": "Search Options Cases", "workflow_action": "SEARCH_OPTIONS_CASES", "purpose": "Search private options research cases by title, underlying, source, status, or tags.", "command": "SEARCH OPTIONS CASES", "page": "pages/24_Options_Quant_Model_Lab.py", "data_required": "case index", "output_type": "case search results", "caveat": "Private local search only.", "research_only": True},
            {"tool_name": "List Surface Review Queue", "workflow_action": "LIST_SURFACE_REVIEW_QUEUE", "purpose": "List persistent surface QA review records from the private review queue.", "command": "SURFACE REVIEW QUEUE", "page": "pages/24_Options_Quant_Model_Lab.py", "data_required": "surface review store", "output_type": "review queue", "caveat": "Review status is audit metadata, not approval.", "research_only": True},
            {"tool_name": "Update Surface Review Status", "workflow_action": "UPDATE_PERSISTENT_SURFACE_REVIEW_STATUS", "purpose": "Update persistent surface QA review status and notes.", "command": "UPDATE SURFACE REVIEW", "page": "pages/24_Options_Quant_Model_Lab.py", "data_required": "review id and status", "output_type": "review queue item", "caveat": "Research audit workflow only.", "research_only": True},
        ],
    },
    {
        "section": "Diagnostics Tools",
        "tools": [
            {"tool_name": "Inspect Release Hygiene", "workflow_action": "INSPECT_RELEASE_HYGIENE", "purpose": "Review release package exclusions.", "command": "RELEASE HYGIENE", "page": "docs/GOAL_11C_RELEASE_HYGIENE_REPORT.md", "data_required": "release manifest", "output_type": "diagnostic", "caveat": "External archives and private state remain excluded.", "research_only": True},
        ],
    },
]


def build_research_tool_catalog() -> list[dict[str, Any]]:
    return [{"section": section["section"], "tools": [dict(tool) for tool in section["tools"]], "research_only": True} for section in _TOOL_SECTIONS]


def build_research_tool_center_payload() -> dict[str, Any]:
    sections = build_research_tool_catalog()
    return {
        "title": "Research Tool Center",
        "sections": sections,
        "tool_count": sum(len(section["tools"]) for section in sections),
        "research_only": True,
    }
