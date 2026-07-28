# Goal 12B Options Chain Architecture

Options, option-chain, volatility-surface, option-book, and model outputs are research calculations only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, or execution instructions.

Pipeline: CSV text/path guard -> alias inference -> normalization -> validation -> quality/freshness summary -> IV diagnostics -> reports/attachments.

Trust boundaries: CSV files are user-controlled; path traversal is rejected, file size is bounded, cells are truncated, and report values are HTML/formula escaped. Missing source becomes `user_supplied_unknown_source`.
