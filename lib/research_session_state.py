from __future__ import annotations

from typing import Any, MutableMapping

_DEFAULT_STATE = {
    "selected_report_id": "",
    "selected_strategy_commit_id": "",
    "selected_commit_id": "",
    "report_filters": {"report_type": "all", "review_status": "all", "query": ""},
    "report_review_notes": "",
    "strategy_review_note": "",
    "selected_preset": "Global",
    "time_window_hours": 24,
    "last_action_result": None,
    "research_only": True,
}


def _streamlit_session_state() -> MutableMapping[str, Any] | None:
    try:
        import streamlit as st  # type: ignore
        return st.session_state
    except Exception:
        return None


def build_research_session_state(**overrides: Any) -> dict[str, Any]:
    state = dict(_DEFAULT_STATE)
    state["report_filters"] = dict(_DEFAULT_STATE["report_filters"])
    state.update({k: v for k, v in overrides.items() if v is not None})
    if state.get("selected_commit_id") and not state.get("selected_strategy_commit_id"):
        state["selected_strategy_commit_id"] = state["selected_commit_id"]
    if state.get("selected_strategy_commit_id") and not state.get("selected_commit_id"):
        state["selected_commit_id"] = state["selected_strategy_commit_id"]
    return state


def get_research_session_state(session_state: MutableMapping[str, Any] | None = None) -> MutableMapping[str, Any]:
    state = session_state if session_state is not None else _streamlit_session_state()
    if state is None:
        return build_research_session_state()
    for key, value in build_research_session_state().items():
        state.setdefault(key, value)
    return state


def set_session_selection(state: MutableMapping[str, Any] | None, key: str, value: Any) -> MutableMapping[str, Any]:
    payload = get_research_session_state(state)
    payload[key] = value
    if key == "selected_strategy_commit_id":
        payload["selected_commit_id"] = value
    if key == "selected_commit_id":
        payload["selected_strategy_commit_id"] = value
    return payload


def get_session_value(state: MutableMapping[str, Any] | None, key: str, default: Any = None) -> Any:
    return get_research_session_state(state).get(key, default)


def persist_report_filter_state(*, report_type: str = "all", review_status: str = "all", query: str = "", session_state: MutableMapping[str, Any] | None = None) -> dict[str, Any]:
    state = get_research_session_state(session_state)
    filters = {"report_type": report_type or "all", "review_status": review_status or "all", "query": query or ""}
    state["report_filters"] = filters
    return filters


def persist_last_action_result(result: dict[str, Any] | None, *, session_state: MutableMapping[str, Any] | None = None) -> dict[str, Any] | None:
    state = get_research_session_state(session_state)
    state["last_action_result"] = result
    return result


def persist_review_note(kind: str, note: str, *, session_state: MutableMapping[str, Any] | None = None) -> str:
    state = get_research_session_state(session_state)
    key = "strategy_review_note" if kind == "strategy" else "report_review_notes"
    state[key] = note or ""
    return state[key]
