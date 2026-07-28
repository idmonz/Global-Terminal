# Goal 11F Report Export Security Patch

## Issue

`export_report_html()` could write `html_body_optional` directly when present.

## Fix

- Added `sanitize_optional_report_html()`.
- Added `render_safe_report_export_html()`.
- Optional HTML is escaped inside a local preview wrapper by default.
- Markdown fallback keeps headings and list structure readable while escaping raw HTML.
- Legacy `render_safe_report_html()` remains compatible with existing report renderer expectations.

## Validation

- Script tags do not survive as executable markup.
- Image event handlers do not survive as executable markup.
- `javascript:` links are not exported as active links.
- Markdown headings and lists remain readable.

Tests: `tests/test_goal11f_report_html_export_security.py`.
