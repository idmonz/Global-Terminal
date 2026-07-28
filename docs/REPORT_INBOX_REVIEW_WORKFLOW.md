# Report Inbox Review Workflow

Reports now support filters, sidebar/list payloads, reader panels, source snapshot/caveat panels, action cards, local export actions, and review states: unread, reviewed, archived, requires_review.

Review status columns were added through schema-safe migration defaults.


## Goal 11D selected-reader state

Report Inbox now has selected report state, sidebar/list filtering, selected reader payloads, review-state updates for the selected report, review notes, selected source caveats, linked context panels, and selected export payloads.

## Goal 11E Update

Goal 11E update: selected report state persists through review updates and filter state is retained through session-state helpers.

## Goal 11F export security update

HTML report export is safe-by-default. Optional HTML bodies are escaped inside a local preview wrapper instead of being written directly.

## Goal 12A report integration

Report Inbox now accepts options pricing, scenario, IV, payoff, and quant model snapshot reports with local attachments and source/provider caveats.
