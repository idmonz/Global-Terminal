"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import type { ContractEnvelope, RuntimeMode } from "@/lib/contracts";
import { asRecordArray, isRecord } from "@/lib/contracts";
import { canonicalAssetHref } from "@/lib/product-routes";

type Row = Record<string, unknown>;
type DisplayMode = "heatmap" | "table" | "scatter" | "factors";
type SavedScreen = {
  screen_id: string;
  name: string;
  definition: Record<string, unknown>;
  updated_at?: string;
  privacy_scope?: string;
};

export function MarketMapScreener({
  envelope,
  runtimeMode,
  apiBaseUrl,
}: {
  envelope: ContractEnvelope;
  runtimeMode: RuntimeMode;
  apiBaseUrl: string | null;
}) {
  const searchParams = useSearchParams();
  const [clientParams, setClientParams] = useState(() => new URLSearchParams(searchParams.toString()));
  const data = isRecord(envelope.data) ? envelope.data : {};
  const instruments = asRecordArray(data.instruments);
  const filterOptions = isRecord(data.filter_options) ? data.filter_options : {};
  const discoveryOptions = isRecord(filterOptions.discovery) ? filterOptions.discovery : {};
  const readiness = isRecord(data.readiness) ? data.readiness : {};
  const universe = isRecord(data.universe_contract) ? data.universe_contract : {};
  const materialization = isRecord(data.materialization) ? data.materialization : {};
  const refreshHealth = isRecord(materialization.refresh_health) ? materialization.refresh_health : {};
  const refreshHistory = asRecordArray(materialization.refresh_history);
  const rankModels = isRecord(data.rank_models) ? data.rank_models : {};
  const factorCatalog = asRecordArray(data.factor_catalog);
  const sectors = stringList(discoveryOptions.sectors ?? filterOptions.sectors);
  const industries = stringList(filterOptions.industries);
  const countries = stringList(filterOptions.countries);
  const exchanges = stringList(filterOptions.exchanges);
  const statuses = stringList(filterOptions.source_statuses);
  const eligibilityOptions = optionsOr(filterOptions.eligibility, ["all", "eligible", "ineligible"]);
  const groupingOptions = optionsOr(filterOptions.grouping, ["sector", "industry", "none"]);
  const sizeMetricOptions = optionsOr(filterOptions.size_metrics, ["market_cap", "volume", "equal"]);
  const colorMetricOptions = optionsOr(filterOptions.color_metrics, ["return_1d_pct", "return_1m_pct", "relative_volume"]);

  const sector = clientParams.get("sector") || "all";
  const industry = clientParams.get("industry") || "all";
  const country = clientParams.get("country") || "all";
  const exchange = clientParams.get("exchange") || "all";
  const eligibility = allowed(clientParams.get("eligibility"), eligibilityOptions, "all");
  const sourceStatus = clientParams.get("freshness") || "all";
  const rankModel = allowed(clientParams.get("rank"), stringList(discoveryOptions.rank), "balanced");
  const display = allowed(clientParams.get("display"), stringList(discoveryOptions.display), "heatmap") as DisplayMode;
  const grouping = allowed(clientParams.get("group"), groupingOptions, "sector");
  const sizeMetric = allowed(clientParams.get("size"), sizeMetricOptions, "market_cap");
  const colorMetric = allowed(clientParams.get("color"), colorMetricOptions, "return_1d_pct");
  const selectedSymbol = clientParams.get("selected") || text(instruments[0]?.symbol, "");
  const compareParam = clientParams.get("compare") || "";
  const compareSymbols = useMemo(
    () => compareParam.split(",").map((item) => item.trim()).filter(Boolean).slice(0, 4),
    [compareParam],
  );
  const queryFromUrl = clientParams.get("query") || "";
  const [queryDraft, setQueryDraft] = useState(queryFromUrl);
  const [savedScreens, setSavedScreens] = useState<SavedScreen[]>([]);
  const [savedScreenId, setSavedScreenId] = useState("");
  const [screenName, setScreenName] = useState("");
  const [savedMessage, setSavedMessage] = useState("");
  const [savedBusy, setSavedBusy] = useState(false);

  const replaceClientParams = useCallback((params: URLSearchParams) => {
    const queryString = params.toString();
    window.history.replaceState(window.history.state, "", `/?${queryString}`);
    setClientParams(new URLSearchParams(queryString));
  }, []);

  const filterState = useMemo(() => ({
    marketCap: clientParams.get("marketCap") || "all",
    return1d: clientParams.get("return1d") || "all",
    return1m: clientParams.get("return1m") || "all",
    volatility: clientParams.get("volatility") || "all",
    rsi: clientParams.get("rsi") || "all",
    trend: clientParams.get("trend") || "all",
    valuation: clientParams.get("valuation") || "all",
    quality: clientParams.get("quality") || "all",
  }), [clientParams]);

  useEffect(() => {
    const onPopState = () => setClientParams(new URLSearchParams(window.location.search));
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    if (!apiBaseUrl) return;
    let active = true;
    fetch(`${apiBaseUrl}/api/market-map-screens`, { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json() as Promise<{ screens?: SavedScreen[] }>;
      })
      .then((payload) => {
        if (active) setSavedScreens(Array.isArray(payload.screens) ? payload.screens : []);
      })
      .catch(() => {
        if (active) setSavedMessage("Local saved screens are unavailable. Discovery remains usable.");
      });
    return () => { active = false; };
  }, [apiBaseUrl]);

  const query = queryFromUrl.trim().toLowerCase();
  const filtered = instruments
    .filter((row) => {
      const matchesSector = sector === "all" || text(row.sector) === sector;
      const matchesIndustry = industry === "all" || text(row.industry) === industry;
      const matchesCountry = country === "all" || text(row.country || row.region) === country;
      const matchesExchange = exchange === "all" || text(row.exchange) === exchange;
      const matchesStatus = sourceStatus === "all" || text(row.source_status) === sourceStatus;
      const haystack = `${text(row.symbol)} ${text(row.name)} ${text(row.sector)} ${text(row.industry)} ${text(row.exchange)} ${text(row.country || row.region)}`.toLowerCase();
      const model = rankFor(row, rankModel);
      return matchesSector
        && matchesIndustry
        && matchesCountry
        && matchesExchange
        && matchesStatus
        && (!query || haystack.includes(query))
        && bucketMatch(row.market_cap, filterState.marketCap, "marketCap")
        && bucketMatch(row.return_1d_pct, filterState.return1d, "return")
        && bucketMatch(row.return_1m_pct, filterState.return1m, "return")
        && bucketMatch(row.realized_volatility_pct, filterState.volatility, "volatility")
        && bucketMatch(row.rsi, filterState.rsi, "rsi")
        && (filterState.trend === "all" || text(record(row.factors).trend_state) === filterState.trend)
        && (filterState.valuation === "all"
          || (filterState.valuation === "available" && record(row.factors).valuation_available === true)
          || (filterState.valuation === "missing" && record(row.factors).valuation_available !== true))
        && (filterState.quality === "all" || text(record(row.data_quality).status) === filterState.quality)
        && (eligibility === "all"
          || (eligibility === "eligible" && model.eligible === true)
          || (eligibility === "ineligible" && model.eligible !== true));
    })
    .sort((left, right) => {
      const scoreOrder = compareValues(rankFor(left, rankModel).score, rankFor(right, rankModel).score, "desc");
      return scoreOrder || compareValues(left.market_cap, right.market_cap, "desc");
    });

  const grouped = groupByHierarchy(filtered, sector, grouping, sizeMetric);
  const selected = filtered.find((row) => text(row.symbol) === selectedSymbol)
    ?? instruments.find((row) => text(row.symbol) === selectedSymbol)
    ?? filtered[0]
    ?? instruments[0];
  const compared = instruments.filter((row) => compareSymbols.includes(text(row.symbol)));
  const scatterRows = filtered.filter((row) => number(row.return_1m_pct) !== null && number(row.realized_volatility_pct) !== null).slice(0, 60);
  const selectedRank = selected ? rankFor(selected, rankModel) : {};
  const modelMetadata = record(rankModels[rankModel]);
  const activeFilterCount = Object.values(filterState).filter((value) => value !== "all").length
    + (sector !== "all" ? 1 : 0)
    + (industry !== "all" ? 1 : 0)
    + (country !== "all" ? 1 : 0)
    + (exchange !== "all" ? 1 : 0)
    + (eligibility !== "all" ? 1 : 0)
    + (sourceStatus !== "all" ? 1 : 0)
    + (query ? 1 : 0);

  function updateParams(updates: Record<string, string>) {
    const params = new URLSearchParams(clientParams.toString());
    Object.entries(updates).forEach(([key, value]) => params.set(key, value));
    replaceClientParams(params);
  }

  function submitQuery(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    updateParams({ query: queryDraft.trim() });
  }

  function selectInstrument(symbol: string) {
    const params = new URLSearchParams(clientParams.toString());
    params.set("selected", symbol);
    replaceClientParams(params);
  }

  function toggleCompare(symbol: string) {
    const next = compareSymbols.includes(symbol)
      ? compareSymbols.filter((item) => item !== symbol)
      : [...compareSymbols, symbol].slice(-4);
    const params = new URLSearchParams(clientParams.toString());
    params.set("compare", next.join(","));
    replaceClientParams(params);
  }

  function setSector(value: string) {
    const params = new URLSearchParams(clientParams.toString());
    params.set("sector", value);
    params.set("industry", "all");
    replaceClientParams(params);
  }

  function resetFilters() {
    updateParams({
      query: "", sector: "all", freshness: "all", marketCap: "all", return1d: "all",
      return1m: "all", volatility: "all", rsi: "all", trend: "all", valuation: "all",
      quality: "all", industry: "all", country: "all", exchange: "all", eligibility: "all",
      rank: "balanced", display: "heatmap", group: "sector", size: "market_cap",
      color: "return_1d_pct", compare: "",
    });
    setQueryDraft("");
  }

  function currentDefinition() {
    return {
      universe: "bounded-us-largecap",
      sectors: sector === "all" ? [] : [sector],
      industries: industry === "all" ? [] : [industry],
      country,
      exchange,
      eligibility,
      market_cap: filterState.marketCap,
      return_1d: filterState.return1d,
      return_1m: filterState.return1m,
      volatility: filterState.volatility,
      rsi: filterState.rsi,
      trend: filterState.trend,
      valuation: filterState.valuation,
      quality: filterState.quality,
      rank: rankModel,
      display,
      grouping,
      size_metric: sizeMetric,
      color_metric: colorMetric,
    };
  }

  async function saveScreen(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!apiBaseUrl) {
      setSavedMessage("Start the optional local API to save private screen definitions.");
      return;
    }
    setSavedBusy(true);
    try {
      const response = await fetch(`${apiBaseUrl}/api/market-map-screens`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: screenName, definition: currentDefinition() }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json() as { screen?: SavedScreen };
      if (payload.screen) {
        setSavedScreens((current) => [payload.screen as SavedScreen, ...current]);
        setSavedScreenId(payload.screen.screen_id);
        setScreenName(payload.screen.name);
      }
      setSavedMessage("Saved locally. The screen name and definition were sent in the POST body, not the URL.");
    } catch {
      setSavedMessage("The local screen could not be saved. Existing screens were not changed.");
    } finally {
      setSavedBusy(false);
    }
  }

  function chooseSavedScreen(screenId: string) {
    setSavedScreenId(screenId);
    const screen = savedScreens.find((item) => item.screen_id === screenId);
    setScreenName(screen?.name ?? "");
  }

  function applySavedScreen() {
    const screen = savedScreens.find((item) => item.screen_id === savedScreenId);
    if (!screen) return;
    const definition = screen.definition ?? {};
    const screenSectors = Array.isArray(definition.sectors) ? definition.sectors : [];
    updateParams({
      sector: text(screenSectors[0], "all"),
      industry: text((Array.isArray(definition.industries) ? definition.industries : [])[0], "all"),
      country: text(definition.country, "all"),
      exchange: text(definition.exchange, "all"),
      eligibility: text(definition.eligibility, "all"),
      marketCap: text(definition.market_cap, "all"),
      return1d: text(definition.return_1d, "all"),
      return1m: text(definition.return_1m, "all"),
      volatility: text(definition.volatility, "all"),
      rsi: text(definition.rsi, "all"),
      trend: text(definition.trend, "all"),
      valuation: text(definition.valuation, "all"),
      quality: text(definition.quality, "all"),
      rank: text(definition.rank, "balanced"),
      display: text(definition.display, "heatmap"),
      group: text(definition.grouping, "sector"),
      size: text(definition.size_metric, "market_cap"),
      color: text(definition.color_metric, "return_1d_pct"),
    });
    setSavedMessage(`Applied ${screen.name}.`);
  }

  async function renameSavedScreen() {
    if (!apiBaseUrl || !savedScreenId) return;
    setSavedBusy(true);
    try {
      const response = await fetch(`${apiBaseUrl}/api/market-map-screens/${encodeURIComponent(savedScreenId)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: screenName }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json() as { screen?: SavedScreen };
      if (payload.screen) setSavedScreens((current) => current.map((item) => item.screen_id === savedScreenId ? payload.screen as SavedScreen : item));
      setSavedMessage("Saved screen renamed locally.");
    } catch {
      setSavedMessage("Rename failed. The prior name remains.");
    } finally {
      setSavedBusy(false);
    }
  }

  async function deleteSavedScreen() {
    if (!apiBaseUrl || !savedScreenId) return;
    setSavedBusy(true);
    try {
      const response = await fetch(`${apiBaseUrl}/api/market-map-screens/${encodeURIComponent(savedScreenId)}`, { method: "DELETE" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setSavedScreens((current) => current.filter((item) => item.screen_id !== savedScreenId));
      setSavedScreenId("");
      setScreenName("");
      setSavedMessage("Saved screen archived locally.");
    } catch {
      setSavedMessage("Delete failed. The saved screen remains available.");
    } finally {
      setSavedBusy(false);
    }
  }

  if (!instruments.length) {
    return (
      <div className="market-map-empty" data-market-map-state="empty">
        <strong>Market universe unavailable</strong>
        <p>{text(envelope.unavailable[0]?.error || envelope.caveats[0], "No provider-backed or fixture rows are available.")}</p>
      </div>
    );
  }

  const originState = marketMapOriginState(clientParams);
  const workstationHref = selected
    ? canonicalAssetHref(text(selected.symbol), "equity", "1d", runtimeMode, "overview", "3mo", {
        originView: "market-map",
        originState,
      })
    : "/?view=market-map";

  return (
    <div
      className="market-map-screener"
      data-market-map-state="ready"
      data-market-map-rows={String(filtered.length)}
      data-market-map-observations={text(universe.observation_count, "0")}
      data-market-map-listing-coverage={text(universe.official_listing_coverage_count, "0")}
      data-market-map-taxonomy-coverage={text(universe.taxonomy_coverage_count, "0")}
      data-market-map-industry-coverage={text(universe.industry_coverage_count, "0")}
      data-market-map-provider-taxonomy={text(universe.provider_taxonomy_coverage_count, "0")}
      data-market-map-taxonomy-conflicts={text(universe.taxonomy_conflict_count, "0")}
      data-market-snapshot-status={text(materialization.read_status, "unmaterialized")}
      data-market-snapshot-version={text(materialization.snapshot_version, "unmaterialized")}
      data-market-snapshot-created={text(materialization.created_at, "")}
      data-market-refresh-status={text(refreshHealth.status, "never-run")}
      data-market-refresh-calls={text(refreshHealth.provider_call_count, "unknown")}
    >
      <section className="market-map-universe-strip" aria-label="Universe and taxonomy truth">
        <div><span>Scope</span><strong>{text(universe.scope_label)}</strong></div>
        <div><span>Screened</span><strong>{text(universe.screened_observation_count, text(universe.observation_count, "0"))}</strong><small>{text(universe.observation_source_status)}</small></div>
        <div><span>Official listed</span><strong>{text(universe.official_listing_coverage_count, "0")}</strong><small>{text(universe.listing_source_status)}</small></div>
        <div>
          <span>Classification</span>
          <strong>{text(universe.taxonomy_coverage_count, "0")} / {instruments.length}</strong>
          <small>{text(universe.local_taxonomy_coverage_count, "0")} local / {text(universe.provider_taxonomy_coverage_count, "0")} provider</small>
          <small>{text(universe.industry_coverage_count, "0")} industry / {text(universe.taxonomy_conflict_count, "0")} conflicts</small>
        </div>
        <div><span>Excluded</span><strong>{text(universe.excluded_unverified_observation_count, "0")}</strong><small>unverified listing match</small></div>
        <div><span>Index claim</span><strong>{universe.authoritative_index_membership === true ? "authoritative" : "none"}</strong><small>{shortTime(universe.listing_as_of)}</small></div>
        <div>
          <span>Snapshot</span>
          <strong>{text(materialization.read_status, "unmaterialized")}</strong>
          <small>{shortTime(materialization.created_at)} / {formatAge(materialization.age_seconds)}</small>
          <small>{formatDuration(refreshHealth.duration_ms)} / {text(refreshHealth.provider_call_count, "?")} calls</small>
        </div>
      </section>

      {refreshHistory.length ? (
        <section className="market-map-refresh-ledger" aria-label="Recent market snapshot refresh history" data-market-refresh-history={refreshHistory.length}>
          <header>
            <span>Refresh ledger</span>
            <strong>{refreshHistory.length} recent jobs</strong>
          </header>
          {refreshHistory.slice(0, 4).map((row) => (
            <div key={`${text(row.job_id)}-${text(row.started_at)}`} data-refresh-job-status={text(row.status)}>
              <strong>{text(row.status)}</strong>
              <span>{shortTime(row.finished_at || row.started_at)}</span>
              <span>{formatNumber(row.instrument_count)} rows</span>
              <span>{formatNumber(row.taxonomy_coverage_count)} classified</span>
              <span>{formatDuration(row.duration_ms)}</span>
              <span>{text(row.provider_call_count, "?")} calls</span>
            </div>
          ))}
        </section>
      ) : null}

      <section className="market-map-command-bar" aria-label="Market discovery controls">
        <form className="market-map-search" onSubmit={submitQuery}>
          <label htmlFor="market-map-query">Find</label>
          <input id="market-map-query" value={queryDraft} onChange={(event) => setQueryDraft(event.target.value)} placeholder="Symbol, company, sector" />
          <button type="submit">Apply</button>
        </form>
        <div className="market-map-view-tabs" aria-label="Display mode">
          {(["heatmap", "table", "scatter", "factors"] as DisplayMode[]).map((item) => (
            <button type="button" className={display === item ? "active" : ""} key={item} onClick={() => updateParams({ display: item })}>
              {label(item)}
            </button>
          ))}
        </div>
        <button className="market-map-reset" type="button" onClick={resetFilters}>Reset {activeFilterCount ? `(${activeFilterCount})` : ""}</button>
      </section>

      <section className="market-map-filter-deck" aria-label="Composable discovery filters">
        <FilterSelect label="Sector" value={sector} options={["all", ...sectors]} onChange={setSector} />
        <FilterSelect label="Industry" value={industry} options={["all", ...industries]} onChange={(value) => updateParams({ industry: value })} />
        <FilterSelect label="Country" value={country} options={["all", ...countries]} onChange={(value) => updateParams({ country: value })} />
        <FilterSelect label="Exchange" value={exchange} options={["all", ...exchanges]} onChange={(value) => updateParams({ exchange: value })} />
        <FilterSelect label="Market cap" value={filterState.marketCap} options={optionList(discoveryOptions.market_cap)} onChange={(value) => updateParams({ marketCap: value })} />
        <FilterSelect label="1D return" value={filterState.return1d} options={optionList(discoveryOptions.return_1d)} onChange={(value) => updateParams({ return1d: value })} />
        <FilterSelect label="1M return" value={filterState.return1m} options={optionList(discoveryOptions.return_1m)} onChange={(value) => updateParams({ return1m: value })} />
        <FilterSelect label="Volatility" value={filterState.volatility} options={optionList(discoveryOptions.volatility)} onChange={(value) => updateParams({ volatility: value })} />
        <FilterSelect label="RSI" value={filterState.rsi} options={optionList(discoveryOptions.rsi)} onChange={(value) => updateParams({ rsi: value })} />
        <FilterSelect label="Trend" value={filterState.trend} options={optionList(discoveryOptions.trend)} onChange={(value) => updateParams({ trend: value })} />
        <FilterSelect label="Valuation" value={filterState.valuation} options={optionList(discoveryOptions.valuation)} onChange={(value) => updateParams({ valuation: value })} />
        <FilterSelect label="Coverage" value={filterState.quality} options={optionList(discoveryOptions.quality)} onChange={(value) => updateParams({ quality: value })} />
        <FilterSelect label="Rank eligibility" value={eligibility} options={eligibilityOptions} onChange={(value) => updateParams({ eligibility: value })} />
        <FilterSelect label="Freshness" value={sourceStatus} options={["all", ...statuses]} onChange={(value) => updateParams({ freshness: value })} />
      </section>

      <section className="market-map-display-controls" aria-label="Heatmap encoding controls">
        <div><span className="eyebrow">Map encoding</span><strong>{sector === "all" ? "Market -> Sector" : `${sector} -> Industry`}</strong></div>
        <FilterSelect label="Group" value={grouping} options={groupingOptions} onChange={(value) => updateParams({ group: value })} />
        <FilterSelect label="Size" value={sizeMetric} options={sizeMetricOptions} onChange={(value) => updateParams({ size: value })} />
        <FilterSelect label="Color" value={colorMetric} options={colorMetricOptions} onChange={(value) => updateParams({ color: value })} />
        <button type="button" disabled={sector === "all" && industry === "all"} onClick={() => updateParams({ sector: "all", industry: "all", group: "sector" })}>Up one level</button>
      </section>

      <div className="market-map-summary-strip">
        <span><b>{filtered.length}</b> visible</span>
        <span><b>{grouped.length}</b> groups</span>
        <span><b>{filtered.filter((row) => rankFor(row, rankModel).eligible === true).length}</b> rank eligible</span>
        <span><b>{scatterRows.length}</b> comparable</span>
        <span><b>{text(envelope.summary.financial_coverage_count, "0")}</b> financial snapshots</span>
        <span><b>{text(envelope.summary.source_status)}</b> market rows</span>
        <small>{text(modelMetadata.description, text(readiness.ranking_method))}</small>
      </div>

      <div className="market-map-primary-grid">
        <section className={`market-map-main-view mode-${display}`}>
          {filtered.length === 0 ? (
            <div className="market-map-zero-state">
              <strong>No eligible instruments match this screen.</strong>
              <p>Required factors are never filled with zero. Relax a filter or switch rank model to inspect a different eligible set.</p>
              <button type="button" onClick={resetFilters}>Clear active filters</button>
            </div>
          ) : display === "heatmap" ? (
            <Heatmap
              groups={grouped}
              selectedSymbol={text(selected?.symbol)}
              onSelect={selectInstrument}
              onGroupSelect={(group) => grouping === "industry" || sector !== "all"
                ? updateParams({ industry: group })
                : updateParams({ sector: group, industry: "all" })}
              readiness={readiness}
              grouping={grouping}
              sizeMetric={sizeMetric}
              colorMetric={colorMetric}
            />
          ) : display === "table" ? (
            <RankedTable rows={filtered} selectedSymbol={text(selected?.symbol)} compareSymbols={compareSymbols} rankModel={rankModel} onSelect={selectInstrument} onCompare={toggleCompare} />
          ) : display === "scatter" ? (
            <section className="market-map-scatter" aria-labelledby="market-map-scatter-title">
              <div className="market-map-section-heading"><h3 id="market-map-scatter-title">Risk / Return Field</h3><span>1M return vs annualized volatility</span></div>
              <ScatterPlot rows={scatterRows} selectedSymbol={text(selected?.symbol)} onSelect={selectInstrument} rankModel={rankModel} />
            </section>
          ) : (
            <FactorMatrix rows={filtered} factorCatalog={factorCatalog} rankModel={rankModel} onSelect={selectInstrument} />
          )}
        </section>

        <aside className="market-map-selected" aria-labelledby="market-map-selected-title">
          <div className="market-map-section-heading"><h3 id="market-map-selected-title">Instrument Evidence</h3><span>{text(selected?.source_status)}</span></div>
          {selected ? (
            <>
              <div className="market-map-selected-title"><strong>{text(selected.symbol)}</strong><span>{text(selected.name)} / {text(selected.sector)}</span></div>
              <div className="market-map-selected-metrics">
                {[
                  ["Price", formatNumber(selected.price)],
                  ["1D", formatPercent(selected.return_1d_pct)],
                  ["1M", formatPercent(selected.return_1m_pct)],
                  ["Volatility", formatPercent(selected.realized_volatility_pct)],
                  ["Drawdown", formatPercent(selected.drawdown_pct)],
                  ["Model score", formatScore(selectedRank.score)],
                  ["Model rank", text(selectedRank.rank, "excluded")],
                  ["Coverage", `${formatNumber(record(selected.data_quality).score)}%`],
                ].map(([name, value]) => <div key={name}><span>{name}</span><strong>{value}</strong></div>)}
              </div>
              <ContributionList contributions={asRecordArray(selectedRank.contributions)} />
              <dl>
                <div><dt>Market as of</dt><dd>{shortTime(record(selected.market_clock).market_data_as_of)}</dd></div>
                <div><dt>Retrieved</dt><dd>{shortTime(selected.fetched_at)}</dd></div>
                <div><dt>Market source</dt><dd>{text(selected.provider)}</dd></div>
                <div><dt>Listing</dt><dd>{text(record(selected.membership).source_status)}</dd></div>
                <div><dt>Venue / MIC</dt><dd>{text(record(selected.membership).exchange)} / {text(record(selected.membership).mic)}</dd></div>
                <div><dt>Taxonomy</dt><dd>{text(record(selected.taxonomy).source_status)}</dd></div>
                <div><dt>Industry</dt><dd>{text(selected.industry)}</dd></div>
                <div><dt>History factors</dt><dd>{text(selected.history_source_status)}</dd></div>
                <div><dt>Financial source</dt><dd>{text(record(selected.financial_snapshot).provider)}</dd></div>
                <div><dt>Financial state</dt><dd>{text(record(selected.financial_snapshot).source_status)}</dd></div>
              </dl>
              {selectedRank.eligible !== true ? (
                <div className="market-map-rank-gap">
                  <strong>Not eligible for {text(modelMetadata.label, rankModel)}</strong>
                  <span>{stringList(selectedRank.exclusion_reasons).map(label).join(", ") || "Required history/fundamental factors are unavailable."}</span>
                </div>
              ) : null}
              <p>{text(selected.caveat)} {text(selected.data_gap, "")}</p>
              <div className="market-map-selected-actions">
                <button type="button" onClick={() => toggleCompare(text(selected.symbol))}>{compareSymbols.includes(text(selected.symbol)) ? "Remove compare" : "Add compare"}</button>
                {selected.workstation_supported === true || (
                  ["active", "listed"].includes(text(record(selected.membership).listing_status).toLowerCase())
                  && ["equity", "etf", "common-stock", "common stock"].includes(text(record(selected.membership).security_type).toLowerCase())
                )
                  ? <Link href={workstationHref}>Open workstation</Link>
                  : <span title="This listing does not satisfy the current exact-symbol capability contract.">Workstation unavailable</span>}
                {text(selected.source_url).startsWith("http") ? <a href={text(selected.source_url)} target="_blank" rel="noreferrer">Primary source</a> : null}
              </div>
            </>
          ) : null}
        </aside>
      </div>

      <section className="market-map-model-strip" aria-label="Ranking models">
        {Object.values(rankModels).map((modelValue) => {
          const model = record(modelValue);
          const modelId = text(model.model_id, "");
          return (
            <button type="button" className={rankModel === modelId ? "active" : ""} key={modelId} onClick={() => updateParams({ rank: modelId })}>
              <strong>{text(model.label)}</strong>
              <span>{text(model.eligible_count, "0")} eligible</span>
              <small>{text(model.version)}</small>
            </button>
          );
        })}
      </section>

      <div className="market-map-analysis-grid">
        {display === "heatmap" ? (
          <section className="market-map-scatter" aria-labelledby="market-map-mini-scatter-title">
            <div className="market-map-section-heading"><h3 id="market-map-mini-scatter-title">Risk / Return</h3><button type="button" onClick={() => updateParams({ display: "scatter" })}>Expand</button></div>
            <ScatterPlot rows={scatterRows} selectedSymbol={text(selected?.symbol)} onSelect={selectInstrument} rankModel={rankModel} />
          </section>
        ) : (
          <RankModelMethod model={modelMetadata} />
        )}
        <ComparisonTray rows={compared} onSelect={selectInstrument} rankModel={rankModel} />
      </div>

      <section className="market-map-saved-screens" aria-labelledby="market-map-saved-title">
        <div className="market-map-section-heading">
          <div><span className="eyebrow">Local-private research state</span><h3 id="market-map-saved-title">Saved Screens</h3></div>
          <span>{apiBaseUrl ? `${savedScreens.length} local` : "local API required"}</span>
        </div>
        <form onSubmit={saveScreen}>
          <label>
            <span>Saved screen</span>
            <select value={savedScreenId} onChange={(event) => chooseSavedScreen(event.target.value)}>
              <option value="">New screen</option>
              {savedScreens.map((screen) => <option value={screen.screen_id} key={screen.screen_id}>{screen.name}</option>)}
            </select>
          </label>
          <label>
            <span>Name</span>
            <input value={screenName} onChange={(event) => setScreenName(event.target.value)} placeholder="Opening quality screen" maxLength={80} />
          </label>
          <button type="submit" disabled={savedBusy || !screenName.trim()}>Save current</button>
          <button type="button" disabled={savedBusy || !savedScreenId} onClick={applySavedScreen}>Apply</button>
          <button type="button" disabled={savedBusy || !savedScreenId || !screenName.trim()} onClick={renameSavedScreen}>Rename</button>
          <button type="button" disabled={savedBusy || !savedScreenId} onClick={deleteSavedScreen}>Archive</button>
        </form>
        <p>{savedMessage || "Only validated filter/model/display IDs are stored. No private name or definition enters the URL or static fixture."}</p>
      </section>
    </div>
  );
}

function FilterSelect({ label: filterLabel, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  const unique = [...new Set(options.length ? options : ["all"])];
  return (
    <label>
      <span>{filterLabel}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {unique.map((item) => <option value={item} key={item}>{label(item)}</option>)}
      </select>
    </label>
  );
}

function Heatmap({
  groups,
  selectedSymbol,
  onSelect,
  onGroupSelect,
  readiness,
  grouping,
  sizeMetric,
  colorMetric,
}: {
  groups: ReturnType<typeof groupByHierarchy>;
  selectedSymbol: string;
  onSelect: (symbol: string) => void;
  onGroupSelect: (group: string) => void;
  readiness: Row;
  grouping: string;
  sizeMetric: string;
  colorMetric: string;
}) {
  return (
    <section
      className="market-map-heatmap"
      aria-labelledby="market-map-heatmap-title"
      data-heatmap-group={grouping}
      data-heatmap-size={sizeMetric}
      data-heatmap-color={colorMetric}
    >
      <div className="market-map-section-heading">
        <div><span className="eyebrow">Breadth by {label(grouping)}</span><h3 id="market-map-heatmap-title">Market Heatmap</h3></div>
        <span>size {label(sizeMetric)} / color {label(colorMetric)} / {text(readiness.universe_scope)}</span>
      </div>
      <div className="market-map-legend" aria-label={`${label(colorMetric)} legend`}>
        <span className="loss-strong">low</span><span className="loss">-</span><span className="flat">no data / neutral</span><span className="gain">+</span><span className="gain-strong">high</span>
      </div>
      <div className="market-map-sector-board">
        {groups.map((group) => (
          <section className="market-map-sector" key={group.sector} style={{ flexGrow: group.sizeShare }}>
            <header>
              <button type="button" disabled={grouping === "none"} onClick={() => onGroupSelect(group.sector)}>{group.sector}</button>
              <span>{group.rows.length}</span>
            </header>
            <div>
              {group.rows.map((row) => {
                const symbol = text(row.symbol);
                return (
                  <button
                    type="button"
                    className={`market-map-tile ${metricTone(row[colorMetric], colorMetric)}${symbol === selectedSymbol ? " selected" : ""}`}
                    style={{ flexGrow: tileWeight(metricValue(row, sizeMetric), group.maxSize) }}
                    key={symbol}
                    onClick={() => onSelect(symbol)}
                    title={`${text(row.name)} / ${label(colorMetric)} ${metricDisplay(row[colorMetric], colorMetric)} / ${text(row.source_status)} / listing ${text(record(row.membership).source_status)} / taxonomy ${text(record(row.taxonomy).source_status)}`}
                  >
                    <strong>{symbol}</strong>
                    <span>{metricDisplay(row[colorMetric], colorMetric)}</span>
                    <small>{sizeMetric === "equal" ? text(row.exchange) : compactNumber(metricValue(row, sizeMetric))}</small>
                  </button>
                );
              })}
            </div>
          </section>
        ))}
      </div>
    </section>
  );
}

function RankedTable({ rows, selectedSymbol, compareSymbols, rankModel, onSelect, onCompare }: { rows: Row[]; selectedSymbol: string; compareSymbols: string[]; rankModel: string; onSelect: (symbol: string) => void; onCompare: (symbol: string) => void }) {
  return (
    <section className="market-map-ranked-table" aria-labelledby="market-map-ranked-title">
      <div className="market-map-section-heading"><h3 id="market-map-ranked-title">Ranked Discovery Table</h3><span>{rows.length} observed / ineligible rows retain null ranks</span></div>
      <div className="market-map-table-scroll">
        <table>
          <thead><tr>{["Compare", "Rank", "Symbol", "Sector", "Score", "Price", "1D", "1M", "Volatility", "P/E", "Coverage", "Source"].map((item) => <th key={item}>{item}</th>)}</tr></thead>
          <tbody>
            {rows.slice(0, 80).map((row) => {
              const symbol = text(row.symbol);
              const model = rankFor(row, rankModel);
              return (
                <tr key={symbol} className={symbol === selectedSymbol ? "selected" : ""}>
                  <td><input type="checkbox" checked={compareSymbols.includes(symbol)} onChange={() => onCompare(symbol)} aria-label={`Compare ${symbol}`} /></td>
                  <td>{text(model.rank, "-")}</td>
                  <td><button type="button" onClick={() => onSelect(symbol)}>{symbol}</button><small>{text(row.name)}</small></td>
                  <td>{text(row.sector)}</td>
                  <td>{formatScore(model.score)}</td>
                  <td>{formatNumber(row.price)}</td>
                  <td className={returnTone(row.return_1d_pct)}>{formatPercent(row.return_1d_pct)}</td>
                  <td className={returnTone(row.return_1m_pct)}>{formatPercent(row.return_1m_pct)}</td>
                  <td>{formatPercent(row.realized_volatility_pct)}</td>
                  <td>{formatNumber(record(row.factors).trailing_pe)}</td>
                  <td>{formatNumber(record(row.data_quality).score)}%</td>
                  <td><span className={`market-map-source ${sourceTone(row.source_status)}`}>{text(row.source_status)}</span></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function FactorMatrix({ rows, factorCatalog, rankModel, onSelect }: { rows: Row[]; factorCatalog: Row[]; rankModel: string; onSelect: (symbol: string) => void }) {
  const top = rows.slice(0, 24);
  return (
    <section className="market-map-factor-matrix" aria-labelledby="market-map-factors-title">
      <div className="market-map-section-heading"><h3 id="market-map-factors-title">Factor Attribution Matrix</h3><span>{label(rankModel)} / contribution points</span></div>
      <div className="market-map-factor-grid">
        {top.map((row) => {
          const model = rankFor(row, rankModel);
          return (
            <button type="button" key={text(row.symbol)} onClick={() => onSelect(text(row.symbol))}>
              <header><strong>{text(model.rank)}. {text(row.symbol)}</strong><span>{formatScore(model.score)}</span></header>
              {asRecordArray(model.contributions).map((item) => (
                <div key={text(item.factor_id)}>
                  <span>{factorLabel(text(item.factor_id), factorCatalog)}</span>
                  <i style={{ width: `${Math.max(2, Math.min(100, (number(item.contribution) ?? 0) * 5))}%` }} />
                  <b>{formatNumber(item.contribution)}</b>
                </div>
              ))}
            </button>
          );
        })}
      </div>
    </section>
  );
}

function ContributionList({ contributions }: { contributions: Row[] }) {
  return (
    <section className="market-map-contributions" aria-label="Rank contribution reconciliation">
      <header><strong>Score contribution</strong><span>{formatNumber(contributions.reduce((sum, item) => sum + (number(item.contribution) ?? 0), 0))} total</span></header>
      {contributions.map((item) => (
        <div key={text(item.factor_id)}>
          <span>{label(text(item.factor_id))}</span>
          <i><b style={{ width: `${Math.max(2, Math.min(100, (number(item.contribution) ?? 0) * 5))}%` }} /></i>
          <strong>{formatNumber(item.contribution)}</strong>
        </div>
      ))}
      {!contributions.length ? <p>Required factors are missing for this rank model.</p> : null}
    </section>
  );
}

function ComparisonTray({ rows, onSelect, rankModel }: { rows: Row[]; onSelect: (symbol: string) => void; rankModel: string }) {
  return (
    <section className="market-map-compare" aria-labelledby="market-map-compare-title">
      <div className="market-map-section-heading"><h3 id="market-map-compare-title">Comparison Tray</h3><span>{rows.length}/4</span></div>
      {rows.length ? rows.map((row) => (
        <button type="button" key={text(row.symbol)} onClick={() => onSelect(text(row.symbol))}>
          <strong>{text(row.symbol)}</strong><span>{formatScore(rankFor(row, rankModel).score)}</span><small>1M {formatPercent(row.return_1m_pct)} / vol {formatPercent(row.realized_volatility_pct)}</small>
        </button>
      )) : <p>Select instruments from the heatmap, table, scatter, or factor matrix.</p>}
    </section>
  );
}

function RankModelMethod({ model }: { model: Row }) {
  return (
    <section className="market-map-rank-method">
      <div className="market-map-section-heading"><h3>Rank Method</h3><span>{text(model.version)}</span></div>
      <strong>{text(model.label)}</strong>
      <p>{text(model.description)}</p>
      <code>{text(model.formula)}</code>
      <small>{text(model.null_policy)} Reconciliation tolerance {text(model.reconciliation_tolerance)}.</small>
    </section>
  );
}

function ScatterPlot({ rows, selectedSymbol, onSelect, rankModel }: { rows: Row[]; selectedSymbol: string; onSelect: (symbol: string) => void; rankModel: string }) {
  if (!rows.length) return <div className="market-map-scatter-empty">Risk/return history is unavailable for the active filters.</div>;
  const returns = rows.map((row) => number(row.return_1m_pct) ?? 0);
  const volatility = rows.map((row) => number(row.realized_volatility_pct) ?? 0);
  const minReturn = Math.min(...returns);
  const maxReturn = Math.max(...returns);
  const maxVol = Math.max(...volatility, 1);
  const x = (value: number) => 46 + (value / maxVol) * 620;
  const y = (value: number) => 250 - ((value - minReturn) / Math.max(maxReturn - minReturn, 1)) * 210;
  return (
    <svg viewBox="0 0 700 285" role="img" aria-label="One month return versus annualized volatility scatter">
      <line x1="46" y1="250" x2="680" y2="250" />
      <line x1="46" y1="25" x2="46" y2="250" />
      <text x="560" y="275">realized volatility</text>
      <text x="8" y="18">1M return</text>
      {rows.map((row) => {
        const symbol = text(row.symbol);
        const score = number(rankFor(row, rankModel).score) ?? 0;
        return (
          <g
            key={symbol}
            onClick={() => onSelect(symbol)}
            role="button"
            tabIndex={0}
            aria-label={`${symbol}: score ${formatScore(score)}, ${formatPercent(row.return_1m_pct)}, volatility ${formatPercent(row.realized_volatility_pct)}`}
          >
            <circle className={symbol === selectedSymbol ? "selected" : ""} cx={x(number(row.realized_volatility_pct) ?? 0)} cy={y(number(row.return_1m_pct) ?? 0)} r={symbol === selectedSymbol ? 8 : 4 + score / 35} />
          </g>
        );
      })}
    </svg>
  );
}

function groupByHierarchy(rows: Row[], selectedSector: string, grouping: string, sizeMetric: string) {
  const groups = new Map<string, Row[]>();
  rows.forEach((row) => {
    const group = grouping === "none"
      ? "All observed"
      : grouping === "industry" || selectedSector !== "all"
        ? text(row.industry, "Unclassified")
        : text(row.sector, "Unclassified");
    groups.set(group, [...(groups.get(group) ?? []), row]);
  });
  return [...groups.entries()].map(([sector, members]) => ({
    sector,
    rows: members,
    sizeShare: Math.max(1, members.reduce((sum, row) => sum + metricValue(row, sizeMetric), 0)),
    maxSize: Math.max(...members.map((row) => metricValue(row, sizeMetric)), 1),
  })).sort((left, right) => right.sizeShare - left.sizeShare);
}

function rankFor(row: Row, modelId: string): Row {
  return record(record(row.rank_models)[modelId]);
}

function bucketMatch(raw: unknown, bucket: string, family: string) {
  if (bucket === "all") return true;
  const value = number(raw);
  if (value === null) return false;
  if (family === "marketCap") return (bucket === "mega" && value >= 200e9) || (bucket === "large" && value >= 10e9 && value < 200e9) || (bucket === "mid" && value >= 2e9 && value < 10e9);
  if (family === "return") return (bucket === "positive" && value > 0) || (bucket === "negative" && value < 0) || (bucket === "above2" && value >= 2) || (bucket === "below-2" && value <= -2);
  if (family === "volatility") return (bucket === "low" && value < 20) || (bucket === "moderate" && value >= 20 && value <= 35) || (bucket === "high" && value > 35);
  if (family === "rsi") return (bucket === "oversold" && value < 30) || (bucket === "neutral" && value >= 30 && value <= 70) || (bucket === "constructive" && value >= 50 && value <= 70) || (bucket === "overbought" && value > 70);
  return false;
}

function marketMapOriginState(searchParams: URLSearchParams) {
  const allowedKeys = new Set(["mode", "query", "sector", "industry", "country", "exchange", "eligibility", "freshness", "marketCap", "return1d", "return1m", "volatility", "rsi", "trend", "valuation", "quality", "rank", "display", "group", "size", "color", "selected", "compare"]);
  const output = new URLSearchParams();
  searchParams.forEach((value, key) => {
    if (allowedKeys.has(key)) output.set(key, value);
  });
  return output.toString();
}

function factorLabel(factorId: string, catalog: Row[]) {
  const row = catalog.find((item) => text(item.factor_id) === factorId);
  return text(row?.label, label(factorId));
}

function optionList(value: unknown) {
  const options = stringList(value);
  return options.length ? options : ["all"];
}

function formatAge(value: unknown) {
  const seconds = number(value);
  if (seconds === null) return "age unavailable";
  if (seconds < 60) return `${Math.round(seconds)}s old`;
  if (seconds < 3_600) return `${Math.round(seconds / 60)}m old`;
  return `${(seconds / 3_600).toFixed(1)}h old`;
}

function formatDuration(value: unknown) {
  const milliseconds = Number(value);
  if (!Number.isFinite(milliseconds) || milliseconds < 0) return "refresh unknown";
  if (milliseconds < 1000) return `${Math.round(milliseconds)}ms refresh`;
  return `${(milliseconds / 1000).toFixed(1)}s refresh`;
}

function optionsOr(value: unknown, fallback: string[]) {
  const options = stringList(value);
  return options.length ? options : fallback;
}

function allowed(value: string | null, options: string[], fallback: string) {
  return value && options.includes(value) ? value : fallback;
}

function compareValues(left: unknown, right: unknown, direction: "asc" | "desc") {
  const a = number(left);
  const b = number(right);
  if (a === null && b === null) return 0;
  if (a === null) return 1;
  if (b === null) return -1;
  return direction === "asc" ? a - b : b - a;
}

function tileWeight(value: unknown, max: number) {
  return Math.max(1, Math.round(((number(value) ?? 1) / Math.max(max, 1)) * 8));
}

function metricValue(row: Row, metric: string) {
  if (metric === "equal") return 1;
  if (metric === "volume") return number(row.volume) ?? 1;
  return number(row.market_cap) ?? number(row.size_value) ?? 1;
}

function metricDisplay(value: unknown, metric: string) {
  if (metric === "relative_volume") {
    const current = number(value);
    return current === null ? "-" : `${current.toFixed(2)}x`;
  }
  return formatPercent(value);
}

function metricTone(value: unknown, metric: string) {
  if (metric !== "relative_volume") return returnTone(value);
  const current = number(value);
  if (current === null) return "flat";
  if (current >= 2) return "activity-strong";
  if (current >= 1) return "activity";
  if (current < 0.5) return "activity-low";
  return "flat";
}

function returnTone(value: unknown) {
  const current = number(value) ?? 0;
  if (current >= 2) return "gain-strong";
  if (current > 0) return "gain";
  if (current <= -2) return "loss-strong";
  if (current < 0) return "loss";
  return "flat";
}

function sourceTone(value: unknown) {
  const status = text(value);
  if (["live/fresh", "cached"].includes(status)) return "ok";
  if (["stale", "fixture", "static/proxy"].includes(status)) return "warn";
  return "danger";
}

function record(value: unknown): Row {
  return isRecord(value) ? value : {};
}

function number(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() && Number.isFinite(Number(value))) return Number(value);
  return null;
}

function text(value: unknown, fallback = "unavailable") {
  if (value === null || value === undefined || value === "") return fallback;
  return typeof value === "object" ? fallback : String(value);
}

function stringList(value: unknown) {
  return Array.isArray(value) ? value.map((item) => text(item, "")).filter(Boolean) : [];
}

function label(value: string) {
  return value.replaceAll("_", " ").replaceAll("-", " ");
}

function formatPercent(value: unknown) {
  const current = number(value);
  return current === null ? "-" : `${current > 0 ? "+" : ""}${current.toFixed(2)}%`;
}

function formatScore(value: unknown) {
  const current = number(value);
  return current === null ? "-" : current.toFixed(1);
}

function formatNumber(value: unknown) {
  const current = number(value);
  return current === null ? "-" : new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(current);
}

function compactNumber(value: unknown) {
  const current = number(value);
  if (current === null) return "fixture weight";
  return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(current);
}

function shortTime(value: unknown) {
  if (typeof value !== "string" || !value) return "unavailable";
  const date = Date.parse(value);
  return Number.isFinite(date) ? new Intl.DateTimeFormat("en", { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" }).format(date) : value;
}
