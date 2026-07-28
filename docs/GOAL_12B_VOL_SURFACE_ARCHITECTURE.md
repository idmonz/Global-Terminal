# Goal 12B Volatility Surface Architecture

Options, option-chain, volatility-surface, option-book, and model outputs are research calculations only. They are not investment advice, trading recommendations, trade approvals, hedging instructions, or execution instructions.

Surface snapshots are built only from supplied chain rows with solved or supplied IV. Dimensions: expiry, days_to_expiry, strike, moneyness, option_type, bid_iv, ask_iv, mid_iv, source, freshness. Nearest-safe interpolation is explicitly labeled and is not a forecast.
