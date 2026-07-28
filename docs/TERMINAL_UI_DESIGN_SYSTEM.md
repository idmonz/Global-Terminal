# Terminal UI Design System

## Module

`lib/terminal_ui.py`

## Purpose

Provide reusable terminal-style UI primitives for Streamlit pages while keeping payloads testable without Streamlit.

## Helpers

- `terminal_page_header()`
- `terminal_section_header()`
- `metric_strip()`
- `status_badge()`
- `severity_badge()`
- `freshness_badge()`
- `data_gap_badge()`
- `intelligence_card()`
- `compact_event_card()`
- `compact_news_card()`
- `watchpoint_card()`
- `mini_bar()`
- `mini_sparkline()`
- `terminal_css()`

## Visual Rules

- Dark terminal surface.
- Dense but readable cards.
- Compact metric strips.
- Severity, freshness, source, and data-gap badges on intelligence panels.
- Tables are secondary and usually placed behind expanders.

## Payload Safety

Most helpers return dictionaries or HTML strings. Tests can validate card text, badge labels, and schema without launching Streamlit.
