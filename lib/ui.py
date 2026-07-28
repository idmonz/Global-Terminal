from __future__ import annotations

from .compliance import render_disclosure


def unique_existing_columns(data, columns: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    if isinstance(data, list):
        candidate_columns = data
        existing = set(columns)
    else:
        candidate_columns = columns
        existing = set(getattr(data, "columns", []))
    for column in candidate_columns:
        if column in existing and column not in seen:
            output.append(column)
            seen.add(column)
    return output


def render_status(st, status) -> None:
    if status is None:
        return
    label = f"{status.provider}: {status.refreshed_status()} | {status.source}"
    if status.ok and not status.warning:
        st.caption(label)
    elif status.ok:
        st.warning(f"{label} - {status.warning}")
    else:
        st.warning(f"{label} - {status.error or 'Unavailable'}")


def render_status_table(st, statuses) -> None:
    rows = [status.to_dict() for status in statuses if status is not None]
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No data status records for this view.")


def render_table(st, data, *, empty_message: str = "Data unavailable for this view.") -> None:
    if data is None or getattr(data, "empty", False):
        st.info(empty_message)
        return
    if hasattr(data, "loc"):
        data = data.loc[:, ~data.columns.duplicated()]
    st.dataframe(data, use_container_width=True, hide_index=True)


def render_chart_or_table(st, fig, data) -> None:
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    else:
        render_table(st, data)


def page_footer(st) -> None:
    render_disclosure(st)
