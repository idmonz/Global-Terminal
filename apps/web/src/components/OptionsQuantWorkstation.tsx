"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

import {
  asRecordArray,
  isRecord,
  type ContractEnvelope,
  type RuntimeMode,
} from "@/lib/contracts";

type Row = Record<string, unknown>;
type Surface = "overview" | "chain" | "iv" | "greeks" | "exposure" | "scenario";

export function OptionsQuantWorkstation({
  envelope,
  runtimeMode,
}: {
  envelope: ContractEnvelope;
  runtimeMode: RuntimeMode;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const data = isRecord(envelope.data) ? envelope.data : {};
  const symbol = text(data.symbol, "AAPL");
  const expiries = Array.isArray(data.expiries) ? data.expiries.map(String) : [];
  const selectedExpiry = searchParams.get("expiry") || text(data.selected_expiry, expiries[0] || "");
  const surface = normalizeSurface(searchParams.get("surface"));
  const optionType = searchParams.get("optionType") || "all";
  const moneyness = searchParams.get("moneyness") || "all";
  const selectedContract = searchParams.get("selected") || text(data.selected_contract, "");
  const compare = (searchParams.get("compare") || "").split(",").filter(Boolean).slice(0, 3);
  const chainRows = asRecordArray(data.chain_rows);
  const rejectedRows = asRecordArray(data.rejected_rows);
  const quality = isRecord(data.quality) ? data.quality : {};
  const readiness = isRecord(data.readiness) ? data.readiness : {};
  const assumptions = isRecord(data.assumptions) ? data.assumptions : {};
  const filteredRows = chainRows.filter((row) =>
    text(row.expiry) === selectedExpiry
    && (optionType === "all" || text(row.option_type) === optionType)
    && (moneyness === "all" || text(row.moneyness) === moneyness));
  const selectedRow = filteredRows.find((row) => text(row.contract_symbol) === selectedContract)
    || chainRows.find((row) => text(row.contract_symbol) === selectedContract)
    || filteredRows.find((row) => text(row.option_type) === "call")
    || filteredRows[0];
  const strikes = groupByStrike(filteredRows);

  function update(next: Record<string, string | null>) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("view", "options-quant");
    params.set("symbol", symbol);
    params.set("mode", runtimeMode);
    for (const [key, value] of Object.entries(next)) {
      if (!value) params.delete(key);
      else params.set(key, value);
    }
    router.push("/?" + params.toString(), { scroll: false });
  }

  function toggleCompare(expiry: string) {
    const next = compare.includes(expiry)
      ? compare.filter((item) => item !== expiry)
      : [...compare, expiry].slice(-3);
    update({ compare: next.join(",") || null });
  }

  return (
    <section
      className="options-product"
      data-options-state={chainRows.length ? "ready" : "unavailable"}
      data-options-rows={chainRows.length}
      data-options-surface={surface}
      aria-labelledby="options-product-title"
    >
      <header className="options-product-header">
        <div>
          <div className="options-breadcrumbs">
            <Link href={"/?view=asset&symbol=" + symbol + "&assetClass=equity&timeframe=1D&mode=" + runtimeMode}>Back to {symbol}</Link>
            <Link href={"/?view=market-map&mode=" + runtimeMode}>Market Map</Link>
          </div>
          <span className="eyebrow">Options research / OMON</span>
          <h2 id="options-product-title">{symbol} Options Quant</h2>
          <p>Chain quality, implied volatility, Greeks and assumption-bound exposure in one research workspace.</p>
        </div>
        <dl className="options-underlying-strip">
          <Metric label="Underlying" value={money(data.underlying_price)} />
          <Metric label="Expiry" value={selectedExpiry || "-"} />
          <Metric label="Contracts" value={String(filteredRows.length)} />
          <Metric label="Quality" value={percent(quality.quality_score)} />
          <Metric label="Source" value={text(envelope.summary.source_status, "unavailable")} />
        </dl>
      </header>

      <div className="options-controls" aria-label="Options workspace controls">
        <label>
          <span>Expiry</span>
          <select value={selectedExpiry} onChange={(event) => update({ expiry: event.target.value, selected: null })}>
            {expiries.map((expiry) => <option key={expiry} value={expiry}>{expiry}</option>)}
          </select>
        </label>
        <div className="segmented-control" aria-label="Option type">
          {["all", "call", "put"].map((value) => (
            <button key={value} type="button" className={optionType === value ? "active" : ""} onClick={() => update({ optionType: value })}>
              {value}
            </button>
          ))}
        </div>
        <label>
          <span>Moneyness</span>
          <select value={moneyness} onChange={(event) => update({ moneyness: event.target.value })}>
            {["all", "itm", "atm", "otm"].map((value) => <option key={value}>{value}</option>)}
          </select>
        </label>
        <div className="options-compare-control">
          <span>Compare expiries</span>
          <div>
            {expiries.slice(0, 6).map((expiry) => (
              <label key={expiry}>
                <input type="checkbox" checked={compare.includes(expiry)} onChange={() => toggleCompare(expiry)} />
                {expiry.slice(5)}
              </label>
            ))}
          </div>
        </div>
      </div>

      <nav className="options-surface-tabs" aria-label="Options analysis surfaces">
        {(["overview", "chain", "iv", "greeks", "exposure", "scenario"] as Surface[]).map((value) => (
          <button
            type="button"
            key={value}
            className={surface === value ? "active" : ""}
            aria-pressed={surface === value}
            onClick={() => update({ surface: value })}
          >
            {value === "iv" ? "IV structure" : value}
          </button>
        ))}
      </nav>

      {!chainRows.length ? (
        <div className="options-unavailable" role="status">
          <strong>Option chain unavailable</strong>
          <span>{envelope.unavailable.map((row) => text(row.data_gap)).filter(Boolean).join(" ") || "No valid provider rows were returned."}</span>
          <Link href={"/?view=options-quant&symbol=" + symbol + "&mode=fixture&surface=chain"}>Open deterministic research fixture</Link>
        </div>
      ) : (
        <div className="options-analysis-layout">
          <div className="options-primary-surface">
            {surface === "overview" ? (
              <OptionsOverviewSurface data={data} expiry={selectedExpiry} selectedRow={selectedRow} filteredRows={filteredRows} />
            ) : surface === "chain" ? (
              <ChainTable strikes={strikes} selectedContract={selectedContract} onSelect={(contract) => update({ selected: contract })} />
            ) : surface === "iv" ? (
              <IvSurface data={data} expiry={selectedExpiry} compare={compare} />
            ) : surface === "greeks" ? (
              <GreeksSurface rows={asRecordArray(data.greeks_rows).filter((row) => text(row.expiry) === selectedExpiry)} />
            ) : surface === "exposure" ? (
              <ExposureSurface rows={asRecordArray(data.gamma_exposure_by_strike)} ready={Boolean(readiness.gex_ready)} />
            ) : (
              <ScenarioSurface rows={asRecordArray(data.scenario_rows)} />
            )}
          </div>
          <aside className="options-inspector" aria-label="Selected option and source context">
            <SelectedContract row={selectedRow} />
            <QualityPanel quality={quality} rejectedRows={rejectedRows} />
            <AssumptionPanel assumptions={assumptions} />
          </aside>
        </div>
      )}

      <footer className="options-disclosure">
        <strong>Research boundary</strong>
        <span>{text(data.caveat, "Research calculations only. No investment advice or execution.")}</span>
      </footer>
    </section>
  );
}

function ChainTable({
  strikes,
  selectedContract,
  onSelect,
}: {
  strikes: { strike: number; call?: Row; put?: Row }[];
  selectedContract: string;
  onSelect: (contract: string) => void;
}) {
  return (
    <section className="options-chain-surface options-section" aria-labelledby="options-chain-title">
      <div className="options-section-heading">
        <div><span className="eyebrow">Calls / strike / puts</span><h3 id="options-chain-title">Option Chain</h3></div>
        <span>{strikes.length} strikes</span>
      </div>
      <div className="options-chain-scroll">
        <table className="options-chain-table">
          <thead>
            <tr><th colSpan={5}>Calls</th><th>Strike</th><th colSpan={5}>Puts</th></tr>
            <tr>
              <th>OI</th><th>Vol</th><th>IV</th><th>Bid</th><th>Ask</th>
              <th className="strike-column">Price</th>
              <th>Bid</th><th>Ask</th><th>IV</th><th>Vol</th><th>OI</th>
            </tr>
          </thead>
          <tbody>
            {strikes.map(({ strike, call, put }) => (
              <tr key={strike} className={(text(call?.contract_symbol) === selectedContract || text(put?.contract_symbol) === selectedContract) ? "selected" : ""}>
                <Cell value={call?.open_interest} />
                <Cell value={call?.volume} />
                <Cell value={iv(call?.provider_iv)} />
                <SelectCell row={call} field="bid" onSelect={onSelect} />
                <SelectCell row={call} field="ask" onSelect={onSelect} />
                <th scope="row" className="strike-column">{number(strike, 2)}</th>
                <SelectCell row={put} field="bid" onSelect={onSelect} />
                <SelectCell row={put} field="ask" onSelect={onSelect} />
                <Cell value={iv(put?.provider_iv)} />
                <Cell value={put?.volume} />
                <Cell value={put?.open_interest} />
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function OptionsOverviewSurface({
  data,
  expiry,
  selectedRow,
  filteredRows,
}: {
  data: Row;
  expiry: string;
  selectedRow?: Row;
  filteredRows: Row[];
}) {
  const smile = asRecordArray(data.iv_smile).filter((row) => text(row.expiry) === expiry);
  const calls = smile.filter((row) => text(row.option_type) === "call");
  const puts = smile.filter((row) => text(row.option_type) === "put");
  const greeks = asRecordArray(data.greeks_rows).filter((row) => text(row.expiry) === expiry);
  const exposure = asRecordArray(data.gamma_exposure_by_strike);
  const scenarios = asRecordArray(data.scenario_rows);
  const quality = isRecord(data.quality) ? data.quality : {};
  const selected = selectedRow || filteredRows[0];
  const selectedStrike = numeric(selected?.strike);
  const nearbyGreeks = selectedStrike === null
    ? greeks.slice(0, 8)
    : [...greeks]
        .sort((left, right) => Math.abs((numeric(left.strike) || 0) - selectedStrike) - Math.abs((numeric(right.strike) || 0) - selectedStrike))
        .slice(0, 8)
        .sort((left, right) => (numeric(left.strike) || 0) - (numeric(right.strike) || 0));

  return (
    <section className="options-overview-surface options-section" data-options-analytics-panels="4" aria-labelledby="options-overview-title">
      <div className="options-section-heading">
        <div><span className="eyebrow">OMON dashboard / source-aware</span><h3 id="options-overview-title">Options Analytics Overview</h3></div>
        <span>{filteredRows.length} selected rows / quality {percent(quality.quality_score)}</span>
      </div>
      <div className="options-analytics-grid">
        <article className="options-card iv-surface" aria-labelledby="options-overview-iv">
          <div className="options-card-head"><div><span className="eyebrow">IV smile</span><h4 id="options-overview-iv">Volatility By Strike</h4></div><span>{smile.length} points</span></div>
          {smile.length >= 3 ? (
            <SvgLineChart className="options-iv-chart options-mini-chart" calls={calls} puts={puts} xField="strike" yField="implied_volatility" />
          ) : <Unavailable label="IV smile" detail="At least three valid IV points are required." />}
        </article>

        <article className="options-card greeks-surface" aria-labelledby="options-overview-greeks">
          <div className="options-card-head"><div><span className="eyebrow">Greeks strip</span><h4 id="options-overview-greeks">Delta / Gamma / Vega</h4></div><span>{nearbyGreeks.length} contracts</span></div>
          <MiniGreekBars rows={nearbyGreeks} />
        </article>

        <article className="options-card exposure-surface" aria-labelledby="options-overview-exposure">
          <div className="options-card-head"><div><span className="eyebrow">Assumption-bound</span><h4 id="options-overview-exposure">Gamma Exposure Proxy</h4></div><span>{exposure.length} strikes</span></div>
          <MiniExposureBars rows={exposure} />
        </article>

        <article className="options-card payoff-surface" aria-labelledby="options-overview-scenario">
          <div className="options-card-head"><div><span className="eyebrow">Scenario grid</span><h4 id="options-overview-scenario">Payoff / P&L Preview</h4></div><span>{scenarios.length} states</span></div>
          <MiniScenarioChart rows={scenarios} />
        </article>
      </div>
    </section>
  );
}

function IvSurface({ data, expiry, compare }: { data: Row; expiry: string; compare: string[] }) {
  const smile = asRecordArray(data.iv_smile).filter((row) => text(row.expiry) === expiry);
  const surface = asRecordArray(data.surface_points);
  const wanted = new Set([expiry, ...compare]);
  const points = surface.filter((row) => wanted.has(text(row.expiry)));
  const chartRows = points.length ? points : smile;
  const calls = chartRows.filter((row) => text(row.option_type) === "call");
  const puts = chartRows.filter((row) => text(row.option_type) === "put");
  return (
    <section className="options-chart-surface options-section iv-surface" aria-labelledby="options-iv-title">
      <div className="options-section-heading">
        <div><span className="eyebrow">Provider IV / decimal</span><h3 id="options-iv-title">Volatility Structure</h3></div>
        <span>{chartRows.length} points</span>
      </div>
      {chartRows.length >= 3 ? (
        <SvgLineChart className="options-iv-chart" calls={calls} puts={puts} xField="strike" yField={points.length ? "implied_volatility" : "implied_volatility"} />
      ) : <Unavailable label="IV structure" detail="At least three valid provider-IV points are required." />}
      <div className="options-term-strip">
        {asRecordArray(data.iv_term_structure).map((row) => (
          <div key={text(row.expiry)}><span>{text(row.expiry)}</span><strong>{iv(row.atm_implied_volatility)}</strong><small>{text(row.sample_count)} ATM samples</small></div>
        ))}
      </div>
    </section>
  );
}

function GreeksSurface({ rows }: { rows: Row[] }) {
  return (
    <section className="options-table-surface options-section greeks-surface" aria-labelledby="options-greeks-title">
      <div className="options-section-heading">
        <div><span className="eyebrow">Black-Scholes approximation</span><h3 id="options-greeks-title">Greeks By Strike</h3></div>
        <span>{rows.length} contracts</span>
      </div>
      {rows.length ? (
        <div className="options-chain-scroll">
          <table className="options-greeks-table">
            <thead><tr><th>Contract</th><th>Side</th><th>Strike</th><th>Delta</th><th>Gamma</th><th>Vega</th><th>Theta/day</th><th>Contract Δ</th><th>Vega/1%</th></tr></thead>
            <tbody>{rows.map((row) => <tr key={text(row.contract_symbol)}><td>{text(row.contract_symbol)}</td><td>{text(row.option_type)}</td><td>{number(row.strike, 2)}</td><td>{number(row.delta, 4)}</td><td>{number(row.gamma, 6)}</td><td>{number(row.vega, 3)}</td><td>{number(row.theta_per_day, 4)}</td><td>{number(row.contract_delta, 2)}</td><td>{number(row.contract_vega_1pct, 2)}</td></tr>)}</tbody>
          </table>
        </div>
      ) : <Unavailable label="Greeks" detail="Valid IV and model inputs are required." />}
    </section>
  );
}

function ExposureSurface({ rows, ready }: { rows: Row[]; ready: boolean }) {
  const max = Math.max(...rows.map((row) => Math.abs(numeric(row.net_gamma_exposure) || 0)), 1);
  return (
    <section className="options-exposure-surface options-section exposure-surface" aria-labelledby="options-exposure-title">
      <div className="options-section-heading">
        <div><span className="eyebrow">Assumption-dependent / not dealer-observed</span><h3 id="options-exposure-title">Gamma Exposure By Strike</h3></div>
        <span>{rows.length} strikes</span>
      </div>
      {ready && rows.length ? (
        <div className="options-exposure-chart">
          {rows.map((row) => {
            const value = numeric(row.net_gamma_exposure) || 0;
            return <div key={text(row.strike)}><span>{number(row.strike, 0)}</span><i className={value >= 0 ? "positive" : "negative"} style={{ width: String(Math.max(2, Math.abs(value) / max * 100)) + "%" }} /><strong>{compact(value)}</strong></div>;
          })}
        </div>
      ) : <Unavailable label="Gamma exposure" detail="Gamma, open interest, multiplier and spot are all required." />}
      <p className="options-method-note">Calls positive and puts negative is an explicit convention, not observed dealer positioning.</p>
    </section>
  );
}

function ScenarioSurface({ rows }: { rows: Row[] }) {
  return (
    <section className="options-table-surface options-section payoff-surface" aria-labelledby="options-scenario-title">
      <div className="options-section-heading">
        <div><span className="eyebrow">Bounded spot / volatility research grid</span><h3 id="options-scenario-title">Scenario Matrix</h3></div>
        <span>{rows.length} states</span>
      </div>
      {rows.length ? (
        <div className="options-chain-scroll">
          <table className="options-scenario-matrix">
            <thead><tr><th>Spot move</th><th>Vol move</th><th>Model price</th><th>P/L from observed premium</th><th>Delta</th><th>Gamma</th><th>Theta/day</th></tr></thead>
            <tbody>{rows.map((row, index) => <tr key={String(index)}><td>{signed(row.spot_change_pct, "%")}</td><td>{signed(row.volatility_change_points, " pt")}</td><td>{money(row.price)}</td><td>{money(row.pnl_from_supplied_premium)}</td><td>{number(row.delta, 4)}</td><td>{number(row.gamma, 6)}</td><td>{number(row.theta_per_day, 4)}</td></tr>)}</tbody>
          </table>
        </div>
      ) : <Unavailable label="Scenario matrix" detail="Select a contract with valid premium, IV and model inputs." />}
    </section>
  );
}

function MiniGreekBars({ rows }: { rows: Row[] }) {
  if (!rows.length) return <Unavailable label="Greeks strip" detail="Valid IV and model inputs are required." />;
  const maxDelta = Math.max(...rows.map((row) => Math.abs(numeric(row.delta) || 0)), 1);
  const maxGamma = Math.max(...rows.map((row) => Math.abs(numeric(row.gamma) || 0)), 0.0001);
  const maxVega = Math.max(...rows.map((row) => Math.abs(numeric(row.vega) || 0)), 1);
  return (
    <div className="options-mini-bars options-greeks-bars">
      {rows.map((row) => (
        <div key={text(row.contract_symbol)}>
          <span>{number(row.strike, 0)} {text(row.option_type).slice(0, 1).toUpperCase()}</span>
          <i className="delta" style={{ width: `${Math.max(3, Math.abs(numeric(row.delta) || 0) / maxDelta * 100)}%` }} />
          <i className="gamma" style={{ width: `${Math.max(3, Math.abs(numeric(row.gamma) || 0) / maxGamma * 100)}%` }} />
          <i className="vega" style={{ width: `${Math.max(3, Math.abs(numeric(row.vega) || 0) / maxVega * 100)}%` }} />
          <strong>{number(row.delta, 2)} / {number(row.vega, 0)}</strong>
        </div>
      ))}
    </div>
  );
}

function MiniExposureBars({ rows }: { rows: Row[] }) {
  if (!rows.length) return <Unavailable label="Exposure proxy" detail="Gamma, open interest, multiplier and spot are required." />;
  const max = Math.max(...rows.map((row) => Math.abs(numeric(row.net_gamma_exposure) || 0)), 1);
  return (
    <div className="options-mini-bars options-exposure-mini">
      {rows.slice(0, 10).map((row) => {
        const value = numeric(row.net_gamma_exposure) || 0;
        return (
          <div key={text(row.strike)}>
            <span>{number(row.strike, 0)}</span>
            <i className={value >= 0 ? "positive" : "negative"} style={{ width: `${Math.max(3, Math.abs(value) / max * 100)}%` }} />
            <strong>{compact(value)}</strong>
          </div>
        );
      })}
    </div>
  );
}

function MiniScenarioChart({ rows }: { rows: Row[] }) {
  if (!rows.length) return <Unavailable label="Payoff preview" detail="Select a contract with valid premium and model inputs." />;
  const max = Math.max(...rows.map((row) => Math.abs(numeric(row.pnl_from_supplied_premium) || 0)), 1);
  return (
    <div className="options-scenario-bars">
      {rows.slice(0, 15).map((row, index) => {
        const pnl = numeric(row.pnl_from_supplied_premium) || 0;
        return (
          <div key={`${text(row.spot_change_pct)}-${text(row.volatility_change_points)}-${index}`}>
            <span>{signed(row.spot_change_pct, "%")}</span>
            <i className={pnl >= 0 ? "positive" : "negative"} style={{ height: `${Math.max(8, Math.abs(pnl) / max * 100)}%` }} />
            <strong>{money(pnl)}</strong>
          </div>
        );
      })}
    </div>
  );
}

function SelectedContract({ row }: { row?: Row }) {
  if (!row) return <Unavailable label="Selected contract" detail="Select a valid chain row." />;
  return (
    <section>
      <span className="eyebrow">Selected contract</span>
      <h3>{text(row.contract_symbol)}</h3>
      <dl className="options-detail-list">
        <Detail label="Side / strike" value={text(row.option_type) + " / " + number(row.strike, 2)} />
        <Detail label="Bid / ask" value={money(row.bid) + " / " + money(row.ask)} />
        <Detail label="Provider IV" value={iv(row.provider_iv)} />
        <Detail label="OI / volume" value={text(row.open_interest, "-") + " / " + text(row.volume, "-")} />
        <Detail label="Last trade" value={text(row.last_trade_at, "unavailable")} />
        <Detail label="Source state" value={text(row.source_status)} />
      </dl>
      <p>{text(row.quality_flags, "No row caveats")}</p>
    </section>
  );
}

function QualityPanel({ quality, rejectedRows }: { quality: Row; rejectedRows: Row[] }) {
  const flags = isRecord(quality.flag_counts) ? quality.flag_counts : {};
  return (
    <section>
      <span className="eyebrow">Chain quality</span>
      <h3>{percent(quality.quality_score)}</h3>
      <dl className="options-detail-list">
        <Detail label="Accepted / rejected" value={text(quality.accepted_rows) + " / " + text(quality.rejected_rows)} />
        <Detail label="Wide spreads" value={text(quality.wide_spread_rows, "0")} />
        <Detail label="Missing OI" value={text(quality.missing_open_interest_rows, "0")} />
        <Detail label="Missing IV" value={text(quality.missing_iv_rows, "0")} />
      </dl>
      {Object.keys(flags).length ? <p>{Object.entries(flags).map(([key, value]) => key + ": " + String(value)).join(" / ")}</p> : null}
      {rejectedRows.length ? <p>{rejectedRows.length} rejected rows remain inspectable in the API contract.</p> : null}
    </section>
  );
}

function AssumptionPanel({ assumptions }: { assumptions: Row }) {
  const rate = isRecord(assumptions.risk_free_rate) ? assumptions.risk_free_rate : {};
  const multiplier = isRecord(assumptions.contract_multiplier) ? assumptions.contract_multiplier : {};
  const dealer = isRecord(assumptions.dealer_sign_convention) ? assumptions.dealer_sign_convention : {};
  return (
    <section>
      <span className="eyebrow">Model assumptions</span>
      <h3>{text(assumptions.pricing_model, "Unavailable")}</h3>
      <dl className="options-detail-list">
        <Detail label="Risk free rate" value={percentFromDecimal(rate.value)} />
        <Detail label="Multiplier" value={text(multiplier.value, "-")} />
        <Detail label="Dealer sign" value={text(dealer.value, "not used")} />
        <Detail label="Observed positioning" value={text(dealer.observed_dealer_positioning, "false")} />
      </dl>
      <p>{text(assumptions.timestamp_alignment)}</p>
    </section>
  );
}

function SvgLineChart({ className, calls, puts, xField, yField }: { className: string; calls: Row[]; puts: Row[]; xField: string; yField: string }) {
  const all = [...calls, ...puts];
  const xs = all.map((row) => numeric(row[xField])).filter((value): value is number => value !== null);
  const ys = all.map((row) => numeric(row[yField])).filter((value): value is number => value !== null);
  const minX = Math.min(...xs); const maxX = Math.max(...xs); const minY = Math.min(...ys); const maxY = Math.max(...ys);
  const point = (row: Row) => {
    const x = numeric(row[xField]) || 0; const y = numeric(row[yField]) || 0;
    return [40 + (x - minX) / Math.max(maxX - minX, 1) * 820, 300 - (y - minY) / Math.max(maxY - minY, 0.01) * 250];
  };
  const path = (rows: Row[]) => rows.sort((a, b) => (numeric(a[xField]) || 0) - (numeric(b[xField]) || 0)).map((row) => point(row).join(",")).join(" ");
  return (
    <svg className={className} viewBox="0 0 900 340" role="img" aria-label="Implied volatility by strike">
      <line x1="40" y1="300" x2="860" y2="300" /><line x1="40" y1="50" x2="40" y2="300" />
      <polyline className="call-line" points={path(calls)} /><polyline className="put-line" points={path(puts)} />
      {all.map((row) => { const [x, y] = point(row); return <circle key={text(row.contract_symbol, text(row.strike) + text(row.option_type))} className={text(row.option_type)} cx={x} cy={y} r="4" />; })}
      <text x="45" y="28">IV {iv(maxY)}</text><text x="740" y="330">Strike {number(maxX, 0)}</text><text x="45" y="330">{number(minX, 0)}</text>
    </svg>
  );
}

function groupByStrike(rows: Row[]) {
  const grouped = new Map<number, { strike: number; call?: Row; put?: Row }>();
  for (const row of rows) {
    const strike = numeric(row.strike);
    if (strike === null) continue;
    const item = grouped.get(strike) || { strike };
    if (text(row.option_type) === "call") item.call = row;
    if (text(row.option_type) === "put") item.put = row;
    grouped.set(strike, item);
  }
  return [...grouped.values()].sort((a, b) => a.strike - b.strike);
}

function SelectCell({ row, field, onSelect }: { row?: Row; field: string; onSelect: (contract: string) => void }) {
  if (!row) return <td>-</td>;
  return <td><button type="button" onClick={() => onSelect(text(row.contract_symbol))}>{money(row[field])}</button></td>;
}
function Cell({ value }: { value: unknown }) { return <td>{text(value, "-")}</td>; }
function Metric({ label, value }: { label: string; value: string }) { return <div><dt>{label}</dt><dd>{value}</dd></div>; }
function Detail({ label, value }: { label: string; value: string }) { return <div><dt>{label}</dt><dd>{value}</dd></div>; }
function Unavailable({ label, detail }: { label: string; detail: string }) { return <div className="options-unavailable" role="status"><strong>{label} unavailable</strong><span>{detail}</span></div>; }
function normalizeSurface(value: string | null): Surface { return ["overview", "chain", "iv", "greeks", "exposure", "scenario"].includes(value || "") ? value as Surface : "overview"; }
function numeric(value: unknown): number | null { const result = Number(value); return value === null || value === undefined || value === "" || !Number.isFinite(result) ? null : result; }
function text(value: unknown, fallback = ""): string { if (Array.isArray(value)) return value.length ? value.join(", ") : fallback; if (value === null || value === undefined || value === "") return fallback; return String(value); }
function number(value: unknown, digits = 2): string { const result = numeric(value); return result === null ? "-" : result.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits }); }
function money(value: unknown): string { const result = numeric(value); return result === null ? "-" : "$" + number(result, 2); }
function iv(value: unknown): string { const result = numeric(value); return result === null ? "-" : number(result * 100, 1) + "%"; }
function percent(value: unknown): string { const result = numeric(value); return result === null ? "-" : number(result, 1) + "/100"; }
function percentFromDecimal(value: unknown): string { const result = numeric(value); return result === null ? "-" : number(result * 100, 2) + "%"; }
function signed(value: unknown, suffix = ""): string { const result = numeric(value); return result === null ? "-" : (result > 0 ? "+" : "") + number(result, 1) + suffix; }
function compact(value: number): string { return Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 2 }).format(value); }
