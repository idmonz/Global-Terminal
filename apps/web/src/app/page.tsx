import { FinanceChart } from "@/components/FinanceChart";
import { LeafletWarMap } from "@/components/LeafletWarMap";
import { DailyBriefWorkspace } from "@/components/DailyBriefWorkspace";
import { MarketMapScreener } from "@/components/MarketMapScreener";
import { OptionsQuantWorkstation } from "@/components/OptionsQuantWorkstation";
import { PortfolioRiskWorkstation } from "@/components/PortfolioRiskWorkstation";
import { ResearchMemoryWorkstation } from "@/components/ResearchMemoryWorkstation";
import { ProgressiveSymbolWorkstation } from "@/components/ProgressiveSymbolWorkstation";
import { AnalystWorkspace } from "@/components/AnalystWorkspace";
import { SymbolSearch } from "@/components/SymbolSearch";
import { WarMapReplayWorkspace } from "@/components/WarMapReplayWorkspace";
import { WatchlistDesk } from "@/components/WatchlistDesk";
import { AttentionDesk } from "@/components/AttentionDesk";
import { WatchlistAlertManager } from "@/components/WatchlistAlertManager";
import Link from "next/link";

import {
  FIXTURE_DEFINITIONS,
  type ContractEnvelope,
  type FixtureDefinition,
  type FixtureKey,
  type RuntimeMode,
  fixtureDefinitionForKey,
  normalizeRuntimeMode,
  isRecord,
  asRecordArray,
} from "@/lib/contracts";
import {
  findLoadedFixture,
  loadAllFixtures,
  loadCompactSymbolSummary,
  loadCompactAnalystWorkspace,
  loadCompactAnalystPrimaryPanel,
  loadRuntimeFixture,
  loadRuntimeHealth,
  loadStaticFixture,
  rowsForFixture,
  sourceRowsForFixtures,
  statusCounts,
  type LoadedFixture,
  type RuntimeHealthSnapshot,
} from "@/lib/fixtures";
import {
  canonicalAssetHref,
  resolveProductAssetContext,
  type ProductAssetClass,
  type ProductAssetContext,
} from "@/lib/product-routes";

type PageSearchParams = Promise<{
  view?: string | string[];
  mode?: string | string[];
  symbol?: string | string[];
  assetClass?: string | string[];
  timeframe?: string | string[];
  interval?: string | string[];
  range?: string | string[];
  surface?: string | string[];
  chartMode?: string | string[];
  chartType?: string | string[];
  panels?: string | string[];
  expiry?: string | string[];
  optionType?: string | string[];
  moneyness?: string | string[];
  selected?: string | string[];
  compare?: string | string[];
  portfolio?: string | string[];
  period?: string | string[];
  section?: string | string[];
  briefId?: string | string[];
  benchmark?: string | string[];
  collection?: string | string[];
  memoryType?: string | string[];
  tag?: string | string[];
  originId?: string | string[];
  origin?: string | string[];
  originView?: string | string[];
  originState?: string | string[];
  list?: string | string[];
  watchMode?: string | string[];
  sort?: string | string[];
  group?: string | string[];
  panel?: string | string[];
  changeType?: string | string[];
  changeSeverity?: string | string[];
  changeStatus?: string | string[];
  change?: string | string[];
  severity?: string | string[];
  sourceStatus?: string | string[];
  region?: string | string[];
  topic?: string | string[];
  layout?: string | string[];
  split?: string | string[];
  attentionSeverity?: string | string[];
  attentionKind?: string | string[];
  attentionSource?: string | string[];
  attentionRegion?: string | string[];
  review?: string | string[];
  tab?: string | string[];
  selectedTrigger?: string | string[];
}>;

const INITIAL_ATTENTION_ROW_LIMIT = 10;

const TABLE_COLUMNS: Record<FixtureKey, string[]> = {
  "market-intelligence": ["symbol", "label", "asset_class", "last_price", "daily_return_pct", "one_month_return_pct", "source_status", "data_gap"],
  "product-parity": ["page", "label", "product_surface", "web_status", "priority", "source_status", "data_gap"],
  "equity-intelligence": ["date", "symbol", "close", "volume", "provider", "source_status", "data_gap"],
  "financial-fundamentals": ["metric", "value", "category", "provider", "source_status", "data_gap"],
  "options-quant": ["provider", "capability", "source_status", "installed", "key_required", "data_gap"],
  "portfolio-risk": ["symbol", "name", "asset_class", "quantity", "price", "market_value", "weight", "source_status"],
  "research-memory": ["memory_type", "title", "origin_view", "compatibility_period", "compatibility_model", "status", "updated_at"],
  "daily-brief": ["claim_kind", "statement", "source_status", "provider", "confidence", "data_gap"],
  "attention-desk": ["title", "severity", "change_kind", "review_state", "provider", "source_status", "observed_at", "retrieved_at"],
  "screener-drilldown": ["symbol", "label", "sector", "daily_return_pct", "target_command", "target_view", "source_status", "data_gap"],
  "market-map-screener": ["symbol", "name", "sector", "market_cap", "return_1d_pct", "return_1m_pct", "realized_volatility_pct", "rank_score", "source_status"],
  "crypto-intelligence": ["timestamp", "symbol", "close", "open_interest_billions", "funding_rate_bps", "taker_buy_sell_ratio", "source_status", "data_gap"],
  "symbol-directory": ["symbol", "name", "asset_class", "exchange", "currency", "registry_provider", "source_status", "data_gap"],
  "symbol-workstation": ["symbol", "name", "asset_class", "status", "source_status", "history_row_count", "provider"],
  "analyst-workspace": ["panel_id", "title", "symbol", "source_status", "provider", "data_gap"],
  "watchlist-desk": ["symbol", "name", "asset_class", "last_price", "change_pct", "refresh_status", "source_status"],
  "watchlist-alert-manager": ["symbol", "rule_type", "state", "frequency", "source_status", "data_gap"],
  "hosted-scheduler-operations": ["state", "timezone", "cadence_minutes", "next_due_at", "last_completed_at", "source_status"],
  manifest: ["method", "path", "payload_type", "description", "live_fetch_default"],
  "war-room": ["title", "severity", "domain", "freshness", "source_status"],
  "war-room-map": ["title", "severity", "region", "coordinate_status", "source_status", "provider", "data_gap"],
  "war-room-map-replay": ["snapshot_id", "captured_at", "observed_at", "runtime_mode", "source_status", "marker_count"],
  "map-news-event-fusion": ["title", "region", "severity", "source_status", "provider", "data_gap"],
  news: ["title", "severity", "region", "provider", "freshness", "data_gap"],
  "provider-health": ["provider", "status", "availability", "row_count", "error", "recommended_action"],
  layers: ["label", "domain", "provider", "availability", "row_count", "source_status", "recommended_action"],
  feeds: ["label", "provider", "category", "region", "source_type", "requires_key", "caveat"],
  "ai-providers": ["provider", "model", "available", "is_free_mode", "source_status", "warning"],
  "asset-universe": ["asset_class", "label", "primary_identifier", "source_status", "local_status", "live_rows_claimed", "routing_commands", "license_stance"],
  "event-graph": ["type", "label", "source_status", "confidence", "provider", "caveat"],
  "command-workspace": ["command", "label", "result_status", "provider", "source_status", "implementation_status", "data_gap"],
  "research-report": ["section_id", "title", "source_status", "provider", "confidence", "data_gap"],
};

export default async function Home({ searchParams }: { searchParams?: PageSearchParams }) {
  const params = await searchParams;
  const requestedView = firstParam(params?.view);
  const isMapProduct = requestedView === "war-room-map";
  const isMarketMapProduct = requestedView === "market-map";
  const isOptionsProduct = requestedView === "options-quant";
  const isPortfolioProduct = requestedView === "portfolio-risk";
  const isResearchMemoryProduct = requestedView === "research-memory";
  const isWatchlistDeskProduct = requestedView === "watchlist-desk";
  const isAttentionProduct = requestedView === "attention-desk";
  const isAlertManagerProduct = requestedView === "alert-manager";
  const isDailyBriefProduct = requestedView === "daily-brief";
  const isAssetRoute = requestedView === "asset";
  const isAnalystWorkspace = requestedView === "analyst-workspace";
  const isCommandProduct = requestedView === "command-workspace";
  const isNewsProduct = requestedView === "news";
  const isMarketProductHome = !requestedView || requestedView === "home" || requestedView === "market-intelligence";
  const memoryMode = firstParam(params?.mode) === "local" ? "local" : "demo";
  const watchlistMode = firstParam(params?.mode) === "local" ? "local" : "fixture";
  const attentionMode = firstParam(params?.mode) === "fixture" ? "fixture" : "cache";
  const alertMode = firstParam(params?.mode) === "fixture" ? "fixture" : "cache";
  const watchlistId = firstParam(params?.list) || "primary";
  const watchlistSelected = firstParam(params?.selected) || firstParam(params?.symbol);
  const memorySurface = normalizeMemorySurface(firstParam(params?.surface));
  const collection = firstParam(params?.collection) || (memoryMode === "local" ? "local-research" : "demo-research");
  const originId = normalizeResearchOrigin(firstParam(params?.originId));
  const runtimeMode = normalizeRuntimeMode(
    isResearchMemoryProduct
      ? memoryMode === "local" ? "cache" : "fixture"
      : isWatchlistDeskProduct
        ? watchlistMode === "local" ? "cache" : "fixture"
      : isAttentionProduct
        ? attentionMode
      : isAlertManagerProduct
        ? alertMode
      : params?.mode ?? (isMarketProductHome || isAssetRoute || isMapProduct || isAnalystWorkspace || isMarketMapProduct || isOptionsProduct || isPortfolioProduct || isCommandProduct || isNewsProduct ? "live-if-available" : "cache"),
  );
  const assetContext = resolveProductAssetContext(
    firstParam(params?.symbol),
    firstParam(params?.assetClass),
    firstParam(params?.interval) || firstParam(params?.timeframe),
    firstParam(params?.range),
    firstParam(params?.surface),
    firstParam(params?.chartType),
    firstParam(params?.panels),
    firstParam(params?.compare),
    firstParam(params?.origin) || firstParam(params?.originView),
    firstParam(params?.originState),
  );
  const activeDefinition = fixtureDefinitionForKey(
    isAnalystWorkspace
      ? "analyst-workspace"
      : isAttentionProduct
      ? "attention-desk"
      : isAlertManagerProduct
      ? "watchlist-alert-manager"
      : isAssetRoute
      ? assetContext.fixtureKey
      : isMapProduct
        ? "map-news-event-fusion"
        : isMarketMapProduct
          ? "market-map-screener"
          : isOptionsProduct
            ? "options-quant"
          : isPortfolioProduct
            ? "portfolio-risk"
          : isResearchMemoryProduct
            ? "research-memory"
          : isWatchlistDeskProduct
            ? "watchlist-desk"
          : isDailyBriefProduct
            ? "daily-brief"
          : requestedView,
  );
  const apiBaseUrl = (process.env.GLOBAL_TERMINAL_API_BASE_URL ?? process.env.NEXT_PUBLIC_GLOBAL_TERMINAL_API_BASE_URL ?? "http://127.0.0.1:8000").replace(/\/+$/, "");

  if (isAttentionProduct) {
    const staticActiveFixture = await loadStaticFixture(activeDefinition);
    const activeFixture = await loadRuntimeFixture(
      activeDefinition,
      runtimeMode,
      staticActiveFixture,
      { researchMode: attentionMode === "fixture" ? "demo" : "local" },
    );
    const fixtures = [activeFixture];
    const counts = statusCounts(sourceRowsForFixtures(fixtures));
    const runtimeHealth = await loadRuntimeHealth(runtimeMode);
    return (
      <main className="terminal-shell product-shell attention-desk-shell">
        <TopBar activeDefinition={activeDefinition} fixtures={fixtures} statusCounts={counts} runtimeMode={runtimeMode} modeLabel={attentionMode} searchContext={assetContext} symbolIdentities={[]} productMode runtimeHealth={runtimeHealth} />
        <div className="attention-desk-workspace-grid" data-product-view="attention-desk">
          <ProductNav active="attention" runtimeMode={runtimeMode} />
          {activeFixture.envelope ? (
            <AttentionDesk
              envelope={compactAttentionEnvelope(activeFixture.envelope)}
              runtimeMode={runtimeMode}
              initialSeverity={firstParam(params?.attentionSeverity)}
              initialKind={firstParam(params?.attentionKind)}
              initialSource={firstParam(params?.attentionSource)}
              initialRegion={firstParam(params?.attentionRegion)}
              initialReview={firstParam(params?.review)}
            />
          ) : (
            <section className="product-main-panel"><div className="empty-state" role="status"><strong>Attention evidence is unavailable.</strong><span>Stored source rows could not be loaded; no fake review items were substituted.</span></div></section>
          )}
        </div>
      </main>
    );
  }

  if (isAlertManagerProduct) {
    const activeFixture = await loadStaticFixture(activeDefinition);
    const schedulerFixture = await loadStaticFixture(fixtureDefinitionForKey("hosted-scheduler-operations"));
    const fixtures = [activeFixture, schedulerFixture];
    const counts = statusCounts(sourceRowsForFixtures(fixtures));
    const runtimeHealth = await loadRuntimeHealth(runtimeMode);
    return (
      <main className="terminal-shell product-shell alert-manager-shell">
        <TopBar activeDefinition={activeDefinition} fixtures={fixtures} statusCounts={counts} runtimeMode={runtimeMode} modeLabel={alertMode} searchContext={assetContext} symbolIdentities={[]} productMode runtimeHealth={runtimeHealth} />
        <div className="alert-manager-workspace-grid" data-product-view="watchlist-alert-manager">
          <ProductNav active="alerts" runtimeMode={runtimeMode} />
          {activeFixture.envelope ? (
            <WatchlistAlertManager
              envelope={activeFixture.envelope}
              schedulerEnvelope={schedulerFixture.envelope ?? undefined}
              runtimeMode={runtimeMode}
              initialTab={firstParam(params?.tab)}
              initialSelectedTrigger={firstParam(params?.selectedTrigger)}
            />
          ) : <ProductLoadError fixture={activeFixture} />}
        </div>
        <ProviderStrip fixtures={fixtures} statusCounts={counts} runtimeMode={runtimeMode} />
      </main>
    );
  }

  if (isWatchlistDeskProduct) {
    const staticActiveFixture = await loadStaticFixture(activeDefinition);
    const activeFixture = await loadRuntimeFixture(
      activeDefinition,
      runtimeMode,
      staticActiveFixture,
      {
        collection: watchlistId,
        symbol: watchlistSelected,
        researchMode: watchlistMode === "local" ? "local" : "demo",
      },
    );
    const fixtures = [activeFixture];
    const counts = statusCounts(sourceRowsForFixtures(fixtures));
    const runtimeHealth = await loadRuntimeHealth(runtimeMode);
    const symbolIdentities = activeFixture.envelope && isRecord(activeFixture.envelope.data)
      ? asRecordArray(activeFixture.envelope.data.items)
      : [];
    return (
      <main className="terminal-shell product-shell watchlist-desk-shell">
        <TopBar activeDefinition={activeDefinition} fixtures={fixtures} statusCounts={counts} runtimeMode={runtimeMode} modeLabel={watchlistMode} searchContext={assetContext} symbolIdentities={symbolIdentities} productMode runtimeHealth={runtimeHealth} />
        <div className="watchlist-desk-workspace-grid" data-product-view="watchlist-desk">
          <ProductNav active="watchlist" runtimeMode={runtimeMode} />
          {activeFixture.envelope ? (
            <WatchlistDesk
              envelope={activeFixture.envelope}
              apiBaseUrl={apiBaseUrl}
              deskMode={watchlistMode}
              listId={watchlistId}
              runtimeMode={runtimeMode}
              initialSelected={watchlistSelected}
              originView={firstParam(params?.originView)}
              originState={firstParam(params?.originState)}
              initialViewMode={firstParam(params?.watchMode)}
              initialSortMode={firstParam(params?.sort)}
              initialGroupMode={firstParam(params?.group)}
              initialPanel={firstParam(params?.panel)}
              initialChangeType={firstParam(params?.changeType)}
              initialChangeSeverity={firstParam(params?.changeSeverity)}
              initialChangeStatus={firstParam(params?.changeStatus)}
              initialChangeId={firstParam(params?.change)}
            />
          ) : <ProductLoadError fixture={activeFixture} />}
        </div>
        <ProviderStrip fixtures={fixtures} statusCounts={counts} runtimeMode={runtimeMode} />
      </main>
    );
  }

  if (isAnalystWorkspace) {
    const primaryPanel = await loadCompactAnalystPrimaryPanel(assetContext.symbol);
    const activeFixture = await loadCompactAnalystWorkspace(
      activeDefinition,
      assetContext.symbol,
      runtimeMode,
      {
        ...assetContext,
        runtimeMode,
        layout: firstParam(params?.layout) || "research",
        panel: firstParam(params?.panel) || panelForWorkspaceChange(firstParam(params?.changeType)),
        origin: firstParam(params?.origin) || firstParam(params?.originView),
        originState: firstParam(params?.originState),
        list: firstParam(params?.list),
        change: firstParam(params?.change),
        changeType: firstParam(params?.changeType),
        changeSeverity: firstParam(params?.changeSeverity),
        changeStatus: firstParam(params?.changeStatus),
      },
    );
    const fixtures = [activeFixture];
    const counts = statusCounts(sourceRowsForFixtures(fixtures));
    const runtimeHealth = await loadRuntimeHealth(runtimeMode);
    const workspaceData = activeFixture.envelope && isRecord(activeFixture.envelope.data)
      ? activeFixture.envelope.data
      : null;
    const initialIdentity = workspaceData && isRecord(workspaceData.identity)
      ? [workspaceData.identity]
      : [];
    const exactUnknown = !activeFixture.envelope;
    return (
      <main className="terminal-shell product-shell analyst-product-shell">
        <TopBar activeDefinition={activeDefinition} fixtures={fixtures} statusCounts={counts} runtimeMode={runtimeMode} searchContext={assetContext} symbolIdentities={initialIdentity} productMode runtimeHealth={runtimeHealth} />
        <div className="analyst-workspace-grid" data-product-view="analyst-workspace">
          <ProductNav active={assetContext.assetClass === "crypto" ? "crypto" : "equity"} runtimeMode={runtimeMode} />
          {!assetContext.supported || exactUnknown ? (
            <UnknownSymbolWorkspace context={assetContext} runtimeMode={runtimeMode} />
          ) : (
            <AnalystWorkspace
              envelope={activeFixture.envelope as ContractEnvelope}
              context={assetContext}
              runtimeMode={runtimeMode}
              apiBaseUrl="/api/runtime"
              primaryEnvelope={primaryPanel}
            />
          )}
        </div>
        <ProviderStrip fixtures={fixtures} statusCounts={counts} runtimeMode={runtimeMode} />
      </main>
    );
  }

  if (isAssetRoute) {
    const compactFallback = await loadCompactSymbolSummary(activeDefinition, assetContext.symbol);
    const activeFixture = assetContext.supported
      ? await loadRuntimeFixture(
          activeDefinition,
          runtimeMode,
          compactFallback,
          { ...assetContext, runtimeMode, delivery: "summary" },
        )
      : compactFallback;
    const fixtures = [activeFixture];
    const counts = statusCounts(sourceRowsForFixtures(fixtures));
    const runtimeHealth = await loadRuntimeHealth(runtimeMode);
    const initialWorkstation = activeFixture.envelope && isRecord(activeFixture.envelope.data)
      ? asRecordArray(activeFixture.envelope.data.workstations)[0]
      : null;
    const initialIdentity = initialWorkstation && isRecord(initialWorkstation.identity)
      ? [initialWorkstation.identity]
      : [];
    const exactUnknown = !activeFixture.envelope
      && Boolean(activeFixture.runtime?.warning?.includes("HTTP 404"));
    return (
      <main className="terminal-shell product-shell asset-product-shell progressive-asset-shell">
        <TopBar activeDefinition={activeDefinition} fixtures={fixtures} statusCounts={counts} runtimeMode={runtimeMode} searchContext={assetContext} symbolIdentities={initialIdentity} productMode runtimeHealth={runtimeHealth} />
        <div className="product-workspace-grid" data-product-view="asset-workspace">
          <ProductNav active={assetContext.assetClass === "crypto" ? "crypto" : "equity"} runtimeMode={runtimeMode} />
          {!assetContext.supported || exactUnknown ? (
            <UnknownSymbolWorkspace context={assetContext} runtimeMode={runtimeMode} />
          ) : activeFixture.envelope ? (
            <section className="product-main-panel asset-product-workspace">
              <ProgressiveSymbolWorkstation
                envelope={activeFixture.envelope}
                context={assetContext}
                runtimeMode={runtimeMode}
                apiBaseUrl="/api/runtime"
              />
              <div className="asset-runtime-diagnostics" aria-label="Asset runtime diagnostics">
                <RuntimeModeBanner mode={runtimeMode} definition={activeFixture.definition} envelope={activeFixture.envelope} runtime={activeFixture.runtime} />
                <RuntimeFallbackNotice fixture={activeFixture} />
              </div>
            </section>
          ) : <ProductLoadError fixture={activeFixture} />}
          <ProductContextRail
            fixture={activeFixture}
            title={`${assetContext.symbol} source boundary`}
            unavailableReason={assetContext.supported && !exactUnknown ? null : "unknown-symbol"}
          />
        </div>
        <ProviderStrip fixtures={fixtures} statusCounts={counts} runtimeMode={runtimeMode} />
      </main>
    );
  }

  const staticFixtures = await loadAllFixtures();
  const staticActiveFixture = findLoadedFixture(staticFixtures, activeDefinition.key);
  const loadedActiveFixture = isAssetRoute && !assetContext.supported
    ? staticActiveFixture
    : await loadRuntimeFixture(
        activeDefinition,
        runtimeMode,
        staticActiveFixture,
        isOptionsProduct
          ? { ...assetContext, expiry: firstParam(params?.expiry) }
          : isPortfolioProduct
            ? {
                portfolio: firstParam(params?.portfolio) || "demo-core",
                period: firstParam(params?.period) || "1y",
                benchmark: firstParam(params?.benchmark) || "SPY",
              }
            : isResearchMemoryProduct
              ? {
                  collection,
                  surface: memorySurface,
                  researchMode: memoryMode,
                  memoryType: firstParam(params?.memoryType),
                  tag: firstParam(params?.tag),
                }
            : isWatchlistDeskProduct
              ? {
                  collection: watchlistId,
                  symbol: watchlistSelected,
                  researchMode: watchlistMode === "local" ? "local" : "demo",
                }
            : isDailyBriefProduct
              ? { period: normalizeBriefPeriod(firstParam(params?.period)) }
            : { ...assetContext, runtimeMode },
      );
  const activeFixture = isAssetRoute
    ? selectSymbolWorkstationFixture(loadedActiveFixture, assetContext)
    : loadedActiveFixture;
  const staticSymbolDirectoryFixture = findLoadedFixture(staticFixtures, "symbol-directory");
  const symbolDirectoryFixture = await loadRuntimeFixture(
    fixtureDefinitionForKey("symbol-directory"),
    runtimeMode,
    staticSymbolDirectoryFixture,
  );
  const symbolIdentities = symbolDirectoryFixture.envelope && isRecord(symbolDirectoryFixture.envelope.data)
    ? asRecordArray(symbolDirectoryFixture.envelope.data.identities)
    : [];
  const staticNewsFixture = findLoadedFixture(staticFixtures, "news");
  const replayFixture = findLoadedFixture(staticFixtures, "war-room-map-replay");
  const commandFixture = findLoadedFixture(staticFixtures, "command-workspace");
  const warMapFixture = findLoadedFixture(staticFixtures, "war-room-map");
  const marketMapFixture = findLoadedFixture(staticFixtures, "market-map-screener");
  const dailyBriefFixture = findLoadedFixture(staticFixtures, "daily-brief");
  const newsFixture = isMarketProductHome || isNewsProduct
    ? await loadRuntimeFixture(fixtureDefinitionForKey("news"), runtimeMode, staticNewsFixture)
    : staticNewsFixture;
  const fixtures = staticFixtures.map((fixture) =>
    fixture.definition.key === activeDefinition.key
      ? activeFixture
      : fixture.definition.key === "news"
        ? newsFixture
        : fixture,
  );
  const sourceRows = sourceRowsForFixtures(fixtures);
  const counts = statusCounts(sourceRows);
  const runtimeHealth = await loadRuntimeHealth(runtimeMode);

  if (isMarketProductHome) {
    return (
      <main className="terminal-shell product-shell">
        <TopBar activeDefinition={activeDefinition} fixtures={fixtures} statusCounts={counts} runtimeMode={runtimeMode} searchContext={assetContext} symbolIdentities={symbolIdentities} productMode runtimeHealth={runtimeHealth} />
        <div className="product-workspace-grid" data-product-view="market-home">
          <ProductNav active="home" runtimeMode={runtimeMode} />
          <MarketProductHome
            marketFixture={activeFixture}
            newsFixture={newsFixture}
            commandFixture={commandFixture}
            warMapFixture={warMapFixture}
            marketMapFixture={marketMapFixture}
            dailyBriefFixture={dailyBriefFixture}
            runtimeMode={runtimeMode}
          />
          <ProductContextRail fixture={activeFixture} title="Market data boundary" />
        </div>
        <ProviderStrip fixtures={fixtures} statusCounts={counts} runtimeMode={runtimeMode} />
      </main>
    );
  }

  if (isMapProduct) {
    return (
      <main className="terminal-shell product-shell map-product-shell">
        <TopBar activeDefinition={activeDefinition} fixtures={fixtures} statusCounts={counts} runtimeMode={runtimeMode} searchContext={assetContext} symbolIdentities={symbolIdentities} productMode runtimeHealth={runtimeHealth} />
        <div className="global-map-workspace-grid" data-product-view="global-risk-map">
          <ProductNav active="war-map" runtimeMode={runtimeMode} />
          <GlobalRiskMapProduct fixture={activeFixture} runtimeMode={runtimeMode} replayEnvelope={replayFixture.envelope} apiBaseUrl={apiBaseUrl} returnHref={attentionReturnHref(firstParam(params?.origin), firstParam(params?.originView), firstParam(params?.originState))} />
        </div>
        <ProviderStrip fixtures={fixtures} statusCounts={counts} runtimeMode={runtimeMode} />
      </main>
    );
  }

  if (isMarketMapProduct) {
    return (
      <main className="terminal-shell product-shell market-map-product-shell">
        <TopBar activeDefinition={activeDefinition} fixtures={fixtures} statusCounts={counts} runtimeMode={runtimeMode} searchContext={assetContext} symbolIdentities={symbolIdentities} productMode runtimeHealth={runtimeHealth} />
        <div className="market-map-workspace-grid" data-product-view="market-map-screener">
          <ProductNav active="market-map" runtimeMode={runtimeMode} />
          <MarketMapProduct
            fixture={activeFixture}
            runtimeMode={runtimeMode}
            apiBaseUrl={activeFixture.runtime?.source === "runtime-api" ? apiBaseUrl : null}
          />
        </div>
        <ProviderStrip fixtures={fixtures} statusCounts={counts} runtimeMode={runtimeMode} />
      </main>
    );
  }

  if (isOptionsProduct) {
    return (
      <main className="terminal-shell product-shell options-product-shell">
        <TopBar activeDefinition={activeDefinition} fixtures={fixtures} statusCounts={counts} runtimeMode={runtimeMode} searchContext={assetContext} symbolIdentities={symbolIdentities} productMode runtimeHealth={runtimeHealth} />
        <div className="options-workspace-grid" data-product-view="options-quant-workstation">
          <ProductNav active="options" runtimeMode={runtimeMode} />
          <OptionsQuantProduct fixture={activeFixture} runtimeMode={runtimeMode} />
          <ProductContextRail fixture={activeFixture} title="Options source boundary" />
        </div>
        <ProviderStrip fixtures={fixtures} statusCounts={counts} runtimeMode={runtimeMode} />
      </main>
    );
  }

  if (isPortfolioProduct) {
    return (
      <main className="terminal-shell product-shell portfolio-product-shell">
        <TopBar activeDefinition={activeDefinition} fixtures={fixtures} statusCounts={counts} runtimeMode={runtimeMode} searchContext={assetContext} symbolIdentities={symbolIdentities} productMode runtimeHealth={runtimeHealth} />
        <div className="portfolio-workspace-grid" data-product-view="portfolio-risk-workstation">
          <ProductNav active="portfolio" runtimeMode={runtimeMode} />
          <PortfolioRiskProduct fixture={activeFixture} runtimeMode={runtimeMode} />
          <ProductContextRail fixture={activeFixture} title="Portfolio source & privacy" />
        </div>
        <ProviderStrip fixtures={fixtures} statusCounts={counts} runtimeMode={runtimeMode} />
      </main>
    );
  }

  if (isResearchMemoryProduct) {
    return (
      <main className="terminal-shell product-shell research-memory-shell">
        <TopBar activeDefinition={activeDefinition} fixtures={fixtures} statusCounts={counts} runtimeMode={runtimeMode} modeLabel={memoryMode} searchContext={assetContext} symbolIdentities={symbolIdentities} productMode runtimeHealth={runtimeHealth} />
        <div className="research-memory-workspace-grid" data-product-view="research-memory-workstation">
          <ProductNav active="memory" runtimeMode={runtimeMode} />
          {activeFixture.envelope ? (
            <ResearchMemoryWorkstation
              envelope={activeFixture.envelope}
              memoryMode={memoryMode}
              collection={collection}
              surface={memorySurface}
              apiBaseUrl={apiBaseUrl}
              originId={originId}
            />
          ) : <ProductLoadError fixture={activeFixture} />}
        </div>
        <ProviderStrip fixtures={fixtures} statusCounts={counts} runtimeMode={runtimeMode} />
      </main>
    );
  }

  if (isDailyBriefProduct) {
    return (
      <main className="terminal-shell product-shell daily-brief-shell">
        <TopBar activeDefinition={activeDefinition} fixtures={fixtures} statusCounts={counts} runtimeMode={runtimeMode} searchContext={assetContext} symbolIdentities={symbolIdentities} productMode runtimeHealth={runtimeHealth} />
        <div className="daily-brief-workspace-grid" data-product-view="daily-brief-workstation">
          <ProductNav active="brief" runtimeMode={runtimeMode} />
          {activeFixture.envelope ? (
            <div className="daily-brief-main-stack">
              <RuntimeModeBanner mode={runtimeMode} definition={activeFixture.definition} envelope={activeFixture.envelope} runtime={activeFixture.runtime} />
              <RuntimeFallbackNotice fixture={activeFixture} />
              <DailyBriefWorkspace
                envelope={activeFixture.envelope}
                runtimeMode={runtimeMode}
                apiBaseUrl={apiBaseUrl}
                period={normalizeBriefPeriod(firstParam(params?.period))}
                initialSection={normalizeBriefSection(firstParam(params?.section))}
                runtimeWarning={activeFixture.runtime?.warning ?? null}
              />
            </div>
          ) : <ProductLoadError fixture={activeFixture} />}
        </div>
        <ProviderStrip fixtures={fixtures} statusCounts={counts} runtimeMode={runtimeMode} />
      </main>
    );
  }

  if (isNewsProduct) {
    return (
      <main className="terminal-shell product-shell news-product-shell">
        <TopBar activeDefinition={activeDefinition} fixtures={fixtures} statusCounts={counts} runtimeMode={runtimeMode} searchContext={assetContext} symbolIdentities={symbolIdentities} productMode runtimeHealth={runtimeHealth} />
        <div className="news-workspace-grid" data-product-view="news-workspace">
          <ProductNav active="news" runtimeMode={runtimeMode} />
          <NewsIntelligenceProduct
            fixture={activeFixture}
            runtimeMode={runtimeMode}
            severityFilter={normalizeNewsFilter(firstParam(params?.severity))}
            sourceStatusFilter={normalizeNewsFilter(firstParam(params?.sourceStatus))}
            regionFilter={normalizeNewsFilter(firstParam(params?.region))}
            topicFilter={normalizeNewsFilter(firstParam(params?.topic))}
            returnHref={attentionReturnHref(firstParam(params?.origin), firstParam(params?.originView), firstParam(params?.originState))}
          />
          <ProductContextRail fixture={activeFixture} title="News source boundary" />
        </div>
        <ProviderStrip fixtures={fixtures} statusCounts={counts} runtimeMode={runtimeMode} />
      </main>
    );
  }

  if (isCommandProduct) {
    return (
      <main className="terminal-shell product-shell command-product-shell">
        <TopBar activeDefinition={activeDefinition} fixtures={fixtures} statusCounts={counts} runtimeMode={runtimeMode} searchContext={assetContext} symbolIdentities={symbolIdentities} productMode runtimeHealth={runtimeHealth} />
        <div className="command-product-workspace-grid" data-product-view="command-workspace">
          <ProductNav active="command" runtimeMode={runtimeMode} />
          {activeFixture.envelope ? (
            <section className="product-main-panel terminal-command-product">
              <RuntimeModeBanner mode={runtimeMode} definition={activeFixture.definition} envelope={activeFixture.envelope} runtime={activeFixture.runtime} />
              <RuntimeFallbackNotice fixture={activeFixture} />
              <CommandLaunchpad runtimeMode={runtimeMode} />
              <CommandWorkspaceView envelope={activeFixture.envelope} />
            </section>
          ) : <ProductLoadError fixture={activeFixture} />}
          <ProductContextRail fixture={activeFixture} title="Command source boundary" />
        </div>
        <ProviderStrip fixtures={fixtures} statusCounts={counts} runtimeMode={runtimeMode} />
      </main>
    );
  }

  return (
    <main className="terminal-shell">
      <TopBar
        activeDefinition={activeDefinition}
        fixtures={fixtures}
        statusCounts={counts}
        runtimeMode={runtimeMode}
        searchContext={assetContext}
        symbolIdentities={symbolIdentities}
        runtimeHealth={runtimeHealth}
      />
      <div className="workspace-grid">
        <WorkspaceRail activeKey={activeDefinition.key} fixtures={fixtures} runtimeMode={runtimeMode} />
        <ContractWorkspace fixture={activeFixture} runtimeMode={runtimeMode} />
        <IntelligenceRail fixture={activeFixture} runtimeMode={runtimeMode} />
      </div>
      <ProviderStrip fixtures={fixtures} statusCounts={counts} runtimeMode={runtimeMode} />
    </main>
  );
}

function TopBar({
  activeDefinition,
  fixtures,
  statusCounts,
  runtimeMode,
  searchContext,
  symbolIdentities,
  productMode = false,
  modeLabel,
  runtimeHealth,
}: {
  activeDefinition: FixtureDefinition;
  fixtures: LoadedFixture[];
  statusCounts: Record<string, number>;
  runtimeMode: RuntimeMode;
  searchContext: ProductAssetContext;
  symbolIdentities: Record<string, unknown>[];
  productMode?: boolean;
  modeLabel?: string;
  runtimeHealth?: RuntimeHealthSnapshot;
}) {
  const validCount = fixtures.filter((fixture) => fixture.envelope).length;
  const invalidCount = fixtures.length - validCount;
  const unavailableCount = fixtures.reduce((count, fixture) => count + (fixture.envelope?.unavailable.length ?? 0), 0);
  const issueCount = fixtures.reduce((count, fixture) => count + fixture.issues.length, 0);
  const activeFixture = fixtures.find((fixture) => fixture.definition.key === activeDefinition.key);
  const activeUnavailableCount = activeFixture?.envelope?.unavailable.length ?? 0;

  return (
    <header className="top-bar">
      <div className="brand-block">
        <span className="eyebrow">{productMode ? "Market intelligence workspace" : "Contract diagnostics"}</span>
        <h1>Global Terminal / {activeDefinition.shortLabel}</h1>
      </div>
      <SymbolSearch identities={symbolIdentities} context={searchContext} runtimeMode={runtimeMode} />
      <div className="status-cluster" aria-label="Fixture status">
        <StatusPill tone={invalidCount || issueCount ? "danger" : "ok"} label="system" value={invalidCount || issueCount ? "attention" : "operational"} />
        <StatusPill
          tone={productMode && activeUnavailableCount === 0 ? "ok" : "warn"}
          label={productMode ? "active gaps" : "coverage gaps"}
          value={String(productMode ? activeUnavailableCount : unavailableCount)}
        />
        <RuntimeHealthChip health={runtimeHealth} />
        <StatusPill tone={(modeLabel ?? runtimeMode) === "demo" || runtimeMode === "fixture" ? "warn" : "neutral"} label="mode" value={modeLabel ?? runtimeMode} />
        <StatusPill tone="ok" label="source states" value={Object.keys(statusCounts).length.toString()} />
        {!productMode ? <StatusPill tone="neutral" label="envelopes" value={`${validCount}/${fixtures.length}`} /> : null}
      </div>
    </header>
  );
}

function RuntimeHealthChip({ health }: { health?: RuntimeHealthSnapshot }) {
  if (!health) {
    return null;
  }
  const tone = health.reachable ? "ok" : health.source === "fixture-mode" ? "neutral" : "warn";
  const value = health.reachable ? "online" : health.source === "fixture-mode" ? "fixture" : "offline";
  const detail = health.reachable
    ? `${health.routeCount ?? "?"} routes / ${health.providerCount ?? "?"} providers`
    : health.baseUrl || health.launcherCommand;

  return (
    <span
      className={`runtime-health-chip ${tone}`}
      data-runtime-health-state={health.status}
      data-runtime-health-reachable={health.reachable ? "true" : "false"}
      title={health.warning ?? health.requestedUrl ?? health.launcherCommand}
    >
      <small>Runtime API</small>
      <strong>{value}</strong>
      <em>{detail}</em>
    </span>
  );
}

type ProductNavKey = "home" | "attention" | "alerts" | "brief" | "equity" | "crypto" | "war-map" | "market-map" | "options" | "portfolio" | "watchlist" | "memory" | "news" | "providers" | "command";

function ProductNav({ active, runtimeMode }: { active: ProductNavKey; runtimeMode: RuntimeMode }) {
  const analysisMode = runtimeMode === "fixture" ? "fixture" : "live-if-available";
  const links = [
    { key: "home", label: "Market Home", detail: "Tape / heatmap / news", href: `/?view=home&mode=${analysisMode}` },
    { key: "attention", label: "Attention Desk", detail: "Changed / review / sources", href: `/?view=attention-desk&mode=${runtimeMode === "fixture" ? "fixture" : "cache"}` },
    { key: "market-map", label: "Market Map", detail: "Heatmap / ranks", href: `/?view=market-map&mode=${analysisMode}` },
    { key: "equity", label: "Stock Market", detail: "Equities / AAPL default", href: canonicalAssetHref("AAPL", "equity", "1D", analysisMode) },
    { key: "crypto", label: "Crypto Market", detail: "Crypto / BTCUSDT default", href: canonicalAssetHref("BTCUSDT", "crypto", "1D", analysisMode) },
    { key: "options", label: "Options", detail: "Chain / IV / Greeks", href: `/?view=options-quant&symbol=AAPL&mode=${analysisMode}&surface=overview` },
    { key: "war-map", label: "War Map", detail: "Events / layers", href: `/?view=war-room-map&mode=${analysisMode}` },
    { key: "news", label: "News", detail: "Source-backed feed", href: `/?view=news&mode=${analysisMode}` },
    { key: "brief", label: "Daily Brief", detail: "Charts / claims / sources", href: `/?view=daily-brief&mode=${analysisMode}&period=morning&section=overview` },
    { key: "command", label: "Terminal", detail: "Commands / routes", href: `/?view=command-workspace&mode=${analysisMode}` },
    { key: "portfolio", label: "Portfolio", detail: "Holdings / risk / stress", href: "/?view=portfolio-risk&portfolio=demo-core&surface=overview&period=1y&benchmark=SPY&mode=" + analysisMode },
    { key: "watchlist", label: "Watchlist Desk", detail: "Lists / charts / refresh", href: "/?view=watchlist-desk&mode=local&list=primary" },
    { key: "alerts", label: "Alert Manager", detail: "Rules / due checks / history", href: `/?view=alert-manager&mode=${runtimeMode === "fixture" ? "fixture" : "cache"}&tab=rules` },
    { key: "memory", label: "Research Memory", detail: "Notes / watchlists / sources", href: "/?view=research-memory&collection=demo-research&surface=inbox&mode=demo" },
    { key: "providers", label: "Providers", detail: "Health / gaps", href: `/?view=provider-health&mode=${analysisMode}` },
  ];

  return (
    <aside className="product-nav" aria-label="Product navigation">
      <p className="rail-label">Research</p>
      <nav>
        {links.map((link) => (
          <Link prefetch={false} key={link.key} className={`product-nav-link${active === link.key ? " active" : ""}`} href={link.href}>
            <strong>{link.label}</strong>
            <small>{link.detail}</small>
          </Link>
        ))}
      </nav>
      <div className="product-nav-footer">
        <span>Diagnostics</span>
        <Link prefetch={false} href={`/?view=manifest&mode=${runtimeMode}`}>API manifest</Link>
        <Link prefetch={false} href={`/?view=product-parity&mode=${runtimeMode}`}>Parity ledger</Link>
      </div>
    </aside>
  );
}

function MarketProductHome({
  marketFixture,
  newsFixture,
  commandFixture,
  warMapFixture,
  marketMapFixture,
  dailyBriefFixture,
  runtimeMode,
}: {
  marketFixture: LoadedFixture;
  newsFixture: LoadedFixture;
  commandFixture: LoadedFixture;
  warMapFixture: LoadedFixture;
  marketMapFixture: LoadedFixture;
  dailyBriefFixture: LoadedFixture;
  runtimeMode: RuntimeMode;
}) {
  if (!marketFixture.envelope) {
    return <ProductLoadError fixture={marketFixture} />;
  }

  const marketData = isRecord(marketFixture.envelope.data) ? marketFixture.envelope.data : {};
  const marketTape = asRecordArray(marketData.market_tape);
  const marketHeatmap = asRecordArray(marketData.market_heatmap);
  const chartSpecs = asRecordArray(marketData.chart_specs);
  const newsData = newsFixture.envelope && isRecord(newsFixture.envelope.data) ? newsFixture.envelope.data : {};
  const newsRows = [
    ...asRecordArray(newsData.high_severity_feed),
    ...asRecordArray(newsData.event_rows),
    ...asRecordArray(newsData.normalized_news),
  ].slice(0, 8);
  const commandData = commandFixture.envelope && isRecord(commandFixture.envelope.data) ? commandFixture.envelope.data : {};
  const commandResults = asRecordArray(commandData.command_results);
  const commandCount = asRecordArray(commandData.commands).length || commandResults.length;
  const warMapData = warMapFixture.envelope && isRecord(warMapFixture.envelope.data) ? warMapFixture.envelope.data : {};
  const markers = asRecordArray(warMapData.markers);
  const marketMapData = marketMapFixture.envelope && isRecord(marketMapFixture.envelope.data) ? marketMapFixture.envelope.data : {};
  const rankedRows = asRecordArray(marketMapData.ranked_rows);
  const dailyBriefData = dailyBriefFixture.envelope && isRecord(dailyBriefFixture.envelope.data) ? dailyBriefFixture.envelope.data : {};
  const briefClaims = asRecordArray(dailyBriefData.claims);
  const terminalMetrics: { label: string; value: number; tone: "ok" | "warn" | "danger" | "neutral" }[] = [
    { label: "Tape", value: marketTape.length, tone: marketTape.length ? "ok" : "warn" },
    { label: "Charts", value: chartSpecs.length, tone: chartSpecs.length ? "ok" : "warn" },
    { label: "Heatmap", value: marketHeatmap.length, tone: marketHeatmap.length ? "ok" : "warn" },
    { label: "News/Risk", value: newsRows.length + markers.length, tone: newsRows.length || markers.length ? "ok" : "warn" },
    { label: "Map", value: markers.length, tone: markers.length ? "ok" : "warn" },
    { label: "Commands", value: commandCount, tone: commandCount ? "ok" : "warn" },
  ];

  return (
    <section className="product-main-panel market-product-home" aria-labelledby="market-home-title">
      <header className="market-home-header">
        <div>
          <span className="eyebrow">Daily research surface</span>
          <h2 id="market-home-title">Markets, risk and news in one working view</h2>
          <p>Start with cross-asset context, then move directly into an instrument workstation without losing URL state.</p>
        </div>
        <div className="market-home-actions">
          <Link href={`/?view=attention-desk&mode=${runtimeMode === "fixture" ? "fixture" : "cache"}`}>
            <span>Review</span><strong>Attention Desk</strong><small>Material change / source health / exact evidence</small>
          </Link>
          <Link href={`/?view=daily-brief&mode=${runtimeMode}&period=morning&section=overview`}>
            <span>Today</span><strong>Daily Brief</strong><small>Claim ledger / changes / source coverage</small>
          </Link>
          <Link href={canonicalAssetHref("AAPL", "equity", "1D", runtimeMode)}>
            <span>STOCK</span><strong>Stock market</strong><small>AAPL default / price / technicals / fundamentals</small>
          </Link>
          <Link href={canonicalAssetHref("BTCUSDT", "crypto", "1D", runtimeMode)}>
            <span>CRYPTO</span><strong>Crypto market</strong><small>BTCUSDT default / funding / open interest</small>
          </Link>
          <Link href={`/?view=command-workspace&mode=${runtimeMode === "fixture" ? "fixture" : "live-if-available"}`}>
            <span>TERM</span><strong>Command workspace</strong><small>Route / inspect / provider gates</small>
          </Link>
        </div>
      </header>

      <MarketTerminalCockpit
        runtimeMode={runtimeMode}
        metrics={terminalMetrics}
        marketTape={marketTape}
        newsRows={newsRows}
        commandResults={commandResults}
        rankedRows={rankedRows}
        markers={markers}
        briefClaims={briefClaims}
      />

      <RuntimeModeBanner
        mode={runtimeMode}
        definition={marketFixture.definition}
        envelope={marketFixture.envelope}
        runtime={marketFixture.runtime}
      />
      <RuntimeFallbackNotice fixture={marketFixture} />

      <MarketIntelligenceWorkspace envelope={marketFixture.envelope} runtimeMode={runtimeMode} />

      <section className="analysis-section market-news-section" aria-labelledby="market-news-title">
        <div className="section-heading">
          <div>
            <span className="eyebrow">World news monitor</span>
            <h3 id="market-news-title">Latest Source-Backed Events</h3>
          </div>
          <Link href={`/?view=news&mode=${runtimeMode}`}>Open news workspace</Link>
        </div>
        {newsRows.length ? (
          <div className="market-news-grid">
            {newsRows.map((row, index) => (
              <article className="market-news-row" key={`${formatValue(row.event_id || row.link || row.title)}-${index}`}>
                <div>
                  <StatusPill tone={statusTone(row.source_status ?? row.freshness)} label="source" value={formatValue(row.source_status ?? row.freshness)} />
                  <span>{formatValue(row.region ?? row.domain ?? "global")}</span>
                </div>
                <strong>{formatValue(row.title)}</strong>
                <small>{formatValue(row.provider)} / {formatValue(row.fetched_at)} / {formatValue(row.data_gap || row.caveat)}</small>
              </article>
            ))}
          </div>
        ) : (
          <div className="empty-state" role="status"><strong>News is unavailable.</strong><span>No fake headlines are substituted.</span></div>
        )}
      </section>
    </section>
  );
}

function MarketTerminalCockpit({
  runtimeMode,
  metrics,
  marketTape,
  newsRows,
  commandResults,
  rankedRows,
  markers,
  briefClaims,
}: {
  runtimeMode: RuntimeMode;
  metrics: { label: string; value: number; tone: "ok" | "warn" | "danger" | "neutral" }[];
  marketTape: Record<string, unknown>[];
  newsRows: Record<string, unknown>[];
  commandResults: Record<string, unknown>[];
  rankedRows: Record<string, unknown>[];
  markers: Record<string, unknown>[];
  briefClaims: Record<string, unknown>[];
}) {
  const analysisMode = runtimeMode === "fixture" ? "fixture" : "live-if-available";
  const topTape = [...marketTape]
    .sort((left, right) => Math.abs(numericValue(right.daily_return_pct) ?? 0) - Math.abs(numericValue(left.daily_return_pct) ?? 0))
    .slice(0, 5);
  const topRanked = rankedRows.slice(0, 5);
  const topCommands = commandResults.slice(0, 6);
  const topMarkers = markers.slice(0, 4);
  const topClaims = briefClaims.slice(0, 4);

  return (
    <section className="market-terminal-cockpit" aria-labelledby="terminal-cockpit-title" data-phase5s-surface="terminal-cockpit">
      <div className="cockpit-head">
        <div>
          <span className="eyebrow">Terminal cockpit</span>
          <h3 id="terminal-cockpit-title">Live routes, markets, map, news and commands</h3>
        </div>
        <div className="cockpit-metrics">
          {metrics.map((metric) => <StatusPill key={metric.label} tone={metric.tone} label={metric.label} value={String(metric.value)} />)}
        </div>
      </div>

      <div className="cockpit-launch-grid" aria-label="Primary terminal journeys">
        <Link href={`/?view=attention-desk&mode=${runtimeMode === "fixture" ? "fixture" : "cache"}`}><span>ATTN</span><strong>Attention Desk</strong><small>Changed / review / source truth</small></Link>
        <Link href={`/?view=market-map&mode=${analysisMode}`}><span>MMAP</span><strong>Market Map</strong><small>Heatmap / rank / filters</small></Link>
        <Link href="/?view=watchlist-desk&mode=local"><span>WL</span><strong>Watchlist Desk</strong><small>Exact symbols / fast panels / local notes</small></Link>
        <Link href={canonicalAssetHref("AAPL", "equity", "1D", analysisMode)}><span>EQT</span><strong>Stock Market</strong><small>AAPL default / chart / technicals</small></Link>
        <Link href={canonicalAssetHref("BTCUSDT", "crypto", "1D", analysisMode)}><span>CRYPTO</span><strong>Crypto Market</strong><small>BTCUSDT default / funding / basis</small></Link>
        <Link href={`/?view=options-quant&symbol=AAPL&mode=${analysisMode}&surface=overview`}><span>OMON</span><strong>Options</strong><small>Chain / IV / Greeks</small></Link>
        <Link href={`/?view=war-room-map&mode=${analysisMode}`}><span>MAP</span><strong>Risk Map</strong><small>Events / news / layers</small></Link>
        <Link href={`/?view=daily-brief&mode=${analysisMode}&period=morning&section=overview`}><span>BRIEF</span><strong>Daily Brief</strong><small>Claims / charts / sources</small></Link>
        <Link href={`/?view=command-workspace&mode=${analysisMode}`}><span>TERM</span><strong>Commands</strong><small>Route terminal actions</small></Link>
        <Link href="/?view=research-memory&collection=demo-research&surface=inbox&mode=demo"><span>MEM</span><strong>Research Memory</strong><small>Notes / sources / returns</small></Link>
      </div>

      <div className="cockpit-data-grid">
        <section className="cockpit-card" aria-labelledby="cockpit-tape-title">
          <div className="section-heading"><h4 id="cockpit-tape-title">Market Pulse</h4><Link href={`/?view=market-map&mode=${analysisMode}`}>open map</Link></div>
          <div className="cockpit-rowset">
            {topTape.map((row) => (
              <Link className="cockpit-market-row" href={cockpitAssetHref(row.symbol, analysisMode)} key={formatValue(row.symbol)}>
                <strong>{formatValue(row.symbol)}</strong>
                <span>{formatSigned(row.daily_return_pct)} / {formatValue(row.source_status)}</span>
              </Link>
            ))}
          </div>
        </section>

        <section className="cockpit-card" aria-labelledby="cockpit-news-title">
          <div className="section-heading"><h4 id="cockpit-news-title">News And Risk</h4><Link href={`/?view=war-room-map&mode=${analysisMode}`}>open map</Link></div>
          <div className="cockpit-rowset">
            {[...newsRows.slice(0, 2), ...topMarkers.slice(0, 2)].slice(0, 4).map((row, index) => (
              <Link className="cockpit-news-item" href={`/?view=war-room-map&mode=${analysisMode}`} key={`${formatValue(row.title)}-${index}`}>
                <strong>{formatValue(row.title)}</strong>
                <span>{formatValue(row.region ?? row.source_status)} / {formatValue(row.provider ?? row.source)}</span>
              </Link>
            ))}
          </div>
        </section>

        <section className="cockpit-card" aria-labelledby="cockpit-discovery-title">
          <div className="section-heading"><h4 id="cockpit-discovery-title">Discovery</h4><Link href={`/?view=market-map&mode=${analysisMode}`}>rank table</Link></div>
          <div className="cockpit-rowset">
            {(topRanked.length ? topRanked : topTape).slice(0, 4).map((row, index) => (
              <Link className="cockpit-market-row" href={cockpitAssetHref(row.symbol, analysisMode)} key={`${formatValue(row.symbol)}-${index}`}>
                <strong>{formatValue(row.symbol)}</strong>
                <span>rank {formatValue(row.rank ?? index + 1)} / {formatValue(row.source_status)}</span>
              </Link>
            ))}
          </div>
        </section>

        <section className="cockpit-card" aria-labelledby="cockpit-command-title">
          <div className="section-heading"><h4 id="cockpit-command-title">Command Tape</h4><Link href={`/?view=command-workspace&mode=${analysisMode}`}>open terminal</Link></div>
          <div className="cockpit-command-strip">
            {topCommands.map((row) => <Link href={commandHref(row, analysisMode)} key={formatValue(row.command)}>{formatValue(row.command)}</Link>)}
          </div>
          <div className="cockpit-rowset compact">
            {topClaims.slice(0, 2).map((row) => <span key={formatValue(row.claim_id)}>{formatValue(row.statement)}</span>)}
          </div>
        </section>
      </div>
    </section>
  );
}

function cockpitAssetHref(symbol: unknown, mode: RuntimeMode): string {
  const raw = formatValue(symbol).toUpperCase();
  const normalized = raw === "BTC-USD" || raw === "BTCUSD" ? "BTCUSDT" : raw === "ETH-USD" || raw === "ETHUSD" ? "ETHUSDT" : raw;
  const assetClass: ProductAssetClass = normalized.endsWith("USDT")
    ? "crypto"
    : ["SPY", "QQQ", "IWM", "DIA", "VTI", "TLT", "GLD", "SLV", "USO", "IBIT"].includes(normalized)
      ? "etf"
      : "equity";
  return canonicalAssetHref(normalized, assetClass, "1D", mode);
}

function commandHref(row: Record<string, unknown>, mode: RuntimeMode): string {
  const command = formatValue(row.command).toUpperCase();
  const analysisMode = mode === "fixture" ? "fixture" : "live-if-available";
  const routes: Record<string, string> = {
    NI: `/?view=news&mode=${analysisMode}`,
    MAP: `/?view=war-room-map&mode=${analysisMode}`,
    DES: canonicalAssetHref("AAPL", "equity", "1D", analysisMode),
    FA: canonicalAssetHref("AAPL", "equity", "1D", analysisMode, "financials"),
    GP: canonicalAssetHref("AAPL", "equity", "1D", analysisMode, "chart"),
    HP: `/?view=market-map&mode=${analysisMode}`,
    WEI: `/?view=portfolio-risk&portfolio=demo-core&surface=overview&period=1y&benchmark=SPY&mode=${analysisMode}`,
    CURV: `/?view=market-intelligence&mode=${analysisMode}`,
    FXC: `/?view=market-intelligence&mode=${analysisMode}`,
    CRYPTO: canonicalAssetHref("BTCUSDT", "crypto", "1D", analysisMode),
    OMON: `/?view=options-quant&symbol=AAPL&mode=${analysisMode}&surface=overview`,
  };
  return routes[command] ?? `/?view=command-workspace&mode=${analysisMode}`;
}

function FilterGroup({
  label,
  param,
  active,
  options,
  runtimeMode,
}: {
  label: string;
  param: string;
  active: string;
  options: string[];
  runtimeMode: RuntimeMode;
}) {
  return (
    <div className="news-filter-group">
      <span>{label}</span>
      <div>
        {options.slice(0, 10).map((option) => {
          const href = option === "all"
            ? `/?view=news&mode=${runtimeMode}`
            : `/?view=news&mode=${runtimeMode}&${param}=${encodeURIComponent(option)}`;
          return <Link key={`${param}-${option}`} className={"news-filter-chip" + (active === option ? " active" : "")} href={href}>{option}</Link>;
        })}
      </div>
    </div>
  );
}

function uniqueNewsRows(rows: Record<string, unknown>[]): Record<string, unknown>[] {
  const seen = new Set<string>();
  const output: Record<string, unknown>[] = [];
  for (const row of rows) {
    const key = `${formatValue(row.title)}|${formatValue(row.source_url || row.url)}|${formatValue(row.published_at)}`;
    if (!formatValue(row.title) || seen.has(key)) {
      continue;
    }
    seen.add(key);
    output.push(row);
  }
  return output;
}

function newsTopics(row: Record<string, unknown> | undefined): string[] {
  if (!row) {
    return ["global"];
  }
  const values = [
    row.impact_channels,
    row.asset_tags,
    row.region_tags,
    row.domain,
    row.source,
  ];
  const topics = values.flatMap((value) => Array.isArray(value) ? value.map(formatValue) : [formatValue(value)])
    .map((value) => value.trim())
    .filter((value) => value && value !== "none");
  return topics.length ? uniqueStrings(topics) : ["global"];
}

function uniqueStrings(values: string[]): string[] {
  return [...new Set(values.map((value) => value.trim()).filter(Boolean))].sort();
}

function buildNewsClusters(rows: Record<string, unknown>[]): {
  key: string;
  region: string;
  topic: string;
  count: number;
  severity: string;
  sourceStatus: string;
}[] {
  const clusters = new Map<string, { key: string; region: string; topic: string; count: number; severity: string; sourceStatus: string }>();
  for (const row of rows) {
    const region = formatValue(row.region || row.location || "global");
    const topic = newsTopics(row)[0] || "global";
    const key = `${region.toLowerCase()}::${topic.toLowerCase()}`;
    const severity = formatValue(row.severity || "watch");
    const sourceStatus = formatValue(row.source_status || row.freshness || "unknown");
    const current = clusters.get(key) || { key, region, topic, count: 0, severity, sourceStatus };
    current.count += 1;
    if (severityRank(severity) > severityRank(current.severity)) {
      current.severity = severity;
    }
    if (sourceStatus === "live/fresh" || (sourceStatus === "cached" && current.sourceStatus !== "live/fresh")) {
      current.sourceStatus = sourceStatus;
    }
    clusters.set(key, current);
  }
  return [...clusters.values()].sort((left, right) => right.count - left.count || severityRank(right.severity) - severityRank(left.severity));
}

function severityRank(value: string): number {
  const severity = value.toLowerCase();
  if (severity === "critical") return 4;
  if (severity === "high") return 3;
  if (severity === "medium") return 2;
  if (severity === "watch") return 1;
  return 0;
}

function newsMapHref(row: Record<string, unknown>, mode: RuntimeMode): string {
  const region = encodeURIComponent(formatValue(row.region || row.location || "global"));
  return `/?view=war-room-map&mode=${mode}&region=${region}`;
}

function newsAssetHref(row: Record<string, unknown>, mode: RuntimeMode): string {
  const topics = newsTopics(row).join(" ").toLowerCase();
  if (topics.includes("bitcoin") || topics.includes("crypto") || topics.includes("btc")) {
    return canonicalAssetHref("BTCUSDT", "crypto", "1D", mode);
  }
  if (topics.includes("oil") || topics.includes("energy")) {
    return canonicalAssetHref("USO", "etf", "1D", mode);
  }
  if (topics.includes("shipping") || topics.includes("red sea")) {
    return `/?view=market-map&mode=${mode}&sector=Industrials`;
  }
  return `/?view=market-map&mode=${mode}`;
}

function safeExternalHref(value: unknown): string | null {
  const href = formatValue(value);
  if (!href || href === "none") {
    return null;
  }
  try {
    const parsed = new URL(href);
    return parsed.protocol === "https:" || parsed.protocol === "http:" ? parsed.toString() : null;
  } catch {
    return null;
  }
}

function UnknownSymbolWorkspace({ context, runtimeMode }: { context: ProductAssetContext; runtimeMode: RuntimeMode }) {
  return (
    <section
      className="product-main-panel unknown-symbol-state"
      aria-labelledby="unknown-symbol-title"
      data-symbol-workstation-state="unknown-symbol"
      data-symbol={context.symbol}
      data-chart-rows="0"
    >
      <span className="eyebrow danger-text">Unavailable / unknown-symbol</span>
      <h2 id="unknown-symbol-title">No verified workspace for {context.symbol}</h2>
      <p>
        The bounded symbol directory did not resolve this identity. No AAPL, BTCUSDT, or other symbol fixture was substituted.
      </p>
      <dl>
        <div><dt>Requested class</dt><dd>{context.assetClass}</dd></div>
        <div><dt>Interval / range</dt><dd>{context.interval} / {context.range}</dd></div>
        <div><dt>Data gap</dt><dd>unknown-symbol</dd></div>
      </dl>
      <div className="unknown-symbol-actions">
        <Link href={canonicalAssetHref("AAPL", "equity", "1D", runtimeMode)}>Open AAPL</Link>
        <Link href={canonicalAssetHref("BTCUSDT", "crypto", "1D", runtimeMode)}>Open BTCUSDT</Link>
        <Link href={`/?view=home&mode=${runtimeMode}`}>Return to Market Home</Link>
      </div>
    </section>
  );
}

function ProductContextRail({
  fixture,
  title,
  unavailableReason = null,
}: {
  fixture: LoadedFixture;
  title: string;
  unavailableReason?: string | null;
}) {
  const envelope = fixture.envelope;
  return (
    <aside className="product-context-rail" aria-label={title}>
      <div className="section-heading"><h3>{title}</h3><span>truth layer</span></div>
      {unavailableReason ? (
        <section className="unknown-context-boundary">
          <span className="eyebrow danger-text">Unavailable</span>
          <strong>{unavailableReason}</strong>
          <p className="panel-note">No fixture or runtime rows are represented as belonging to this requested symbol.</p>
          <p className="panel-note">Provider and symbol-specific contract validation are required before coverage can be enabled.</p>
        </section>
      ) : envelope ? (
        <>
          {researchOriginForFixture(fixture.definition.key) ? (
            <section className="memory-save-cta">
              <span className="eyebrow">Research Memory</span>
              <p className="panel-note">Carry this workstation into a source-bound local research snapshot.</p>
              <Link href={`/?view=research-memory&collection=demo-research&surface=inbox&mode=demo&originId=${researchOriginForFixture(fixture.definition.key)}`}>Save research snapshot</Link>
            </section>
          ) : null}
          <div className="context-stack">
            {envelope.source_status.slice(0, 8).map((row, index) => <StatusRow key={`product-source-${index}`} row={row} />)}
          </div>
          <section>
            <span className="eyebrow">Caveats</span>
            {envelope.caveats.slice(0, 6).map((item) => <p className="panel-note" key={item}>{item}</p>)}
          </section>
          <section>
            <span className="eyebrow danger-text">Unavailable</span>
            {envelope.unavailable.length ? envelope.unavailable.slice(0, 6).map((row, index) => <StatusRow key={`product-gap-${index}`} row={row} />) : <p className="panel-note">No declared unavailable rows.</p>}
          </section>
        </>
      ) : <p className="panel-note">Contract payload unavailable.</p>}
    </aside>
  );
}

function ProductLoadError({ fixture }: { fixture: LoadedFixture }) {
  return (
    <section className="product-main-panel unknown-symbol-state" role="alert">
      <span className="eyebrow danger-text">Contract unavailable</span>
      <h2>{fixture.definition.label} could not be loaded</h2>
      {fixture.issues.map((issue) => <p key={issue}>{issue}</p>)}
    </section>
  );
}

function WorkspaceRail({ activeKey, fixtures, runtimeMode }: { activeKey: FixtureKey; fixtures: LoadedFixture[]; runtimeMode: RuntimeMode }) {
  return (
    <aside className="workspace-rail" aria-label="Workspaces">
      <p className="rail-label">Workspaces</p>
      <nav>
        {FIXTURE_DEFINITIONS.map((definition) => {
          const fixture = fixtures.find((item) => item.definition.key === definition.key);
          const isActive = activeKey === definition.key;
          const hasIssues = Boolean(fixture?.issues.length);

          return (
            <Link
              key={definition.key}
              className={`rail-link${isActive ? " active" : ""}${hasIssues ? " danger" : ""}`}
              href={`/?view=${definition.key}&mode=${runtimeMode}`}
            >
              <span>{definition.shortLabel}</span>
              <small>{definition.payloadType}</small>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

function ContractWorkspace({ fixture, runtimeMode }: { fixture: LoadedFixture; runtimeMode: RuntimeMode }) {
  if (!fixture.envelope) {
    return (
      <section className="work-panel" aria-labelledby="fixture-error-title">
        <div className="panel-heading">
          <span className="eyebrow danger-text">Malformed Fixture</span>
          <h2 id="fixture-error-title">{fixture.definition.label}</h2>
        </div>
        <div className="error-box" role="alert">
          {fixture.issues.map((issue) => (
            <p key={issue}>{issue}</p>
          ))}
        </div>
      </section>
    );
  }

  const rows = rowsForFixture(fixture);
  const envelope = fixture.envelope;

  return (
    <section className="work-panel" aria-labelledby="workspace-title">
      <div className="panel-heading">
        <span className="eyebrow">{fixture.definition.route}</span>
        <h2 id="workspace-title">{fixture.definition.label}</h2>
        <p>
          {envelope.payload_type} / {envelope.contract_version} / {formatDate(envelope.generated_at)}
        </p>
      </div>
      <RuntimeModeBanner mode={runtimeMode} definition={fixture.definition} envelope={envelope} runtime={fixture.runtime} />
      <RuntimeFallbackNotice fixture={fixture} />
      <SummaryGrid envelope={envelope} />
      {fixture.definition.key === "market-intelligence" ? (
        <MarketIntelligenceWorkspace envelope={envelope} />
      ) : fixture.definition.key === "product-parity" ? (
        <ProductParityWorkspace envelope={envelope} />
      ) : fixture.definition.key === "equity-intelligence" ? (
        <EquityIntelligenceWorkspace envelope={envelope} mode="overview" />
      ) : fixture.definition.key === "financial-fundamentals" ? (
        <FinancialFundamentalsWorkspace envelope={envelope} />
      ) : fixture.definition.key === "options-quant" ? (
        <OptionsQuantWorkspace envelope={envelope} />
      ) : fixture.definition.key === "screener-drilldown" ? (
        <ScreenerDrilldownWorkspace envelope={envelope} />
      ) : fixture.definition.key === "crypto-intelligence" ? (
        <CryptoIntelligenceWorkspace envelope={envelope} />
      ) : fixture.definition.key === "war-room-map" ? (
        <WarRoomMapWorkspace envelope={envelope} />
      ) : fixture.definition.key === "map-news-event-fusion" ? (
        <MapNewsEventFusionWorkspace envelope={envelope} />
      ) : fixture.definition.key === "event-graph" ? (
        <EventGraphWorkspace envelope={envelope} />      ) : fixture.definition.key === "command-workspace" ? (
        <CommandWorkspaceView envelope={envelope} />
      ) : fixture.definition.key === "research-report" ? (
        <ResearchReportWorkspace envelope={envelope} />
      ) : (
        <DataPreview definition={fixture.definition} rows={rows} envelope={envelope} />
      )}
    </section>
  );
}

function RuntimeModeBanner({
  mode,
  definition,
  envelope,
  runtime,
}: {
  mode: RuntimeMode;
  definition: FixtureDefinition;
  envelope: ContractEnvelope;
  runtime?: LoadedFixture["runtime"];
}) {
  const statuses = envelope.source_status
    .map((row) => String(row.source_status ?? row.status ?? row.availability ?? "unknown"))
    .filter(Boolean);
  const uniqueStatuses = Array.from(new Set(statuses));
  const hasLiveRows = uniqueStatuses.some((status) => ["live/fresh", "fresh", "cached", "stale"].includes(status));
  const hasFixtureRows = uniqueStatuses.some((status) => status.includes("fixture"));
  const message =
    mode === "fixture"
      ? "Static fixture mode is deterministic and network-free. Treat these rows as product fixtures unless a row explicitly says live/fresh or cached."
      : mode === "cache"
        ? "Cache mode reads the local API at the configured base URL (default 127.0.0.1:8000); failed requests retain an explicit static fixture fallback."
        : "Live-if-available requests include_runtime=true through the optional local API. Provider failure must remain cached, stale, unavailable, error-labeled, or fixture-fallback.";

  return (
    <section className={`runtime-banner ${mode}`} aria-label="Runtime mode boundary">
      <div>
        <span className="eyebrow">Runtime Boundary</span>
        <strong>{definition.label}</strong>
        <p>{message}</p>
      </div>
      <div className="runtime-banner-status">
        <StatusPill tone={mode === "fixture" ? "warn" : "neutral"} label="mode" value={mode} />
        <StatusPill tone={hasLiveRows ? "ok" : "warn"} label="live/cache rows" value={hasLiveRows ? "present" : "none"} />
        <StatusPill tone={hasFixtureRows ? "warn" : "neutral"} label="fixture rows" value={hasFixtureRows ? "present" : "none"} />
        <StatusPill tone={runtime?.source === "runtime-api" ? "ok" : runtime?.source === "runtime-fallback" ? "warn" : "neutral"} label="web source" value={runtime?.source ?? "static-fixture"} />
        <StatusPill tone="neutral" label="source states" value={String(uniqueStatuses.length)} />
      </div>
    </section>
  );
}

function RuntimeFallbackNotice({ fixture }: { fixture: LoadedFixture }) {
  if (!fixture.runtime?.warning) {
    return null;
  }

  return (
    <div className="runtime-warning" role="status">
      <strong>Runtime fallback</strong>
      <span>{fixture.runtime.warning}</span>
    </div>
  );
}

function SummaryGrid({ envelope }: { envelope: ContractEnvelope }) {
  const summaryEntries = Object.entries(envelope.summary).slice(0, 8);
  const fallbackEntries: [string, unknown][] = [
    ["payload_type", envelope.payload_type],
    ["source_status", envelope.source_status.length],
    ["unavailable", envelope.unavailable.length],
    ["errors", envelope.errors.length],
  ];
  const entries = summaryEntries.length ? summaryEntries : fallbackEntries;

  return (
    <div className="summary-grid" aria-label="Envelope summary">
      {entries.map(([key, value]) => (
        <div className="metric-tile" key={key}>
          <span>{labelize(key)}</span>
          <strong>{formatValue(value)}</strong>
        </div>
      ))}
    </div>
  );
}

function MarketIntelligenceWorkspace({
  envelope,
  runtimeMode = "fixture",
}: {
  envelope: ContractEnvelope;
  runtimeMode?: RuntimeMode;
}) {
  const data = isRecord(envelope.data) ? envelope.data : {};
  const marketTape = asRecordArray(data.market_tape);
  const heatRows = asRecordArray(data.risk_heat);
  const marketHeatmap = asRecordArray(data.market_heatmap);
  const macroContext = asRecordArray(data.macro_context);
  const chartSpecs = asRecordArray(data.chart_specs);

  return (
    <div className="workstation-view">
      <section className="terminal-desk" aria-labelledby="market-desk-title">
        <div>
          <span className="eyebrow">Market Overview</span>
          <h3 id="market-desk-title">Cross-Asset Tape</h3>
        </div>
        <div className="command-input-line">
          <span>CTX</span>
          <code>{marketTape.map((row) => formatValue(row.symbol)).join(" / ")}</code>
        </div>
        <div className="command-desk-status">
          <StatusPill tone="warn" label="source" value={formatValue(envelope.summary.source_status ?? "fixture")} />
          <StatusPill tone="neutral" label="charts" value={String(chartSpecs.length)} />
          <StatusPill tone="neutral" label="assets" value={String(marketTape.length)} />
        </div>
      </section>

      <MarketHeatmapBoard rows={marketHeatmap} runtimeMode={runtimeMode} />

      <ChartSpecGrid chartSpecs={chartSpecs} />

      <div className="analysis-grid two-col">
        <section className="analysis-section" aria-labelledby="market-tape-title">
          <div className="section-heading">
            <h3 id="market-tape-title">Market Tape</h3>
            <span>{marketTape.length} rows</span>
          </div>
          <div className="dense-rowset">
            {marketTape.map((row) => (
              <div className="instrument-row" key={formatValue(row.symbol)}>
                <div>
                  <Link href={canonicalAssetHref(formatValue(row.symbol), "equity", "1D", runtimeMode)}>
                    <strong>{formatValue(row.symbol)}</strong>
                  </Link>
                  <span>{formatValue(row.label)} / {formatValue(row.asset_class)}</span>
                </div>
                <div className="instrument-values">
                  <b>{formatValue(row.last_price)}</b>
                  <small>{formatSigned(row.daily_return_pct)} daily / {formatSigned(row.one_month_return_pct)} 1m</small>
                </div>
                <StatusPill tone={statusTone(row.source_status)} label="source" value={formatValue(row.source_status)} />
              </div>
            ))}
          </div>
        </section>

        <section className="analysis-section" aria-labelledby="macro-context-title">
          <div className="section-heading">
            <h3 id="macro-context-title">Context Links</h3>
            <span>{macroContext.length} themes</span>
          </div>
          <div className="context-stack">
            {macroContext.map((row) => (
              <div className="context-row" key={formatValue(row.theme)}>
                <strong>{formatValue(row.theme)}</strong>
                <span>{formatValue(row.linked_symbols)} / {formatValue(row.source_status)}</span>
                <small>{formatValue(row.data_gap || row.caveat)}</small>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="analysis-section" aria-labelledby="risk-heat-title">
        <div className="section-heading">
          <h3 id="risk-heat-title">Risk Heat</h3>
          <span>move classification</span>
        </div>
        <div className="heat-grid">
          {heatRows.map((row) => (
            <div className="heat-cell" key={formatValue(row.symbol)}>
              <strong>{formatValue(row.symbol)}</strong>
              <span>{formatValue(row.risk_bucket)}</span>
              <div className="heat-meter">
                <i style={{ width: `${Math.max(4, Math.min(100, numericValue(row.score) ?? 0))}%` }} />
              </div>
              <small>{formatValue(row.source_status)} / {formatValue(row.data_gap)}</small>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function MarketHeatmapBoard({ rows, runtimeMode = "fixture" }: { rows: Record<string, unknown>[]; runtimeMode?: RuntimeMode }) {
  if (!rows.length) {
    return (
      <section className="analysis-section" aria-labelledby="market-heatmap-title">
        <div className="section-heading">
          <h3 id="market-heatmap-title">Market Heatmap</h3>
          <span>provider required</span>
        </div>
        <div className="empty-state" role="status">
          <strong>No heatmap rows available.</strong>
          <span>Provider-backed constituents, market caps, and returns are required.</span>
        </div>
      </section>
    );
  }

  const sectors = Array.from(new Set(rows.map((row) => formatValue(row.sector)))).filter(Boolean);

  return (
    <section className="market-heatmap-workspace" aria-labelledby="market-heatmap-title" data-renderer="clean-room-market-heatmap">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Finviz / TradingView Pattern</span>
          <h3 id="market-heatmap-title">Market Heatmap</h3>
        </div>
        <span>{rows.length} synthetic fixture tiles</span>
      </div>
      <div className="market-heatmap-toolbar" aria-label="Heatmap legend">
        <StatusPill tone="neutral" label="size" value="market cap weight" />
        <StatusPill tone="neutral" label="color" value="1D return" />
        <StatusPill tone="warn" label="source" value="fixture" />
        <span className="heatmap-legend">
          <i className="loss-strong" /> -2.5%
          <i className="loss" /> -0.35%
          <i className="flat" /> flat
          <i className="gain" /> +0.35%
          <i className="gain-strong" /> +2.5%
        </span>
      </div>
      <div className="market-heatmap-board">
        {sectors.map((sector) => {
          const sectorRows = rows.filter((row) => formatValue(row.sector) === sector);
          const sectorWeight = sectorRows.reduce((total, row) => total + (numericValue(row.market_cap_weight) ?? 0), 0);
          return (
            <section className="market-heatmap-sector" key={sector}>
              <header>
                <strong>{sector}</strong>
                <span>{shortNumber(sectorWeight)} weight</span>
              </header>
              <div className="market-heatmap-tiles">
                {sectorRows.map((row) => {
                  const change = numericValue(row.daily_return_pct) ?? 0;
                  const weight = numericValue(row.market_cap_weight) ?? 1;
                  const tone = heatmapTone(change);
                  return (
                    <article
                      className={`market-heatmap-tile ${tone}`}
                      key={`${formatValue(row.sector)}-${formatValue(row.symbol)}`}
                      style={{ flexGrow: Math.max(0.8, weight), flexBasis: `${Math.max(5.5, Math.min(36, weight * 3.2))}%` }}
                      title={`${formatValue(row.symbol)} ${formatSigned(change)} / ${formatValue(row.industry)} / ${formatValue(row.source_status)}`}
                    >
                      <strong>{formatValue(row.symbol)}</strong>
                      <b>{formatSigned(change)}</b>
                      <small>{formatValue(row.label)}</small>
                      <Link
                        className="heatmap-drilldown-link"
                        href={canonicalAssetHref(formatValue(row.symbol), "equity", "1D", runtimeMode)}
                      >
                        Open
                      </Link>
                    </article>
                  );
                })}
              </div>
            </section>
          );
        })}
      </div>
      <p className="heatmap-caveat">
        Synthetic clean-room fixture. Real heatmap mode requires provider-backed constituents, market caps, returns, and freshness rows before any live claim.
      </p>
    </section>
  );
}

function ProductParityWorkspace({ envelope }: { envelope: ContractEnvelope }) {
  const data = isRecord(envelope.data) ? envelope.data : {};
  const pages = asRecordArray(data.streamlit_pages);
  const missing = asRecordArray(data.missing_web_surfaces);
  const queue = asRecordArray(data.priority_migration_queue);
  const references = asRecordArray(data.external_reference_map);

  return (
    <div className="workstation-view">
      <section className="terminal-desk" aria-labelledby="parity-title">
        <div>
          <span className="eyebrow">Inventory</span>
          <h3 id="parity-title">Streamlit To Web Parity</h3>
        </div>
        <div className="command-input-line">
          <span>GAP</span>
          <code>{missing.map((row) => formatValue(row.surface)).join(" / ")}</code>
        </div>
        <div className="command-desk-status">
          <StatusPill tone="neutral" label="pages" value={String(pages.length)} />
          <StatusPill tone="warn" label="missing" value={String(missing.length)} />
          <StatusPill tone="ok" label="copied" value={formatValue(envelope.summary.external_source_copied)} />
        </div>
      </section>

      <section className="analysis-section" aria-labelledby="streamlit-pages-title">
        <div className="section-heading">
          <h3 id="streamlit-pages-title">Streamlit Capability Map</h3>
          <span>{pages.length} pages</span>
        </div>
        <div className="table-wrap">
          <table>
            <caption>Streamlit capability inventory</caption>
            <thead>
              <tr>
                {["label", "product_surface", "web_status", "priority", "primary_lib_engines", "data_gap"].map((column) => (
                  <th key={column} scope="col">{labelize(column)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pages.map((row) => (
                <tr key={formatValue(row.page)}>
                  <td>{formatValue(row.label)}</td>
                  <td>{formatValue(row.product_surface)}</td>
                  <td>{formatValue(row.web_status)}</td>
                  <td>{formatValue(row.priority)}</td>
                  <td>{formatValue(row.primary_lib_engines)}</td>
                  <td>{formatValue(row.data_gap)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="analysis-grid two-col">
        <section className="analysis-section" aria-labelledby="migration-title">
          <div className="section-heading">
            <h3 id="migration-title">Migration Queue</h3>
            <span>honest remaining work</span>
          </div>
          <div className="context-stack">
            {queue.map((row) => (
              <div className="context-row" key={formatValue(row.rank)}>
                <strong>{formatValue(row.rank)}. {formatValue(row.surface)}</strong>
                <span>{formatValue(row.status)}</span>
                <small>{formatValue(row.next_step)}</small>
              </div>
            ))}
          </div>
        </section>
        <section className="analysis-section" aria-labelledby="references-title">
          <div className="section-heading">
            <h3 id="references-title">External Boundary</h3>
            <span>{references.length} references</span>
          </div>
          <div className="context-stack">
            {references.map((row) => (
              <div className="context-row" key={formatValue(row.external_project)}>
                <strong>{formatValue(row.external_project)}</strong>
                <span>{formatValue(row.license_stance)} / copied {formatValue(row.copied_source)}</span>
                <small>{formatValue(row.adopted_behavior)}</small>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function EquityIntelligenceWorkspace({
  envelope,
  mode,
  forceChartFallback = false,
}: {
  envelope: ContractEnvelope;
  mode: "overview" | "financials" | "options";
  forceChartFallback?: boolean;
}) {
  const data = isRecord(envelope.data) ? envelope.data : {};
  const symbol = formatValue(data.symbol ?? envelope.summary.symbol ?? "AAPL");
  const priceHistory = asRecordArray(data.price_history);
  const chartSpecs = asRecordArray(data.chart_specs);
  const technical = isRecord(data.technical_diagnostics) ? data.technical_diagnostics : {};
  const financial = isRecord(data.financial_overview) ? data.financial_overview : {};
  const options = isRecord(data.options_gamma_proxy) ? data.options_gamma_proxy : {};
  const valuation = asRecordArray(data.valuation_quality);
  const scenarios = asRecordArray(data.scenario_matrix);
  const events = asRecordArray(data.news_events);
  const providerRows = asRecordArray(data.provider_status);
  const title = mode === "financials" ? "Financial / Fundamentals" : mode === "options" ? "Options / Quant Readiness" : "Equity Intelligence";

  return (
    <div className="workstation-view">
      <section className="terminal-desk" aria-labelledby="equity-title">
        <div>
          <span className="eyebrow">{symbol}</span>
          <h3 id="equity-title">{title}</h3>
        </div>
        <div className="command-input-line">
          <span>CMD</span>
          <code>{symbol} FA / {symbol} DES / {symbol} OMON</code>
        </div>
        <div className="command-desk-status">
          <StatusPill tone={statusTone(envelope.summary.source_status)} label="source" value={formatValue(envelope.summary.source_status)} />
          <StatusPill tone="neutral" label="price rows" value={String(priceHistory.length)} />
          <StatusPill tone="neutral" label="charts" value={String(chartSpecs.length)} />
        </div>
      </section>

      {mode === "overview" ? <ChartSpecGrid chartSpecs={chartSpecs.slice(0, 3)} forceFallback={forceChartFallback} /> : null}

      {mode === "overview" ? (
        <div className="analysis-grid two-col">
          <section className="analysis-section" aria-labelledby="technical-title">
            <div className="section-heading">
              <h3 id="technical-title">Technical Diagnostics</h3>
              <span>{formatValue(technical.source_status)}</span>
            </div>
            <div className="metric-matrix">
              {["latest_price", "price_vs_50dma", "price_vs_200dma", "rsi", "realized_volatility", "range_52w_position"].map((key) => (
                <div className="micro-metric" key={key}>
                  <span>{labelize(key)}</span>
                  <strong>{formatValue(technical[key])}</strong>
                </div>
              ))}
            </div>
            <p className="panel-note">{formatValue(technical.caveat)} {formatValue(technical.data_gap)}</p>
          </section>

          <section className="analysis-section" aria-labelledby="scenario-title">
            <div className="section-heading">
              <h3 id="scenario-title">Scenario Matrix</h3>
              <span>{scenarios.length} scenarios</span>
            </div>
            <div className="context-stack">
              {scenarios.map((row) => (
                <div className="context-row" key={formatValue(row.scenario)}>
                  <strong>{formatValue(row.scenario)} / {formatValue(row.evidence_weight)}</strong>
                  <span>{formatValue(row.source_status)} / {formatValue(row.provider)}</span>
                  <small>{formatValue(row.evidence_summary)} {formatValue(row.data_gap)}</small>
                </div>
              ))}
            </div>
          </section>
        </div>
      ) : null}

      {mode === "financials" ? (
        <div className="analysis-grid two-col">
          <section className="analysis-section" aria-labelledby="financial-title">
            <div className="section-heading">
              <h3 id="financial-title">Financial Overview</h3>
              <span>{formatValue(financial.source_status)}</span>
            </div>
            <dl className="detail-list">
              {["company_name", "sector", "market_cap", "revenue_growth_proxy", "gross_margin_proxy", "free_cashflow_margin_proxy"].map((key) => (
                <div key={key}>
                  <dt>{labelize(key)}</dt>
                  <dd>{formatValue(financial[key])}</dd>
                </div>
              ))}
            </dl>
            <p className="panel-note">{formatValue(financial.caveat)} {formatValue(financial.data_gap)}</p>
          </section>
          <section className="analysis-section" aria-labelledby="valuation-title">
            <div className="section-heading">
              <h3 id="valuation-title">Data Quality</h3>
              <span>{valuation.length} rows</span>
            </div>
            <div className="heat-grid compact">
              {valuation.map((row) => (
                <div className="heat-cell" key={formatValue(row.metric)}>
                  <strong>{formatValue(row.metric)}</strong>
                  <span>{formatValue(row.status)} / {formatValue(row.source_status)}</span>
                  <div className="heat-meter"><i style={{ width: `${Math.max(4, Math.min(100, numericValue(row.score) ?? 0))}%` }} /></div>
                  <small>{formatValue(row.data_gap)}</small>
                </div>
              ))}
            </div>
          </section>
        </div>
      ) : null}

      {mode === "options" ? (
        <div className="analysis-grid two-col">
          <section className="analysis-section" aria-labelledby="options-title">
            <div className="section-heading">
              <h3 id="options-title">Options Readiness</h3>
              <span>{formatValue(options.source_status)}</span>
            </div>
            <dl className="detail-list">
              {["put_call_open_interest_ratio", "put_call_volume_ratio", "estimated_gamma_concentration_proxy", "provider", "source_status"].map((key) => (
                <div key={key}>
                  <dt>{labelize(key)}</dt>
                  <dd>{formatValue(options[key])}</dd>
                </div>
              ))}
            </dl>
            <p className="panel-note">{formatValue(options.caveat)} {formatValue(options.data_gap)}</p>
          </section>
          <section className="analysis-section" aria-labelledby="options-scenarios-title">
            <div className="section-heading">
              <h3 id="options-scenarios-title">Volatility Context</h3>
              <span>scenario rows</span>
            </div>
            <div className="context-stack">
              {scenarios.map((row) => (
                <div className="context-row" key={formatValue(row.scenario)}>
                  <strong>{formatValue(row.scenario)} / {formatValue(row.evidence_weight)}</strong>
                  <span>{formatValue(row.provider)} / {formatValue(row.source_status)}</span>
                  <small>{formatValue(row.caveat)} {formatValue(row.data_gap)}</small>
                </div>
              ))}
            </div>
          </section>
        </div>
      ) : null}

      {mode !== "overview" ? <ChartSpecGrid chartSpecs={chartSpecs.slice(2)} /> : null}

      <section className="analysis-section" aria-labelledby="equity-provider-title">
        <div className="section-heading">
          <h3 id="equity-provider-title">Provider And Event Context</h3>
          <span>{providerRows.length} source rows / {events.length} events</span>
        </div>
        <div className="provider-context-grid">
          <div className="context-stack">
            {providerRows.slice(0, 6).map((row, index) => (
              <StatusRow key={`equity-provider-${index}`} row={row} />
            ))}
          </div>
          <div className="context-stack">
            {events.length ? events.map((row) => (
              <div className="context-row" key={formatValue(row.event_id)}>
                <strong>{formatValue(row.title)}</strong>
                <span>{formatValue(row.region)} / {formatValue(row.source_status)}</span>
                <small>{formatValue(row.data_gap || row.caveat)}</small>
              </div>
            )) : <p className="panel-note">No source-backed company news rows in this fixture.</p>}
          </div>
        </div>
      </section>
    </div>
  );
}

function FinancialFundamentalsWorkspace({ envelope }: { envelope: ContractEnvelope }) {
  const data = isRecord(envelope.data) ? envelope.data : {};
  const symbol = formatValue(data.symbol ?? envelope.summary.symbol ?? "AAPL");
  const overview = isRecord(data.financial_overview) ? data.financial_overview : {};
  const metrics = asRecordArray(data.statement_metrics);
  const quality = asRecordArray(data.valuation_quality);
  const chartSpecs = asRecordArray(data.chart_specs);
  const sources = asRecordArray(data.source_register);
  const unavailable = asRecordArray(data.unavailable_sources);
  const commands = asRecordArray(data.command_routes);

  return (
    <div className="workstation-view fundamentals-workstation" data-workspace="FinancialFundamentalsWorkspace">
      <section className="terminal-desk" aria-labelledby="fundamentals-title">
        <div>
          <span className="eyebrow">{symbol}</span>
          <h3 id="fundamentals-title">Financial Fundamentals</h3>
        </div>
        <div className="command-input-line">
          <span>DES</span>
          <code>{commands.map((route) => formatValue(route.raw)).join(" / ") || `${symbol} DES / ${symbol} KEY`}</code>
        </div>
        <div className="command-desk-status">
          <StatusPill tone={statusTone(envelope.summary.source_status)} label="source" value={formatValue(envelope.summary.source_status)} />
          <StatusPill tone="neutral" label="metrics" value={String(metrics.length)} />
          <StatusPill tone={unavailable.length ? "warn" : "ok"} label="data gaps" value={String(unavailable.length)} />
        </div>
      </section>

      <div className="analysis-grid two-col">
        <section className="analysis-section" aria-labelledby="company-profile-title">
          <div className="section-heading">
            <h3 id="company-profile-title">Company Profile</h3>
            <span>{formatValue(overview.source_status)}</span>
          </div>
          <dl className="detail-list">
            {["company_name", "sector", "market_cap", "revenue_growth_proxy", "gross_margin_proxy", "free_cashflow_margin_proxy"].map((key) => (
              <div key={key}>
                <dt>{labelize(key)}</dt>
                <dd>{formatValue(overview[key])}</dd>
              </div>
            ))}
          </dl>
          <p className="panel-note">{formatValue(overview.caveat)} {formatValue(overview.data_gap)}</p>
        </section>

        <section className="analysis-section" aria-labelledby="statement-metrics-title">
          <div className="section-heading">
            <h3 id="statement-metrics-title">Statement Metrics</h3>
            <span>{metrics.length} rows</span>
          </div>
          <div className="metric-matrix fundamentals-metric-grid">
            {metrics.map((row) => (
              <div className="micro-metric" key={formatValue(row.metric)}>
                <span>{formatValue(row.category)}</span>
                <strong>{formatValue(row.value)}</strong>
                <small>{formatValue(row.metric)} / {formatValue(row.source_status)}</small>
              </div>
            ))}
          </div>
        </section>
      </div>

      <ChartSpecGrid chartSpecs={chartSpecs} />

      <div className="analysis-grid two-col">
        <section className="analysis-section" aria-labelledby="valuation-quality-title">
          <div className="section-heading">
            <h3 id="valuation-quality-title">Valuation And Data Quality</h3>
            <span>{quality.length} checks</span>
          </div>
          <div className="heat-grid compact">
            {quality.map((row) => (
              <div className="heat-cell" key={formatValue(row.metric)}>
                <strong>{formatValue(row.metric)}</strong>
                <span>{formatValue(row.status)} / {formatValue(row.source_status)}</span>
                <div className="heat-meter">
                  <i style={{ width: `${Math.max(4, Math.min(100, numericValue(row.score) ?? 0))}%` }} />
                </div>
                <small>{formatValue(row.data_gap || row.caveat)}</small>
              </div>
            ))}
          </div>
        </section>

        <section className="analysis-section" aria-labelledby="financial-source-title">
          <div className="section-heading">
            <h3 id="financial-source-title">Source Register</h3>
            <span>{sources.length} rows</span>
          </div>
          <div className="context-stack">
            {sources.slice(0, 8).map((row, index) => (
              <StatusRow key={`financial-source-${index}`} row={row} />
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function OptionsQuantWorkspace({ envelope }: { envelope: ContractEnvelope }) {
  const data = isRecord(envelope.data) ? envelope.data : {};
  const symbol = formatValue(data.symbol ?? envelope.summary.symbol ?? "AAPL");
  const options = isRecord(data.options_gamma_proxy) ? data.options_gamma_proxy : {};
  const capabilities = asRecordArray(data.provider_capabilities);
  const greeks = asRecordArray(data.greeks_table);
  const scenarios = asRecordArray(data.scenario_table);
  const scenarioMatrix = asRecordArray(data.scenario_matrix);
  const structures = asRecordArray(data.strategy_templates);
  const readiness = isRecord(data.readiness) ? data.readiness : {};
  const sources = asRecordArray(data.source_register);
  const unavailable = asRecordArray(data.unavailable_sources);
  const availableCapabilities = capabilities.filter((row) => row.source_status === "supplied").length;

  return (
    <div className="workstation-view options-quant-workstation" data-workspace="OptionsQuantWorkspace">
      <section className="terminal-desk" aria-labelledby="options-quant-title">
        <div>
          <span className="eyebrow">{symbol}</span>
          <h3 id="options-quant-title">Options Quant</h3>
        </div>
        <div className="command-input-line">
          <span>OMON</span>
          <code>{symbol} OMON / PRICE OPTION / SOLVE IV</code>
        </div>
        <div className="command-desk-status">
          <StatusPill tone={availableCapabilities ? "ok" : "warn"} label="calculator" value={availableCapabilities ? "supplied" : "gated"} />
          <StatusPill tone="warn" label="live chain" value={formatValue(readiness.live_option_chain_claimed)} />
          <StatusPill tone={unavailable.length ? "danger" : "ok"} label="provider gaps" value={String(unavailable.length)} />
        </div>
      </section>

      <section className="analysis-section options-boundary-panel" aria-labelledby="options-boundary-title">
        <div className="section-heading">
          <h3 id="options-boundary-title">Coverage Boundary</h3>
          <span>{formatValue(options.source_status)}</span>
        </div>
        <div className="readiness-grid">
          {[
            ["Live option chain", readiness.live_option_chain_claimed],
            ["GEX claimed", readiness.gex_claimed],
            ["Dealer positioning", readiness.dealer_positioning_claimed],
            ["Manual calculator", readiness.manual_calculator_available],
            ["Provider required", readiness.provider_required],
          ].map(([label, value]) => (
            <div className="boundary-row" key={label as string}>
              <strong>{label as string}</strong>
              <span>{formatValue(value)}</span>
              <small>{value === true ? "Available or explicitly supplied." : "Not claimed in this fixture/runtime mode."}</small>
            </div>
          ))}
        </div>
      </section>

      <div className="analysis-grid two-col">
        <section className="analysis-section" aria-labelledby="provider-capabilities-title">
          <div className="section-heading">
            <h3 id="provider-capabilities-title">Provider Capabilities</h3>
            <span>{capabilities.length} checks</span>
          </div>
          <div className="context-stack">
            {capabilities.map((row, index) => (
              <div className="context-row" key={`capability-${index}`}>
                <strong>{formatValue(row.provider)}</strong>
                <span>{formatValue(row.capability)} / {formatValue(row.source_status)}</span>
                <small>{formatValue(row.data_gap || row.caveat || row.notice)}</small>
              </div>
            ))}
          </div>
        </section>

        <section className="analysis-section" aria-labelledby="options-proxy-title">
          <div className="section-heading">
            <h3 id="options-proxy-title">Gamma And Flow Readiness</h3>
            <span>{formatValue(options.source_status)}</span>
          </div>
          <dl className="detail-list">
            {["put_call_open_interest_ratio", "put_call_volume_ratio", "estimated_gamma_concentration_proxy", "provider", "freshness"].map((key) => (
              <div key={key}>
                <dt>{labelize(key)}</dt>
                <dd>{formatValue(options[key])}</dd>
              </div>
            ))}
          </dl>
          <p className="panel-note">{formatValue(options.caveat)} {formatValue(options.data_gap)}</p>
        </section>
      </div>

      <div className="analysis-grid two-col">
        <section className="analysis-section" aria-labelledby="greeks-title">
          <div className="section-heading">
            <h3 id="greeks-title">Greeks Snapshot</h3>
            <span>{greeks.length} model rows</span>
          </div>
          <div className="greeks-grid">
            {greeks.map((row) => (
              <div className="micro-metric" key={formatValue(row.greek)}>
                <span>{formatValue(row.greek)}</span>
                <strong>{formatValue(row.value)}</strong>
                <small>{formatValue(row.unit)} / research {formatValue(row.research_only)}</small>
              </div>
            ))}
          </div>
        </section>

        <section className="analysis-section" aria-labelledby="options-scenarios-title">
          <div className="section-heading">
            <h3 id="options-scenarios-title">Scenario Surface</h3>
            <span>{scenarios.length} rows</span>
          </div>
          <div className="scenario-strip">
            {scenarios.slice(0, 9).map((row, index) => (
              <div className="context-row" key={`options-scenario-${index}`}>
                <strong>{formatValue(row.underlying_price)} / vol {formatValue(row.volatility)}</strong>
                <span>price {formatValue(row.price)} / delta {formatValue(row.delta)}</span>
                <small>gamma {formatValue(row.gamma)} / theta {formatValue(row.theta_per_day)}</small>
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className="analysis-grid two-col">
        <section className="analysis-section" aria-labelledby="structure-templates-title">
          <div className="section-heading">
            <h3 id="structure-templates-title">Structure Templates</h3>
            <span>{structures.length} rows</span>
          </div>
          <div className="context-stack">
            {structures.slice(0, 6).map((row, index) => (
              <div className="context-row" key={`structure-${index}`}>
                <strong>{formatValue(row.name || row.template || row.strategy)}</strong>
                <span>{formatValue(row.research_only ?? row.source_status)}</span>
                <small>{formatValue(row.caveat || row.description || row.data_gap)}</small>
              </div>
            ))}
          </div>
        </section>

        <section className="analysis-section" aria-labelledby="options-source-title">
          <div className="section-heading">
            <h3 id="options-source-title">Source Register</h3>
            <span>{sources.length} rows / {scenarioMatrix.length} equity scenarios</span>
          </div>
          <div className="context-stack">
            {sources.map((row, index) => (
              <StatusRow key={`options-source-${index}`} row={row} />
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function ScreenerDrilldownWorkspace({ envelope }: { envelope: ContractEnvelope }) {
  const data = isRecord(envelope.data) ? envelope.data : {};
  const tiles = asRecordArray(data.drilldown_tiles);
  const sectors = asRecordArray(data.sector_summaries);
  const sources = asRecordArray(data.source_register);
  const unavailable = asRecordArray(data.unavailable_sources);

  return (
    <div className="workstation-view screener-drilldown-workstation" data-workspace="ScreenerDrilldownWorkspace">
      <section className="terminal-desk" aria-labelledby="screener-drilldown-title">
        <div>
          <span className="eyebrow">Heatmap Drilldown</span>
          <h3 id="screener-drilldown-title">Screener Matrix</h3>
        </div>
        <div className="command-input-line">
          <span>SCREEN</span>
          <code>{tiles.slice(0, 8).map((tile) => formatValue(tile.target_command)).join(" / ")}</code>
        </div>
        <div className="command-desk-status">
          <StatusPill tone="neutral" label="tiles" value={String(tiles.length)} />
          <StatusPill tone="neutral" label="sectors" value={String(sectors.length)} />
          <StatusPill tone={unavailable.length ? "warn" : "ok"} label="live screener" value={unavailable.length ? "provider required" : "available"} />
        </div>
      </section>

      <section className="analysis-section" aria-labelledby="drilldown-grid-title">
        <div className="section-heading">
          <h3 id="drilldown-grid-title">Tile Drilldowns</h3>
          <span>{tiles.length} source-labeled targets</span>
        </div>
        <div className="drilldown-grid">
          {tiles.map((tile) => {
            const change = numericValue(tile.daily_return_pct) ?? 0;
            return (
              <article className={`drilldown-card ${heatmapTone(change)}`} key={`${formatValue(tile.symbol)}-${formatValue(tile.sector)}`}>
                <div className="result-card-top">
                  <code>{formatValue(tile.symbol)}</code>
                  <span>{formatSigned(change)}</span>
                </div>
                <strong>{formatValue(tile.label)}</strong>
                <small>{formatValue(tile.sector)} / {formatValue(tile.industry)}</small>
                <small>{formatValue(tile.source_status)} / confidence {formatValue(tile.confidence)}</small>
                <Link className="drilldown-action" href={formatValue(tile.web_href)}>
                  {formatValue(tile.target_command)}
                </Link>
              </article>
            );
          })}
        </div>
      </section>

      <div className="analysis-grid two-col">
        <section className="analysis-section" aria-labelledby="sector-summary-title">
          <div className="section-heading">
            <h3 id="sector-summary-title">Sector Summaries</h3>
            <span>{sectors.length} sectors</span>
          </div>
          <div className="context-stack">
            {sectors.map((row) => (
              <div className="context-row" key={formatValue(row.sector)}>
                <strong>{formatValue(row.sector)}</strong>
                <span>{formatValue(row.tile_count)} tiles / weight {formatValue(row.weight)}</span>
                <small>Strongest {formatValue(row.strongest_symbol)} / weakest {formatValue(row.weakest_symbol)} / {formatValue(row.data_gap)}</small>
              </div>
            ))}
          </div>
        </section>

        <section className="analysis-section" aria-labelledby="screener-source-title">
          <div className="section-heading">
            <h3 id="screener-source-title">Provider Boundary</h3>
            <span>{sources.length} source rows</span>
          </div>
          <div className="context-stack">
            {unavailable.map((row, index) => (
              <StatusRow key={`screener-unavailable-${index}`} row={row} />
            ))}
            {sources.slice(0, 6).map((row, index) => (
              <StatusRow key={`screener-source-${index}`} row={row} />
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function CryptoIntelligenceWorkspace({
  envelope,
  forceChartFallback = false,
}: {
  envelope: ContractEnvelope;
  forceChartFallback?: boolean;
}) {
  const data = isRecord(envelope.data) ? envelope.data : {};
  const symbol = formatValue(data.symbol ?? envelope.summary.symbol ?? "BTCUSDT");
  const chartSpecs = asRecordArray(data.chart_specs);
  const snapshot = isRecord(data.derivatives_snapshot) ? data.derivatives_snapshot : {};
  const overview = isRecord(data.market_overview) ? data.market_overview : {};
  const timeseries = asRecordArray(data.derivatives_timeseries);
  const scenarios = asRecordArray(data.scenario_matrix);
  const pressure = asRecordArray(data.liquidation_pressure_proxy);
  const providerRows = asRecordArray(data.provider_status);

  return (
    <div className="workstation-view">
      <section className="terminal-desk" aria-labelledby="crypto-title">
        <div>
          <span className="eyebrow">{symbol}</span>
          <h3 id="crypto-title">Crypto Intelligence</h3>
        </div>
        <div className="command-input-line">
          <span>CMD</span>
          <code>{symbol} CRYPTO / NI</code>
        </div>
        <div className="command-desk-status">
          <StatusPill tone={statusTone(envelope.summary.source_status)} label="source" value={formatValue(envelope.summary.source_status)} />
          <StatusPill tone="neutral" label="rows" value={String(timeseries.length)} />
          <StatusPill tone="neutral" label="charts" value={String(chartSpecs.length)} />
        </div>
      </section>

      <ChartSpecGrid chartSpecs={chartSpecs} forceFallback={forceChartFallback} />

      <div className="analysis-grid two-col">
        <section className="analysis-section" aria-labelledby="crypto-snapshot-title">
          <div className="section-heading">
            <h3 id="crypto-snapshot-title">Market And Derivatives</h3>
            <span>{formatValue(snapshot.source_status)}</span>
          </div>
          <div className="metric-matrix">
            {[
              ["current_price", overview.current_price ?? snapshot.mark_price],
              ["premium_pct", snapshot.premium_pct],
              ["open_interest_billions", snapshot.open_interest_billions],
              ["funding_rate_bps", snapshot.funding_rate_bps],
              ["taker_ratio", snapshot.taker_buy_sell_ratio],
              ["long_short_ratio", snapshot.global_long_short_ratio],
            ].map(([label, value]) => (
              <div className="micro-metric" key={String(label)}>
                <span>{labelize(String(label))}</span>
                <strong>{formatValue(value)}</strong>
              </div>
            ))}
          </div>
          <p className="panel-note">{formatValue(snapshot.caveat)} {formatValue(snapshot.data_gap)}</p>
        </section>

        <section className="analysis-section" aria-labelledby="crypto-scenarios-title">
          <div className="section-heading">
            <h3 id="crypto-scenarios-title">Scenario Matrix</h3>
            <span>{scenarios.length} rows</span>
          </div>
          <div className="context-stack">
            {scenarios.map((row) => (
              <div className="context-row" key={formatValue(row.scenario)}>
                <strong>{formatValue(row.scenario)} / {formatValue(row.evidence_weight)}</strong>
                <span>{formatValue(row.provider)} / {formatValue(row.source_status)}</span>
                <small>{formatValue(row.evidence_summary)} {formatValue(row.data_gap)}</small>
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className="analysis-grid two-col">
        <section className="analysis-section" aria-labelledby="pressure-title">
          <div className="section-heading">
            <h3 id="pressure-title">Liquidity Pressure Proxy</h3>
            <span>{pressure.length} rows</span>
          </div>
          <div className="heat-grid compact">
            {pressure.map((row) => (
              <div className="heat-cell" key={formatValue(row.band ?? row.level)}>
                <strong>{formatValue(row.band ?? row.level)}</strong>
                <span>{formatValue(row.side)}</span>
                <div className="heat-meter"><i style={{ width: `${Math.max(4, Math.min(100, numericValue(row.pressure_score) ?? 0))}%` }} /></div>
                <small>{formatValue(row.source_status)} / {formatValue(row.data_gap || row.caveat)}</small>
              </div>
            ))}
          </div>
        </section>
        <section className="analysis-section" aria-labelledby="crypto-providers-title">
          <div className="section-heading">
            <h3 id="crypto-providers-title">Provider Gate</h3>
            <span>{providerRows.length} rows</span>
          </div>
          <div className="context-stack">
            {providerRows.slice(0, 8).map((row, index) => (
              <StatusRow key={`crypto-provider-${index}`} row={row} />
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function ChartSpecGrid({ chartSpecs, forceFallback = false }: { chartSpecs: Record<string, unknown>[]; forceFallback?: boolean }) {
  if (chartSpecs.length === 0) {
    return (
      <div className="empty-state" role="status">
        <strong>No chart specs in this payload.</strong>
        <span>Chart surfaces require JSON-safe chart_specs rows.</span>
      </div>
    );
  }

  return (
    <section className="chart-grid" aria-label="Chart specifications">
      {chartSpecs.map((chart) => (
        <article className="chart-card" key={formatValue(chart.chart_id)}>
          <div className="section-heading">
            <h3>{formatValue(chart.title)}</h3>
            <span>{formatValue(chart.chart_type)} / {formatValue(chart.source_status)}</span>
          </div>
          <FinanceChart chart={forceFallback ? { ...chart, series: [], data_gap: "chart-renderer-diagnostic-fallback" } : chart} />
          <details className="native-chart-fallback">
            <summary>Native SVG fallback</summary>
            <NativeChart chart={chart} />
          </details>
          <div className="chart-meta">
            <span>{formatValue(chart.provider)}</span>
            <span>{formatValue(chart.fetched_at)}</span>
          </div>
          <p>{formatValue(chart.caveat)} {formatValue(chart.data_gap)}</p>
        </article>
      ))}
    </section>
  );
}

function NativeChart({ chart }: { chart: Record<string, unknown> }) {
  const series = asRecordArray(chart.series);
  const seriesWithPoints: Array<Record<string, unknown> & { points: Record<string, unknown>[] }> = series
    .map((item) => ({ ...item, points: asRecordArray(item.points) }))
    .filter((item) => item.points.length > 0);
  const allPoints = seriesWithPoints.flatMap((item) => item.points);
  const yValues = allPoints.map((point) => numericValue(point.y)).filter((value): value is number => value !== null);
  if (allPoints.length === 0 || yValues.length === 0) {
    return <div className="chart-empty">No plottable points</div>;
  }

  const chartType = String(chart.chart_type ?? "line").toLowerCase();
  const palette = ["#2dd4bf", "#f4b740", "#86efac", "#fb7185", "#93c5fd"];
  const width = 440;
  const height = 220;
  const margin = { top: 18, right: 18, bottom: 34, left: 52 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const globalDomain = paddedDomain(yValues);
  const independentSeriesScale = chartType.includes("multi") && seriesWithPoints.length > 1;
  const xCount = Math.max(...seriesWithPoints.map((item) => item.points.length), 1);
  const xAt = (index: number, count = xCount) => margin.left + (count <= 1 ? plotWidth / 2 : (index / (count - 1)) * plotWidth);
  const yAt = (value: number, domain = globalDomain) => margin.top + (1 - (value - domain.min) / domain.span) * plotHeight;
  const zeroY = yAt(Math.max(globalDomain.min, Math.min(0, globalDomain.max)));
  const firstLabel = formatValue(seriesWithPoints[0]?.points[0]?.x);
  const lastPoints = seriesWithPoints[0]?.points ?? [];
  const lastLabel = formatValue(lastPoints[lastPoints.length - 1]?.x);

  if (chartType.includes("bar") || chartType.includes("heat")) {
    const points = seriesWithPoints[0]?.points ?? [];
    const slot = plotWidth / Math.max(points.length, 1);
    const barWidth = Math.max(4, Math.min(24, slot * 0.62));
    return (
      <svg className="native-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={formatValue(chart.title)} preserveAspectRatio="none">
        <ChartAxes width={width} height={height} margin={margin} minY={globalDomain.min} maxY={globalDomain.max} firstLabel={firstLabel} lastLabel={lastLabel} zeroY={zeroY} />
        {points.map((point, index) => {
          const value = numericValue(point.y) ?? 0;
          const x = xAt(index, points.length) - barWidth / 2;
          const y = Math.min(yAt(value), zeroY);
          const barHeight = Math.max(2, Math.abs(zeroY - yAt(value)));
          return <rect key={`${formatValue(point.x)}-${index}`} x={x} y={y} width={barWidth} height={barHeight} rx="2" />;
        })}
      </svg>
    );
  }

  return (
    <svg className="native-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={formatValue(chart.title)} preserveAspectRatio="none">
      <ChartAxes width={width} height={height} margin={margin} minY={globalDomain.min} maxY={globalDomain.max} firstLabel={firstLabel} lastLabel={lastLabel} zeroY={zeroY} normalized={independentSeriesScale} />
      {seriesWithPoints.map((item, index) => {
        const values = item.points.map((point) => numericValue(point.y)).filter((value): value is number => value !== null);
        const domain = independentSeriesScale ? paddedDomain(values) : globalDomain;
        const path = item.points
          .map((point, pointIndex) => {
            const value = numericValue(point.y) ?? domain.min;
            return `${xAt(pointIndex, item.points.length)},${yAt(value, domain)}`;
          })
          .join(" ");
        const last = item.points[item.points.length - 1];
        const lastValue = numericValue(last?.y);
        return (
          <g key={formatValue(item.name ?? index)}>
            <polyline points={path} stroke={palette[index % palette.length]} />
            {lastValue !== null ? (
              <text className="chart-series-label" x={width - margin.right - 4} y={yAt(lastValue, domain) - 4} textAnchor="end">
                {formatValue(item.name ?? `s${index + 1}`)}
              </text>
            ) : null}
          </g>
        );
      })}
    </svg>
  );
}

function ChartAxes({
  width,
  height,
  margin,
  minY,
  maxY,
  firstLabel,
  lastLabel,
  zeroY,
  normalized = false,
}: {
  width: number;
  height: number;
  margin: { top: number; right: number; bottom: number; left: number };
  minY: number;
  maxY: number;
  firstLabel: string;
  lastLabel: string;
  zeroY: number;
  normalized?: boolean;
}) {
  const plotRight = width - margin.right;
  const plotBottom = height - margin.bottom;
  const midY = margin.top + (plotBottom - margin.top) / 2;
  return (
    <g className="chart-axes">
      {[margin.top, midY, plotBottom].map((y) => (
        <line key={`grid-${y}`} className="chart-gridline" x1={margin.left} y1={y} x2={plotRight} y2={y} />
      ))}
      <line className="chart-axis" x1={margin.left} y1={margin.top} x2={margin.left} y2={plotBottom} />
      <line className="chart-axis" x1={margin.left} y1={plotBottom} x2={plotRight} y2={plotBottom} />
      <line className="chart-zero" x1={margin.left} y1={zeroY} x2={plotRight} y2={zeroY} />
      <text className="chart-axis-label" x={margin.left - 8} y={margin.top + 4} textAnchor="end">{normalized ? "norm" : shortNumber(maxY)}</text>
      <text className="chart-axis-label" x={margin.left - 8} y={plotBottom} textAnchor="end">{normalized ? "series" : shortNumber(minY)}</text>
      <text className="chart-axis-label" x={margin.left} y={height - 10} textAnchor="start">{shortDateLabel(firstLabel)}</text>
      <text className="chart-axis-label" x={plotRight} y={height - 10} textAnchor="end">{shortDateLabel(lastLabel)}</text>
    </g>
  );
}

function paddedDomain(values: number[]): { min: number; max: number; span: number } {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const rawSpan = max - min;
  const pad = rawSpan === 0 ? Math.max(Math.abs(max) * 0.08, 1) : rawSpan * 0.08;
  const paddedMin = min - pad;
  const paddedMax = max + pad;
  return { min: paddedMin, max: paddedMax, span: paddedMax - paddedMin || 1 };
}
function EventGraphWorkspace({ envelope }: { envelope: ContractEnvelope }) {
  const data = isRecord(envelope.data) ? envelope.data : {};
  const nodes = asRecordArray(data.nodes);
  const edges = asRecordArray(data.edges);
  const commands = asRecordArray(data.command_suggestions);
  const evidenceRefs = asRecordArray(data.evidence_refs);
  const readiness = isRecord(data.readiness) ? data.readiness : {};
  const graphPersistence = isRecord(readiness.graph_persistence) ? readiness.graph_persistence : {};
  const liveStore = isRecord(readiness.live_store) ? readiness.live_store : {};
  const eventNodes = nodes.filter((node) => node.type === "event");
  const inferredEdges = edges.filter((edge) => edge.source_status === "inferred/proxy");
  const sourceBackedEdges = edges.filter((edge) => edge.source_status !== "inferred/proxy");
  const relationshipRows = edges.slice(0, 14);

  return (
    <div className="event-graph-view">
      <section className="graph-readiness" aria-labelledby="graph-readiness-title">
        <div>
          <span className="eyebrow">Persistence</span>
          <h3 id="graph-readiness-title">Live Store Status</h3>
        </div>
        <StatusPill tone="warn" label="graph" value={formatValue(graphPersistence.status ?? "unavailable")} />
        <StatusPill tone="warn" label="store" value={formatValue(liveStore.status ?? "unavailable")} />
        <p>{formatValue(graphPersistence.caveat ?? liveStore.caveat)}</p>
      </section>

      <div className="graph-lanes" aria-label="Graph relationship summary">
        <div className="graph-lane">
          <span>Events</span>
          <strong>{eventNodes.length}</strong>
          <small>source rows</small>
        </div>
        <div className="graph-lane">
          <span>Edges</span>
          <strong>{edges.length}</strong>
          <small>{inferredEdges.length} inferred</small>
        </div>
        <div className="graph-lane">
          <span>Commands</span>
          <strong>{commands.length}</strong>
          <small>route suggestions</small>
        </div>
        <div className="graph-lane">
          <span>Evidence</span>
          <strong>{evidenceRefs.length}</strong>
          <small>audit refs</small>
        </div>
      </div>

      <section className="graph-section" aria-labelledby="graph-relationships-title">
        <div className="section-heading">
          <h3 id="graph-relationships-title">Relationship Matrix</h3>
          <span>{sourceBackedEdges.length} source/status edges, {inferredEdges.length} inferred/proxy edges</span>
        </div>
        <div className="table-wrap graph-table">
          <table>
            <caption>Event-to-asset graph relationships</caption>
            <thead>
              <tr>
                {["relationship", "source", "target", "confidence", "source_status", "evidence", "caveat"].map((column) => (
                  <th key={column} scope="col">
                    {labelize(column)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {relationshipRows.map((edge) => (
                <tr key={formatValue(edge.id)}>
                  <td>{formatValue(edge.relationship)}</td>
                  <td>{formatValue(edge.source)}</td>
                  <td>{formatValue(edge.target)}</td>
                  <td>{formatValue(edge.confidence)}</td>
                  <td>{formatValue(edge.source_status)}</td>
                  <td>{formatValue(edge.evidence)}</td>
                  <td>{formatValue(edge.caveat)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="graph-split">
        <section className="graph-section" aria-labelledby="graph-nodes-title">
          <div className="section-heading">
            <h3 id="graph-nodes-title">Node Tape</h3>
            <span>{nodes.length} nodes</span>
          </div>
          <div className="node-tape">
            {nodes.slice(0, 18).map((node) => (
              <div className="node-row" key={formatValue(node.id)}>
                <strong>{formatValue(node.label)}</strong>
                <span>{formatValue(node.type)} / {formatValue(node.source_status)} / {formatValue(node.confidence)}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="graph-section" aria-labelledby="graph-commands-title">
          <div className="section-heading">
            <h3 id="graph-commands-title">Command Suggestions</h3>
            <span>clean-room routes</span>
          </div>
          <div className="command-stack">
            {commands.length ? (
              commands.map((command) => (
                <div className="command-row" key={formatValue(command.target_node_id ?? command.command)}>
                  <code>{formatValue(command.command)}</code>
                  <div>
                    <strong>{formatValue(command.label)}</strong>
                    <span>{formatValue(command.implementation_status)} / confidence {formatValue(command.confidence)}</span>
                    <small>{formatValue(command.caveat)}</small>
                  </div>
                </div>
              ))
            ) : (
              <p>No command suggestions in this graph.</p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function CommandLaunchpad({ runtimeMode }: { runtimeMode: RuntimeMode }) {
  const analysisMode = runtimeMode === "fixture" ? "fixture" : "live-if-available";
  const cards: { command: string; title: string; detail: string; href: string; status: string }[] = [
    { command: "NI", title: "News Intelligence", detail: "Source-backed headlines, severity and provenance", href: `/?view=news&mode=${analysisMode}`, status: "source-backed" },
    { command: "MAP", title: "Risk Map", detail: "WorldMonitor-style markers, layers and source gaps", href: `/?view=war-room-map&mode=${analysisMode}`, status: "map-ready" },
    { command: "DES", title: "Security Desk", detail: "Open the bounded AAPL symbol workstation", href: canonicalAssetHref("AAPL", "equity", "1D", analysisMode), status: "workstation" },
    { command: "FA", title: "Fundamentals", detail: "Financial statement and ratio surface when provider-backed", href: canonicalAssetHref("AAPL", "equity", "1D", analysisMode, "financials"), status: "provider-gated" },
    { command: "GP", title: "Price Chart", detail: "TradingView-style local chart route without broker execution", href: canonicalAssetHref("AAPL", "equity", "1D", analysisMode, "chart"), status: "chart-ready" },
    { command: "OMON", title: "Options Monitor", detail: "Chain, IV and Greeks boundary for equity options", href: `/?view=options-quant&symbol=AAPL&mode=${analysisMode}&surface=overview`, status: "provider-gated" },
    { command: "CRYPTO", title: "Crypto Desk", detail: "BTCUSDT funding, basis and market pressure route", href: canonicalAssetHref("BTCUSDT", "crypto", "1D", analysisMode), status: "source-backed" },
    { command: "WEI", title: "Portfolio Risk", detail: "Weights, drawdown, stress and source boundary", href: `/?view=portfolio-risk&portfolio=demo-core&surface=overview&period=1y&benchmark=SPY&mode=${analysisMode}`, status: "demo-ready" },
  ];

  return (
    <section className="command-launchpad" aria-labelledby="command-launchpad-title" data-phase5s-surface="command-launchpad">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Bloomberg-like command routing</span>
          <h3 id="command-launchpad-title">Launch a research workflow</h3>
        </div>
        <span>read-only / no broker execution</span>
      </div>
      <div className="command-launch-grid">
        {cards.map((card) => (
          <Link className="terminal-command-card" href={card.href} key={card.command}>
            <code>{card.command}</code>
            <strong>{card.title}</strong>
            <span>{card.detail}</span>
            <small>{card.status}</small>
          </Link>
        ))}
      </div>
    </section>
  );
}

function CommandWorkspaceView({ envelope }: { envelope: ContractEnvelope }) {
  const data = isRecord(envelope.data) ? envelope.data : {};
  const commands = asRecordArray(data.commands);
  const contexts = asRecordArray(data.contexts);
  const results = asRecordArray(data.command_results);
  const requirements = asRecordArray(data.provider_requirements);
  const evidenceRefs = asRecordArray(data.evidence_refs);
  const readiness = isRecord(data.readiness) ? data.readiness : {};
  const unavailableCapabilities = asRecordArray(readiness.unavailable_capabilities);
  const availableCount = results.filter((result) => result.available === true).length;
  const blockedCount = results.length - availableCount;
  const phase2Contexts = contexts.filter((context) => context.source === "phase2f_event_asset_graph");

  return (
    <div className="command-workspace-view">
      <section className="command-desk" aria-labelledby="command-desk-title">
        <div>
          <span className="eyebrow">Terminal Actions</span>
          <h3 id="command-desk-title">Command Tape</h3>
        </div>
        <div className="command-input-line" aria-label="Supported clean-room commands">
          <span>CMD</span>
          <code>{commands.map((command) => formatValue(command.command)).join(" / ")}</code>
        </div>
        <div className="command-desk-status" aria-label="Command status counts">
          <StatusPill tone={availableCount ? "ok" : "warn"} label="available" value={String(availableCount)} />
          <StatusPill tone="warn" label="gated" value={String(blockedCount)} />
          <StatusPill tone="neutral" label="evidence" value={String(evidenceRefs.length)} />
        </div>
      </section>

      <div className="command-grid">
        <section className="command-section" aria-labelledby="command-context-title">
          <div className="section-heading">
            <h3 id="command-context-title">Active Context</h3>
            <span>{phase2Contexts.length} graph-seeded rows</span>
          </div>
          <div className="context-stack">
            {phase2Contexts.slice(0, 12).map((context) => (
              <div className="context-row" key={formatValue(context.context_id)}>
                <strong>{formatValue(context.command || context.label || context.context_type)}</strong>
                <span>{formatValue(context.context_type)} / {formatValue(context.source_status)} / {formatValue(context.provider)}</span>
                <small>{formatValue(context.caveat || context.data_gap)}</small>
              </div>
            ))}
          </div>
        </section>

        <section className="command-section" aria-labelledby="command-readiness-title">
          <div className="section-heading">
            <h3 id="command-readiness-title">Action Boundary</h3>
            <span>{unavailableCapabilities.length} unavailable</span>
          </div>
          <div className="boundary-list">
            {unavailableCapabilities.map((capability) => (
              <div className="boundary-row" key={formatValue(capability.capability)}>
                <strong>{formatValue(capability.capability)}</strong>
                <span>{formatValue(capability.status)} / {formatValue(capability.provider)}</span>
                <small>{formatValue(capability.caveat)}</small>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="command-section" aria-labelledby="provider-gate-title">
        <div className="section-heading">
          <h3 id="provider-gate-title">Provider Gate</h3>
          <span>fresh or cached required for live command results</span>
        </div>
        <div className="table-wrap command-table">
          <table>
            <caption>Command provider requirements</caption>
            <thead>
              <tr>
                {["command", "provider_family", "provider", "status", "requires_provider", "available_for_live_result", "recommended_action"].map((column) => (
                  <th key={column} scope="col">
                    {labelize(column)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {requirements.map((row) => (
                <tr key={formatValue(row.command)}>
                  <td>{formatValue(row.command)}</td>
                  <td>{formatValue(row.provider_family)}</td>
                  <td>{formatValue(row.provider)}</td>
                  <td>{formatValue(row.status)}</td>
                  <td>{formatValue(row.requires_provider)}</td>
                  <td>{formatValue(row.available_for_live_result)}</td>
                  <td>{formatValue(row.recommended_action)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="command-section" aria-labelledby="command-results-title">
        <div className="section-heading">
          <h3 id="command-results-title">Result Previews</h3>
          <span>{results.length} command envelopes</span>
        </div>
        <div className="command-result-grid">
          {results.map((result) => {
            const preview = isRecord(result.preview) ? result.preview : {};
            const action = isRecord(result.action_contract) ? result.action_contract : {};
            return (
              <article className={`command-result-card${result.available === true ? " available" : ""}`} key={formatValue(result.command)}>
                <div className="result-card-top">
                  <code>{formatValue(result.command)}</code>
                  <span>{formatValue(result.result_status)}</span>
                </div>
                <strong>{formatValue(result.label)}</strong>
                <p>{formatValue(preview.message)}</p>
                <small>{formatValue(result.provider)} / {formatValue(result.source_status)} / enabled {formatValue(action.enabled)}</small>
                <small>{formatValue(result.data_gap || preview.data_gap)}</small>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}

function MarketMapProduct({ fixture, runtimeMode, apiBaseUrl }: { fixture: LoadedFixture; runtimeMode: RuntimeMode; apiBaseUrl: string | null }) {
  if (!fixture.envelope) {
    return <ProductLoadError fixture={fixture} />;
  }
  const data = isRecord(fixture.envelope.data) ? fixture.envelope.data : {};
  const instruments = asRecordArray(data.instruments);
  const ranked = asRecordArray(data.ranked_rows);
  const sectors = asRecordArray(data.sector_summaries);
  const universe = isRecord(data.universe_contract) ? data.universe_contract : {};
  const summary = isRecord(data.summary) ? data.summary : {};
  const sourceBacked = instruments.filter((row) => ["live/fresh", "cached", "stale"].includes(String(row.source_status))).length;

  return (
    <section className="market-map-product" aria-labelledby="market-map-product-title">
      <header className="market-map-product-header">
        <div>
          <span className="eyebrow">Market discovery</span>
          <h2 id="market-map-product-title">Scan listed-market breadth without losing source truth</h2>
          <p>Choose hierarchy, size and color independently. Listing identity, delayed observations, local taxonomy and rank eligibility remain separate evidence layers.</p>
        </div>
        <div className="market-map-product-stats">
          <StatusPill tone={sourceBacked ? "ok" : "warn"} label="observed" value={String(sourceBacked)} />
          <StatusPill tone={Number(universe.official_listing_coverage_count) ? "ok" : "warn"} label="official listed" value={formatValue(universe.official_listing_coverage_count || 0)} />
          <StatusPill tone="neutral" label="taxonomy" value={formatValue(universe.taxonomy_coverage_count ?? sectors.length)} />
          <StatusPill tone="neutral" label="ranked" value={String(ranked.length || Number(summary.ranked_count || 0))} />
        </div>
      </header>
      <RuntimeModeBanner mode={runtimeMode} definition={fixture.definition} envelope={fixture.envelope} runtime={fixture.runtime} />
      <MarketMapScreener envelope={fixture.envelope} runtimeMode={runtimeMode} apiBaseUrl={apiBaseUrl} />
    </section>
  );
}

function OptionsQuantProduct({ fixture, runtimeMode }: { fixture: LoadedFixture; runtimeMode: RuntimeMode }) {
  if (!fixture.envelope) {
    return <ProductLoadError fixture={fixture} />;
  }
  return (
    <section className="product-main-panel options-product-panel" aria-label="Options quant product">
      <RuntimeModeBanner mode={runtimeMode} definition={fixture.definition} envelope={fixture.envelope} runtime={fixture.runtime} />
      <RuntimeFallbackNotice fixture={fixture} />
      <OptionsQuantWorkstation envelope={fixture.envelope} runtimeMode={runtimeMode} />
    </section>
  );
}

function NewsIntelligenceProduct({
  fixture,
  runtimeMode,
  severityFilter,
  sourceStatusFilter,
  regionFilter,
  topicFilter,
  returnHref,
}: {
  fixture: LoadedFixture;
  runtimeMode: RuntimeMode;
  severityFilter: string;
  sourceStatusFilter: string;
  regionFilter: string;
  topicFilter: string;
  returnHref: string | null;
}) {
  if (!fixture.envelope) {
    return <ProductLoadError fixture={fixture} />;
  }

  const envelope = fixture.envelope;
  const data = isRecord(envelope.data) ? envelope.data : {};
  const allRows = uniqueNewsRows([
    ...asRecordArray(data.high_severity_feed),
    ...asRecordArray(data.event_rows),
    ...asRecordArray(data.normalized_news),
  ]);
  const sourceRows = asRecordArray(data.source_freshness).length ? asRecordArray(data.source_freshness) : envelope.source_status;
  const impactRows = asRecordArray(data.impact_matrix);
  const regionalRows = asRecordArray(data.regional_cards);
  const timelineRows = asRecordArray(data.timeline);
  const clusters = buildNewsClusters(allRows);
  const filteredRows = allRows.filter((row) => {
    const severity = formatValue(row.severity || "watch").toLowerCase();
    const status = formatValue(row.source_status || row.freshness || "unknown").toLowerCase();
    const region = formatValue(row.region || row.location || "global").toLowerCase();
    const topics = newsTopics(row).map((item) => item.toLowerCase());
    return (severityFilter === "all" || severity === severityFilter)
      && (sourceStatusFilter === "all" || status === sourceStatusFilter)
      && (regionFilter === "all" || region === regionFilter)
      && (topicFilter === "all" || topics.includes(topicFilter));
  });
  const selectedRow = filteredRows[0] || allRows[0];
  const sourceBacked = allRows.filter((row) => ["fresh", "live/fresh", "cached", "stale"].includes(formatValue(row.source_status || row.freshness).toLowerCase())).length;
  const fixtureRows = allRows.filter((row) => formatValue(row.source_status || row.freshness) === "fixture").length;
  const severityOptions = ["all", ...uniqueStrings(allRows.map((row) => formatValue(row.severity || "watch").toLowerCase()))];
  const statusOptions = ["all", ...uniqueStrings(allRows.map((row) => formatValue(row.source_status || row.freshness || "unknown").toLowerCase()))];
  const regionOptions = ["all", ...uniqueStrings(allRows.map((row) => formatValue(row.region || row.location || "global").toLowerCase()))];
  const topicOptions = ["all", ...uniqueStrings(allRows.flatMap((row) => newsTopics(row).map((item) => item.toLowerCase())))];

  return (
    <section className="product-main-panel news-product-workspace" aria-labelledby="news-product-title">
      {returnHref ? <div className="attention-return-bar"><Link prefetch={false} href={returnHref}>{returnWorkspaceLabel(returnHref)}</Link><span>Review filters and queue state preserved</span></div> : null}
      <RuntimeModeBanner mode={runtimeMode} definition={fixture.definition} envelope={envelope} runtime={fixture.runtime} />
      <RuntimeFallbackNotice fixture={fixture} />

      <header className="news-product-header">
        <div>
          <span className="eyebrow">News intelligence / source desk</span>
          <h2 id="news-product-title">Source-Backed News Workspace</h2>
          <p>Cluster public-feed rows by region, severity, topic and source state, then route map-linked items into the War Map context.</p>
        </div>
        <div className="news-status-strip">
          <StatusPill tone={sourceBacked ? "ok" : "warn"} label="source-backed" value={String(sourceBacked)} />
          <StatusPill tone={fixtureRows ? "warn" : "neutral"} label="fixture" value={String(fixtureRows)} />
          <StatusPill tone={envelope.unavailable.length ? "danger" : "ok"} label="gaps" value={String(envelope.unavailable.length)} />
          <StatusPill tone="neutral" label="sources" value={String(sourceRows.length)} />
        </div>
      </header>

      <nav className="news-filter-bar" aria-label="News filters">
        <FilterGroup label="Severity" param="severity" active={severityFilter} options={severityOptions} runtimeMode={runtimeMode} />
        <FilterGroup label="Source" param="sourceStatus" active={sourceStatusFilter} options={statusOptions} runtimeMode={runtimeMode} />
        <FilterGroup label="Region" param="region" active={regionFilter} options={regionOptions} runtimeMode={runtimeMode} />
        <FilterGroup label="Topic" param="topic" active={topicFilter} options={topicOptions} runtimeMode={runtimeMode} />
      </nav>

      {!allRows.length ? (
        <div className="news-empty-state" role="status">
          <strong>No verified news rows are available.</strong>
          <span>No fake live headlines are substituted; inspect provider/source freshness rows for the gap.</span>
        </div>
      ) : (
        <div className="news-product-layout">
          <section className="news-main-stack" aria-labelledby="news-clusters-title">
            <div className="section-heading">
              <div><span className="eyebrow">Cluster board</span><h3 id="news-clusters-title">Story / Event Clusters</h3></div>
              <span>{filteredRows.length} visible / {allRows.length} total</span>
            </div>
            <div className="news-cluster-grid">
              {clusters.slice(0, 8).map((cluster) => (
                <article className="news-cluster-card" key={cluster.key}>
                  <div><strong>{cluster.region}</strong><span>{cluster.topic}</span></div>
                  <b>{cluster.count} rows</b>
                  <small>{cluster.severity} / {cluster.sourceStatus}</small>
                </article>
              ))}
            </div>

            <div className="news-row-stack" data-news-visible-rows={filteredRows.length}>
              {filteredRows.slice(0, 18).map((row, index) => (
                <article className="news-workspace-row" key={`${formatValue(row.title)}-${index}`}>
                  <div className="news-row-topline">
                    <StatusPill tone={statusTone(row.source_status || row.freshness)} label={formatValue(row.severity || "watch")} value={formatValue(row.source_status || row.freshness)} />
                    <span>{formatValue(row.provider || row.source)} / {formatValue(row.region || row.location || "global")}</span>
                  </div>
                  <h3>{formatValue(row.title)}</h3>
                  <p>{formatValue(row.summary || row.caveat || row.data_gap)}</p>
                  <div className="news-row-actions">
                    <Link href={newsMapHref(row, runtimeMode)}>Map context</Link>
                    <Link href={newsAssetHref(row, runtimeMode)}>Asset context</Link>
                    {safeExternalHref(row.source_url || row.url) ? <a href={safeExternalHref(row.source_url || row.url) || undefined} target="_blank" rel="noreferrer">Source</a> : <span>source url unavailable</span>}
                  </div>
                  <small>{formatValue(row.fetched_at || row.published_at)} / confidence {formatValue(row.confidence)} / {formatValue(row.data_gap || row.caveat)}</small>
                </article>
              ))}
            </div>
          </section>

          <aside className="news-source-rail" aria-label="News source and selected event">
            <section>
              <span className="eyebrow">Selected row</span>
              <h3>{formatValue(selectedRow?.title || "No selected story")}</h3>
              <dl className="detail-list">
                <div><dt>Region</dt><dd>{formatValue(selectedRow?.region || selectedRow?.location)}</dd></div>
                <div><dt>Severity</dt><dd>{formatValue(selectedRow?.severity)}</dd></div>
                <div><dt>Provider</dt><dd>{formatValue(selectedRow?.provider || selectedRow?.source)}</dd></div>
                <div><dt>Coordinates</dt><dd>{formatValue(selectedRow?.lat)} / {formatValue(selectedRow?.lon)}</dd></div>
              </dl>
            </section>

            <section>
              <span className="eyebrow">Impact matrix</span>
              <div className="news-impact-grid">
                {impactRows.slice(0, 8).map((row, index) => (
                  <div key={`impact-${index}`}><strong>{formatValue(row.impact_channel)}</strong><span>{formatValue(row.total_count)} rows / {formatValue(row.latest_title)}</span></div>
                ))}
              </div>
            </section>

            <section>
              <span className="eyebrow">Regional cards</span>
              <div className="news-mini-list">
                {regionalRows.slice(0, 8).map((row, index) => <div className="news-source-row" key={`region-${index}`}><strong>{formatValue(row.region)}</strong><span>{formatValue(row.headline_count)} / {formatValue(row.severity)}</span></div>)}
              </div>
            </section>

            <section>
              <span className="eyebrow">Source freshness</span>
              <div className="news-mini-list">
                {sourceRows.slice(0, 10).map((row, index) => <div className="news-source-row" key={`source-${index}`}><strong>{formatValue(row.provider || row.source)}</strong><span>{formatValue(row.status || row.source_status)} / {formatValue(row.coverage || row.row_count)}</span></div>)}
              </div>
            </section>

            <section>
              <span className="eyebrow">Timeline</span>
              <div className="news-mini-list">
                {timelineRows.slice(0, 8).map((row, index) => <div className="news-source-row" key={`timeline-${index}`}><strong>{formatValue(row.period)}</strong><span>{formatValue(row.total_count)} rows / watch {formatValue(row.watch_count)}</span></div>)}
              </div>
            </section>
          </aside>
        </div>
      )}
    </section>
  );
}

function PortfolioRiskProduct({ fixture, runtimeMode }: { fixture: LoadedFixture; runtimeMode: RuntimeMode }) {
  if (!fixture.envelope) {
    return <ProductLoadError fixture={fixture} />;
  }
  return (
    <section className="product-main-panel portfolio-product-panel" aria-label="Portfolio and risk product">
      <RuntimeModeBanner mode={runtimeMode} definition={fixture.definition} envelope={fixture.envelope} runtime={fixture.runtime} />
      <RuntimeFallbackNotice fixture={fixture} />
      <PortfolioRiskWorkstation envelope={fixture.envelope} runtimeMode={runtimeMode} />
    </section>
  );
}

function GlobalRiskMapProduct({ fixture, runtimeMode, replayEnvelope, apiBaseUrl, returnHref }: { fixture: LoadedFixture; runtimeMode: RuntimeMode; replayEnvelope: ContractEnvelope | null; apiBaseUrl: string | null; returnHref: string | null }) {
  if (!fixture.envelope) {
    return <ProductLoadError fixture={fixture} />;
  }

  const envelope = fixture.envelope;
  const data = isRecord(envelope.data) ? envelope.data : {};
  const markers = asRecordArray(data.markers);
  const layers = asRecordArray(data.layer_health);
  const relatedNews = asRecordArray(data.news_rows).length
    ? asRecordArray(data.news_rows)
    : asRecordArray(data.related_news);
  const connectedAssets = asRecordArray(data.connected_assets);
  const eventLinks = asRecordArray(data.event_links);
  const eventContexts = asRecordArray(data.event_contexts);
  const selectedMarkerId = typeof data.selected_marker_id === "string" ? data.selected_marker_id : "";
  const unavailableSources = asRecordArray(data.unavailable_sources);
  const readiness = isRecord(data.readiness) ? data.readiness : {};
  const sourceBackedCount = markers.filter((marker) =>
    ["live/fresh", "cached", "stale"].includes(String(marker.source_status)),
  ).length;
  const fixtureCount = markers.filter((marker) => String(marker.source_status) === "fixture").length;

  return (
    <section className="global-risk-map-product" aria-labelledby="global-risk-map-title">
      {returnHref ? <div className="attention-return-bar"><Link prefetch={false} href={returnHref}>{returnWorkspaceLabel(returnHref)}</Link><span>Selected event review state preserved</span></div> : null}
      <header className="global-map-product-header map-first-header">
        <div>
          <span className="eyebrow">Global risk operations</span>
          <h2 id="global-risk-map-title">Events, news and market exposure on one map</h2>
          <p>Select an event to inspect its source, location method, related reporting and evidence-backed asset links.</p>
        </div>
        <div className="global-map-header-stats" aria-label="Map data summary">
          <StatusPill tone={sourceBackedCount ? "ok" : "warn"} label="source-backed" value={String(sourceBackedCount)} />
          <StatusPill tone={fixtureCount ? "warn" : "neutral"} label="fixture" value={String(fixtureCount)} />
          <StatusPill tone={unavailableSources.length ? "danger" : "ok"} label="source gaps" value={String(unavailableSources.length)} />
        </div>
      </header>
      <MapRuntimeSourceStrip
        fixture={fixture}
        envelope={envelope}
        runtimeMode={runtimeMode}
        markerCount={markers.length}
        sourceBackedCount={sourceBackedCount}
        layerCount={layers.length}
        unavailableCount={unavailableSources.length}
      />
      <WarMapReplayWorkspace
        currentMarkers={markers}
        currentLayers={layers}
        currentNews={relatedNews}
        currentAssets={connectedAssets}
        currentLinks={eventLinks}
        currentEventContexts={eventContexts}
        defaultSelectedMarkerId={selectedMarkerId}
        unavailableSources={unavailableSources}
        readiness={readiness}
        replayFixture={replayEnvelope}
        apiBaseUrl={apiBaseUrl}
        runtimeMode={runtimeMode}
      />
      <div className="war-map-runtime-detail" aria-label="Full runtime boundary">
        <RuntimeModeBanner mode={runtimeMode} definition={fixture.definition} envelope={envelope} runtime={fixture.runtime} />
      </div>
    </section>
  );
}

function MapRuntimeSourceStrip({
  fixture,
  envelope,
  runtimeMode,
  markerCount,
  sourceBackedCount,
  layerCount,
  unavailableCount,
}: {
  fixture: LoadedFixture;
  envelope: ContractEnvelope;
  runtimeMode: RuntimeMode;
  markerCount: number;
  sourceBackedCount: number;
  layerCount: number;
  unavailableCount: number;
}) {
  const sourceStatus = formatValue(envelope.summary.source_status || envelope.summary.status || fixture.runtime?.source || runtimeMode);
  const webSource = formatValue(fixture.runtime?.source || fixture.definition.key);
  const liveRows = formatValue(envelope.summary.row_count || envelope.summary.live_row_count || envelope.summary.source_backed_marker_count || sourceBackedCount);
  return (
    <section className="war-map-source-strip" data-phase5u-source-strip="true" aria-label="War map source boundary">
      <div>
        <span className="eyebrow">Source boundary</span>
        <strong>{fixture.definition.label}</strong>
      </div>
      <dl>
        <div><dt>Mode</dt><dd>{runtimeMode}</dd></div>
        <div><dt>Source</dt><dd>{webSource}</dd></div>
        <div><dt>Status</dt><dd>{sourceStatus}</dd></div>
        <div><dt>Rows</dt><dd>{markerCount} events / {layerCount} layers</dd></div>
        <div><dt>Live/cache</dt><dd>{liveRows}</dd></div>
        <div><dt>Gaps</dt><dd>{unavailableCount}</dd></div>
      </dl>
    </section>
  );
}

function WarRoomMapWorkspace({ envelope }: { envelope: ContractEnvelope }) {
  const data = isRecord(envelope.data) ? envelope.data : {};
  const markers = asRecordArray(data.markers);
  const layers = asRecordArray(data.layers);
  const timelineFilters = asRecordArray(data.timeline_filters);
  const compareWindows = asRecordArray(data.compare_windows);
  const providerRequirements = asRecordArray(data.provider_requirements);
  const readiness = isRecord(data.readiness) ? data.readiness : {};
  const unavailableCapabilities = asRecordArray(readiness.unavailable_capabilities);
  const liveLayers = layers.filter((layer) => ["live/fresh", "cached"].includes(String(layer.source_status)));
  const proxyLayers = layers.filter((layer) => String(layer.source_status) === "proxy/static");
  const unavailableLayers = layers.filter((layer) => String(layer.availability) === "unavailable");

  return (
    <div className="war-map-view">
      <section className="map-command-strip" aria-labelledby="war-map-title">
        <div>
          <span className="eyebrow">Map-First War Room</span>
          <h3 id="war-map-title">Source-Backed Event Surface</h3>
        </div>
        <div className="map-command-line" aria-label="Map command context">
          <span>MAP</span>
          <code>{markers.length} markers / {layers.length} layers / compare ready</code>
        </div>
        <div className="command-desk-status" aria-label="Map source counts">
          <StatusPill tone={liveLayers.length ? "ok" : "warn"} label="live/cached layers" value={String(liveLayers.length)} />
          <StatusPill tone="warn" label="proxy/static" value={String(proxyLayers.length)} />
          <StatusPill tone="danger" label="unavailable" value={String(unavailableLayers.length)} />
        </div>
      </section>

      <LeafletWarMap markers={markers} layers={layers} timelineFilters={timelineFilters} />
      <section className="map-section" aria-labelledby="compare-title">
        <div className="section-heading">
          <h3 id="compare-title">Compare Window Readiness</h3>
          <span>{compareWindows.length} schema rows</span>
        </div>
        <div className="compare-grid">
          {compareWindows.map((window) => (
            <article className={`compare-card${window.available === false ? " unavailable" : ""}`} key={formatValue(window.window_id)}>
              <div className="result-card-top">
                <code>{formatValue(window.window_id)}</code>
                <span>{formatValue(window.status)}</span>
              </div>
              <strong>{formatValue(window.label)}</strong>
              <p>{formatValue(window.caveat)}</p>
              <small>persistence {formatValue(window.requires_persistence)} / markers {formatValue(window.marker_count)}</small>
            </article>
          ))}
        </div>
      </section>

      <section className="map-section" aria-labelledby="provider-matrix-title">
        <div className="section-heading">
          <h3 id="provider-matrix-title">Provider Gate Matrix</h3>
          <span>{providerRequirements.length} requirements</span>
        </div>
        <div className="table-wrap command-table">
          <table>
            <caption>War Room map provider requirements</caption>
            <thead>
              <tr>
                {["layer_id", "provider", "provider_status", "availability", "requires_key", "row_count", "live_claim_allowed", "recommended_action"].map((column) => (
                  <th key={column} scope="col">
                    {labelize(column)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {providerRequirements.slice(0, 18).map((row) => (
                <tr key={formatValue(row.requirement_id)}>
                  <td>{formatValue(row.layer_id)}</td>
                  <td>{formatValue(row.provider)}</td>
                  <td>{formatValue(row.provider_status)}</td>
                  <td>{formatValue(row.availability)}</td>
                  <td>{formatValue(row.requires_key)}</td>
                  <td>{formatValue(row.row_count)}</td>
                  <td>{formatValue(row.live_claim_allowed)}</td>
                  <td>{formatValue(row.recommended_action)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="map-section" aria-labelledby="map-readiness-title">
        <div className="section-heading">
          <h3 id="map-readiness-title">Unavailable Capability Boundary</h3>
          <span>{unavailableCapabilities.length} blocked</span>
        </div>
        <div className="boundary-list map-boundary">
          {unavailableCapabilities.map((capability) => (
            <div className="boundary-row" key={formatValue(capability.capability)}>
              <strong>{formatValue(capability.capability)}</strong>
              <span>{formatValue(capability.status)} / {formatValue(capability.provider)}</span>
              <small>{formatValue(capability.caveat)}</small>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function MapNewsEventFusionWorkspace({ envelope }: { envelope: ContractEnvelope }) {
  const data = isRecord(envelope.data) ? envelope.data : {};
  const markers = asRecordArray(data.markers);
  const relatedNews = asRecordArray(data.related_news);
  const eventLinks = asRecordArray(data.event_links);
  const connectedAssets = asRecordArray(data.connected_assets);
  const heatmapContext = asRecordArray(data.heatmap_context);
  const layerHealth = asRecordArray(data.layer_health);
  const providerHealth = asRecordArray(data.provider_health);
  const unavailableSources = asRecordArray(data.unavailable_sources);
  const timelineWindows = asRecordArray(data.timeline_windows);
  const sourceRegister = asRecordArray(data.source_register);
  const readiness = isRecord(data.readiness) ? data.readiness : {};
  const selectedMarker = isRecord(data.selected_marker) ? data.selected_marker : markers[0] ?? {};
  const selectedTitle = formatValue(selectedMarker.title || selectedMarker.marker_id || "Selected event");
  const liveSourceCount = Number(readiness.live_source_count ?? 0);
  const heatmapRows = heatmapContext.slice(0, 12);

  return (
    <div className="map-fusion-view" data-workspace="MapNewsEventFusionWorkspace">
      <section className="map-command-strip fusion-command-strip" aria-labelledby="map-fusion-title">
        <div>
          <span className="eyebrow">World Monitor Fusion</span>
          <h3 id="map-fusion-title">Map News Event Fusion</h3>
        </div>
        <div className="map-command-line" aria-label="Fusion command context">
          <span>MAPFUSION</span>
          <code>{markers.length} markers / {relatedNews.length} news / {eventLinks.length} graph links</code>
        </div>
        <div className="command-desk-status" aria-label="Fusion source counts">
          <StatusPill tone={liveSourceCount ? "ok" : "warn"} label="live/cache rows" value={String(liveSourceCount)} />
          <StatusPill tone="neutral" label="heatmap context" value={String(heatmapContext.length)} />
          <StatusPill tone={unavailableSources.length ? "danger" : "ok"} label="unavailable" value={String(unavailableSources.length)} />
        </div>
      </section>

      <LeafletWarMap markers={markers} layers={layerHealth} timelineFilters={timelineWindows} />

      <div className="fusion-hero-grid">
        <section className="fusion-card selected-event-card" aria-labelledby="fusion-selected-title">
          <div className="section-heading">
            <h3 id="fusion-selected-title">Selected Event</h3>
            <span>{formatValue(selectedMarker.source_status || envelope.summary.source_status)}</span>
          </div>
          <strong>{selectedTitle}</strong>
          <p>{formatValue(selectedMarker.summary || selectedMarker.caveat || selectedMarker.data_gap)}</p>
          <dl className="fusion-kv-grid">
            {[
              ["Region", selectedMarker.region],
              ["Severity", selectedMarker.severity],
              ["Provider", selectedMarker.provider],
              ["Confidence", selectedMarker.confidence],
              ["Coordinate", selectedMarker.coordinate_method || selectedMarker.coordinate_status],
              ["Fetched", selectedMarker.fetched_at],
            ].map(([label, value]) => (
              <div key={label as string}>
                <dt>{label as string}</dt>
                <dd>{formatValue(value)}</dd>
              </div>
            ))}
          </dl>
          <small>{formatValue(selectedMarker.source_url || selectedMarker.data_gap || "No source URL in fixture row")}</small>
        </section>

        <section className="fusion-card" aria-labelledby="fusion-news-title">
          <div className="section-heading">
            <h3 id="fusion-news-title">Related News</h3>
            <span>{relatedNews.length} matched rows</span>
          </div>
          <div className="fusion-news-stack">
            {relatedNews.slice(0, 6).map((news, index) => (
              <article className="fusion-news-row" key={`${formatValue(news.title)}-${index}`}>
                <strong>{formatValue(news.title)}</strong>
                <span>{formatValue(news.provider)} / {formatValue(news.region)} / {formatValue(news.source_status || news.freshness)}</span>
                <small>{formatValue(news.data_gap || news.caveat || news.source_url)}</small>
              </article>
            ))}
          </div>
        </section>
      </div>

      <section className="fusion-card map-fusion-heatmap" aria-labelledby="fusion-heatmap-title">
        <div className="section-heading">
          <h3 id="fusion-heatmap-title">Heatmap Reaction Context</h3>
          <span>{heatmapRows.length} source-labeled tiles</span>
        </div>
        <div className="fusion-heatmap-grid">
          {heatmapRows.map((tile) => {
            const change = Number(tile.daily_return_pct ?? 0);
            return (
              <article
                className={`fusion-heatmap-tile ${heatmapTone(change)}`}
                key={`${formatValue(tile.symbol)}-${formatValue(tile.sector)}`}
              >
                <strong>{formatValue(tile.symbol)}</strong>
                <b>{formatSigned(tile.daily_return_pct)}</b>
                <span>{formatValue(tile.sector)}</span>
                <small>{formatValue(tile.source_status)} / {formatValue(tile.data_gap || tile.caveat)}</small>
              </article>
            );
          })}
        </div>
      </section>

      <div className="analysis-grid two-col">
        <section className="fusion-card" aria-labelledby="fusion-event-links-title">
          <div className="section-heading">
            <h3 id="fusion-event-links-title">Event-To-Asset Links</h3>
            <span>{eventLinks.length} relationships</span>
          </div>
          <div className="fusion-link-grid">
            {eventLinks.slice(0, 12).map((link, index) => (
              <article className="fusion-link-card" key={`${formatValue(link.edge_id)}-${index}`}>
                <code>{formatValue(link.relationship)}</code>
                <strong>{formatValue(link.label)}</strong>
                <span>{formatValue(link.node_type)} / {formatValue(link.source_status)} / confidence {formatValue(link.confidence)}</span>
                <small>{formatValue(link.data_gap || link.caveat)}</small>
              </article>
            ))}
          </div>
        </section>

        <section className="fusion-card" aria-labelledby="fusion-assets-title">
          <div className="section-heading">
            <h3 id="fusion-assets-title">Connected Assets</h3>
            <span>{connectedAssets.length} nodes</span>
          </div>
          <div className="context-stack">
            {connectedAssets.slice(0, 10).map((asset, index) => (
              <div className="context-row" key={`${formatValue(asset.id)}-${index}`}>
                <strong>{formatValue(asset.label)}</strong>
                <span>{formatValue(asset.type)} / {formatValue(asset.provider)} / {formatValue(asset.source_status)}</span>
                <small>{formatValue(asset.data_gap || asset.caveat)}</small>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="fusion-card" aria-labelledby="fusion-health-title">
        <div className="section-heading">
          <h3 id="fusion-health-title">Provider And Layer Truth</h3>
          <span>{providerHealth.length} providers / {layerHealth.length} layers</span>
        </div>
        <div className="fusion-health-grid">
          {[...providerHealth.slice(0, 8), ...layerHealth.slice(0, 8)].map((row, index) => (
            <div className="boundary-row" key={`${formatValue(row.provider || row.layer_id)}-${index}`}>
              <strong>{formatValue(row.provider || row.label || row.layer_id)}</strong>
              <span>{formatValue(row.status || row.source_status || row.availability)} / rows {formatValue(row.row_count)}</span>
              <small>{formatValue(row.recommended_action || row.data_gap || row.caveat)}</small>
            </div>
          ))}
        </div>
      </section>

      <section className="fusion-card" aria-labelledby="fusion-source-title">
        <div className="section-heading">
          <h3 id="fusion-source-title">Source Register</h3>
          <span>{sourceRegister.length} provenance rows</span>
        </div>
        <div className="table-wrap command-table">
          <table>
            <caption>Map-news-event fusion source register</caption>
            <thead>
              <tr>
                {["provider", "source_status", "freshness", "confidence", "data_gap"].map((column) => (
                  <th key={column} scope="col">{labelize(column)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sourceRegister.slice(0, 14).map((row, index) => (
                <tr key={`fusion-source-${index}`}>
                  <td>{formatValue(row.provider)}</td>
                  <td>{formatValue(row.source_status)}</td>
                  <td>{formatValue(row.freshness)}</td>
                  <td>{formatValue(row.confidence)}</td>
                  <td>{formatValue(row.data_gap || row.caveat)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}


function ResearchReportWorkspace({ envelope }: { envelope: ContractEnvelope }) {
  const data = isRecord(envelope.data) ? envelope.data : {};
  const sections = asRecordArray(data.sections);
  const scenarios = asRecordArray(data.scenario_matrix);
  const sources = asRecordArray(data.source_register);
  const policy = isRecord(data.policy) ? data.policy : {};
  const styleReference = isRecord(data.style_reference) ? data.style_reference : {};
  const detected = Array.isArray(policy.forbidden_language_detected) ? policy.forbidden_language_detected : [];

  return (
    <div className="research-report-view">
      <section className="terminal-desk" aria-labelledby="research-report-title">
        <div>
          <span className="eyebrow">Source-Bound Report</span>
          <h3 id="research-report-title">{formatValue(data.report_title)}</h3>
        </div>
        <div className="command-input-line">
          <span>REPORT</span>
          <code>{sections.length} sections / {scenarios.length} scenarios / {sources.length} sources</code>
        </div>
        <div className="command-desk-status">
          <StatusPill tone={detected.length ? "danger" : "ok"} label="advice language" value={detected.length ? "blocked" : "clean"} />
          <StatusPill tone="neutral" label="mode" value={formatValue(styleReference.adoption_mode)} />
          <StatusPill tone="warn" label="source" value={formatValue(envelope.summary.source_status ?? "mixed")} />
        </div>
      </section>

      <section className="analysis-section" aria-labelledby="report-sections-title">
        <div className="section-heading">
          <h3 id="report-sections-title">Research Sections</h3>
          <span>non-advisory structure</span>
        </div>
        <div className="report-section-stack">
          {sections.map((section) => {
            const evidenceRows = asRecordArray(section.evidence_rows);
            const bullets = Array.isArray(section.summary_bullets) ? section.summary_bullets : [];
            return (
              <article className="report-section-card" key={formatValue(section.section_id)}>
                <div className="result-card-top">
                  <code>{formatValue(section.section_id)}</code>
                  <span>{formatValue(section.source_status)}</span>
                </div>
                <h4>{formatValue(section.title)}</h4>
                <ul>
                  {bullets.slice(0, 4).map((bullet, index) => (
                    <li key={`${formatValue(section.section_id)}-${index}`}>{formatValue(bullet)}</li>
                  ))}
                </ul>
                <div className="evidence-mini-grid">
                  {evidenceRows.slice(0, 3).map((row, index) => (
                    <div className="context-row" key={`${formatValue(section.section_id)}-evidence-${index}`}>
                      <strong>{formatValue(row.label)}</strong>
                      <span>{formatValue(row.provider)} / {formatValue(row.source_status)} / confidence {formatValue(row.confidence)}</span>
                      <small>{formatValue(row.data_gap || row.caveat)}</small>
                    </div>
                  ))}
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <div className="analysis-grid two-col">
        <section className="analysis-section" aria-labelledby="scenario-matrix-title">
          <div className="section-heading">
            <h3 id="scenario-matrix-title">Scenario Matrix</h3>
            <span>{scenarios.length} rows</span>
          </div>
          <div className="context-stack">
            {scenarios.map((scenario) => (
              <div className="context-row" key={formatValue(scenario.scenario)}>
                <strong>{formatValue(scenario.scenario)}</strong>
                <span>weight {formatValue(scenario.evidence_weight)} / {formatValue(scenario.source_status)}</span>
                <small>{formatValue(scenario.research_condition || scenario.invalidating_evidence)}</small>
              </div>
            ))}
          </div>
        </section>

        <section className="analysis-section" aria-labelledby="report-policy-title">
          <div className="section-heading">
            <h3 id="report-policy-title">Policy Boundary</h3>
            <span>{formatValue(styleReference.source)}</span>
          </div>
          <div className="boundary-list">
            <div className="boundary-row">
              <strong>Non-Advisory</strong>
              <span>{formatValue(policy.non_advisory)}</span>
              <small>{formatValue(styleReference.caveat)}</small>
            </div>
            <div className="boundary-row">
              <strong>Account Action</strong>
              <span>{formatValue(policy.account_action_enabled)}</span>
              <small>Report output stays research-only.</small>
            </div>
            <div className="boundary-row">
              <strong>Detected Forbidden Language</strong>
              <span>{detected.length ? detected.map(formatValue).join(", ") : "none"}</span>
              <small>Trade and leverage phrasing is rewritten before display.</small>
            </div>
          </div>
        </section>
      </div>

      <section className="analysis-section" aria-labelledby="source-register-title">
        <div className="section-heading">
          <h3 id="source-register-title">Source Register</h3>
          <span>{sources.length} rows</span>
        </div>
        <div className="table-wrap command-table">
          <table>
            <caption>Research report source register</caption>
            <thead>
              <tr>
                {["provider", "source", "source_status", "freshness", "confidence", "data_gap"].map((column) => (
                  <th key={column} scope="col">{labelize(column)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sources.slice(0, 16).map((row, index) => (
                <tr key={`source-register-${index}`}>
                  <td>{formatValue(row.provider)}</td>
                  <td>{formatValue(row.source)}</td>
                  <td>{formatValue(row.source_status)}</td>
                  <td>{formatValue(row.freshness)}</td>
                  <td>{formatValue(row.confidence)}</td>
                  <td>{formatValue(row.data_gap)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function DataPreview({
  definition,
  rows,
  envelope,
}: {
  definition: FixtureDefinition;
  rows: Record<string, unknown>[];
  envelope: ContractEnvelope;
}) {
  const columns = TABLE_COLUMNS[definition.key];

  if (rows.length === 0) {
    return (
      <div className="empty-state" role="status">
        <strong>No row collection in this payload.</strong>
        <span>{formatValue(envelope.data)}</span>
      </div>
    );
  }

  return (
    <div className="table-wrap">
      <table>
        <caption>{definition.shortLabel} fixture rows</caption>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column} scope="col">
                {labelize(column)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 10).map((row, index) => (
            <tr key={`${definition.key}-${index}`}>
              {columns.map((column) => (
                <td key={column}>{formatValue(row[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > 10 ? <p className="table-note">Showing 10 of {rows.length} rows.</p> : null}
    </div>
  );
}

function IntelligenceRail({ fixture, runtimeMode }: { fixture: LoadedFixture; runtimeMode: RuntimeMode }) {
  const envelope = fixture.envelope;

  return (
    <aside className="intel-rail" aria-label="Caveats and source status">
      <RailSection title={`Runtime: ${runtimeMode}`}>
        <p>{runtimeMode === "fixture" ? "Static fixture mode is deterministic and network-free. Rows must not be interpreted as live market data." : runtimeMode === "cache" ? "Cache mode uses the configured local API (default 127.0.0.1:8000) and displays an explicit fixture fallback if it is unreachable." : "Live-if-available mode calls the local API with include_runtime=true. Failed providers must remain cached, stale, unavailable, error-labeled, or fixture-fallback."}</p>
        {fixture.runtime?.requestedUrl ? <p>Runtime URL: {fixture.runtime.requestedUrl}</p> : null}
      </RailSection>
      <RailSection title="Caveats">
        {envelope?.caveats.length ? (
          envelope.caveats.map((caveat) => <p key={caveat}>{caveat}</p>)
        ) : (
          <p>No caveats in this envelope.</p>
        )}
      </RailSection>
      <RailSection title="Unavailable">
        {envelope?.unavailable.length ? (
          envelope.unavailable.slice(0, 6).map((row, index) => (
            <StatusRow key={`unavailable-${index}`} row={row} />
          ))
        ) : (
          <p>No unavailable rows.</p>
        )}
      </RailSection>
      <RailSection title="Errors">
        {fixture.issues.length ? fixture.issues.map((issue) => <p key={issue}>{issue}</p>) : null}
        {envelope?.errors.length ? (
          envelope.errors.slice(0, 4).map((row, index) => <StatusRow key={`error-${index}`} row={row} />)
        ) : !fixture.issues.length ? (
          <p>No errors in this envelope.</p>
        ) : null}
      </RailSection>
      <RailSection title="Source Status">
        {envelope?.source_status.length ? (
          envelope.source_status.slice(0, 5).map((row, index) => <StatusRow key={`source-${index}`} row={row} />)
        ) : (
          <p>No source-status rows.</p>
        )}
      </RailSection>
    </aside>
  );
}

function ProviderStrip({
  fixtures,
  statusCounts,
  runtimeMode,
}: {
  fixtures: LoadedFixture[];
  statusCounts: Record<string, number>;
  runtimeMode: RuntimeMode;
}) {
  const unavailable = fixtures.reduce((count, fixture) => count + (fixture.envelope?.unavailable.length ?? 0), 0);
  const errors = fixtures.reduce((count, fixture) => count + (fixture.envelope?.errors.length ?? 0) + fixture.issues.length, 0);

  return (
    <footer className="provider-strip" aria-label="Provider freshness strip">
      <span>Runtime mode: {runtimeMode}</span>
      <span>Fixture source: static/api-fixtures</span>
      <span>Runtime API: 127.0.0.1:8000 default / environment override supported</span>
      <span>OpenSky: missing-key unless OAuth and states fetch succeed</span>
      <span>Gemini: free-first, search grounding opt-in</span>
      <span>Unavailable rows: {unavailable}</span>
      <span>Errors: {errors}</span>
      {Object.entries(statusCounts)
        .slice(0, 6)
        .map(([status, count]) => (
          <span key={status}>
            {status}: {count}
          </span>
        ))}
    </footer>
  );
}

function RailSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rail-section">
      <h3>{title}</h3>
      <div>{children}</div>
    </section>
  );
}

function StatusRow({ row }: { row: Record<string, unknown> }) {
  const primary =
    row.provider ??
    row.label ??
    row.feed_id ??
    row.layer_id ??
    row.path ??
    row.source ??
    "status row";
  const secondary = row.error ?? row.warning ?? row.caveat ?? row.recommended_action ?? row.status ?? row.source_status;

  return (
    <div className="status-row">
      <strong>{formatValue(primary)}</strong>
      <span>{formatValue(secondary)}</span>
    </div>
  );
}

function StatusPill({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "ok" | "warn" | "danger" | "neutral";
}) {
  return (
    <span className={`status-pill ${tone}`}>
      <small>{label}</small>
      <strong>{value}</strong>
    </span>
  );
}
function shortNumber(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(1)}B`;
  }
  if (abs >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`;
  }
  if (abs >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`;
  }
  if (abs > 0 && abs < 1) {
    return value.toPrecision(2);
  }
  return value.toFixed(abs >= 100 ? 0 : 2);
}

function shortDateLabel(value: string): string {
  if (!value || value === "none") {
    return "";
  }
  const parsed = new Date(value);
  if (!Number.isNaN(parsed.getTime())) {
    return parsed.toISOString().slice(5, 10);
  }
  return value.length > 12 ? value.slice(0, 12) : value;
}

function numericValue(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function statusTone(value: unknown): "ok" | "warn" | "danger" | "neutral" {
  const status = String(value ?? "");
  if (status === "live/fresh" || status === "cached" || status === "available") {
    return "ok";
  }
  if (status === "missing-key" || status === "unavailable" || status.includes("forbidden")) {
    return "danger";
  }
  if (status.includes("proxy") || status === "fixture" || status === "stale" || status.includes("schema-ready")) {
    return "warn";
  }
  return "neutral";
}

function heatmapTone(value: number): "gain-strong" | "gain" | "flat" | "loss" | "loss-strong" {
  if (value >= 2.5) {
    return "gain-strong";
  }
  if (value >= 0.35) {
    return "gain";
  }
  if (value <= -2.5) {
    return "loss-strong";
  }
  if (value <= -0.35) {
    return "loss";
  }
  return "flat";
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toISOString();
}

function formatSigned(value: unknown): string {
  const number = numericValue(value);
  if (number === null) {
    return "none";
  }
  const prefix = number > 0 ? "+" : "";
  return `${prefix}${number.toFixed(2)}%`;
}

function labelize(value: string): string {
  return value.replaceAll("_", " ");
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "none";
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return "none";
    }
    return value.map(formatValue).join(", ");
  }

  if (isRecord(value)) {
    const entries = Object.entries(value)
      .slice(0, 4)
      .map(([key, item]) => `${labelize(key)}: ${formatValue(item)}`);
    return entries.length ? entries.join(" | ") : "object";
  }

  return String(value);
}

function selectSymbolWorkstationFixture(fixture: LoadedFixture, context: ProductAssetContext): LoadedFixture {
  if (!fixture.envelope || fixture.definition.key !== "symbol-workstation" || !isRecord(fixture.envelope.data)) {
    return fixture;
  }
  const data = fixture.envelope.data;
  const target = asRecordArray(data.workstations).find((row) => {
    const identity = isRecord(row.identity) ? row.identity : {};
    return formatValue(identity.symbol) === context.symbol && formatValue(identity.asset_class) === context.assetClass;
  });
  if (!target) {
    return {
      ...fixture,
      envelope: {
        ...fixture.envelope,
        data: { ...data, workstations: [] },
        summary: {
          workspace: "symbol-workstation",
          symbol: context.symbol,
          asset_class: context.assetClass,
          status: "unknown-symbol",
          source_status: "unavailable",
          workstation_count: 0,
          non_advisory: true,
        },
        source_status: [],
        unavailable: [{
          provider: "symbol-directory",
          source_status: "unavailable",
          availability: "unavailable",
          error: "unknown-symbol",
          recommended_action: "Search the bounded symbol directory.",
        }],
        errors: [],
      } as ContractEnvelope,
    };
  }
  const selectedTarget = withCatalogComparison(target, data, context);
  const sourceRows = asRecordArray(selectedTarget.source_register);
  const unavailable = asRecordArray(selectedTarget.unavailable_sources);
  return {
    ...fixture,
    envelope: {
      ...fixture.envelope,
      data: { ...data, workstations: [selectedTarget] },
      summary: isRecord(selectedTarget.summary) ? selectedTarget.summary : fixture.envelope.summary,
      source_status: sourceRows,
      unavailable,
      errors: unavailable.filter((row) => row.error),
    } as ContractEnvelope,
  };
}

function withCatalogComparison(target: Record<string, unknown>, data: Record<string, unknown>, context: ProductAssetContext): Record<string, unknown> {
  if (!context.compare) {
    return target;
  }
  const current = isRecord(target.comparison) ? target.comparison : {};
  if ((numericValue(current.overlap_count) ?? 0) > 1) {
    return target;
  }
  const compareTarget = asRecordArray(data.workstations).find((row) => {
    const identity = isRecord(row.identity) ? row.identity : {};
    return formatValue(identity.symbol) === context.compare;
  });
  if (!compareTarget) {
    return target;
  }
  const points = buildCatalogComparisonPoints(asRecordArray(target.history), asRecordArray(compareTarget.history));
  if (points.length < 2) {
    return target;
  }
  const primarySymbol = context.symbol;
  const compareSymbol = context.compare;
  const comparison = {
    status: "fixture-route-join",
    source_status: "fixture",
    primary_symbol: primarySymbol,
    comparison_symbol: compareSymbol,
    overlap_count: points.length,
    alignment_method: "timestamp-inner-join",
    normalization: "rebased-return-percent-from-first-overlap",
    points,
    caveat: "Computed from deterministic static catalog fallback rows because the optional runtime API was unavailable.",
    data_gap: "Static comparison is useful for layout and workflow verification, but it is not live market data.",
    not_financial_advice: true,
  };
  const comparisonChart = {
    chart_id: `${primarySymbol}.comparison`,
    chart_type: "indicator-line",
    title: `Normalized return vs ${compareSymbol}`,
    height_px: 180,
    source_status: "fixture",
    caveat: "Static catalog comparison generated in the web fallback path.",
    data_gap: "Runtime API comparison should replace this when available.",
    series: [
      { name: primarySymbol, points: points.map((point) => ({ x: point.x, y: point.primary_return_pct })) },
      { name: compareSymbol, points: points.map((point) => ({ x: point.x, y: point.comparison_return_pct })) },
    ],
  };
  const chartViews = isRecord(target.chart_views) ? target.chart_views : {};
  const analysis = asRecordArray(chartViews.analysis).filter((row) => !formatValue(row.chart_id).endsWith(".comparison"));
  const summary = isRecord(target.summary) ? target.summary : {};
  return {
    ...target,
    comparison,
    chart_views: { ...chartViews, analysis: [...analysis, comparisonChart] },
    chart_specs: [...asRecordArray(target.chart_specs).filter((row) => !formatValue(row.chart_id).endsWith(".comparison")), comparisonChart],
    summary: { ...summary, comparison_overlap_count: points.length },
  };
}

function buildCatalogComparisonPoints(primaryRows: Record<string, unknown>[], comparisonRows: Record<string, unknown>[]): Record<string, number | string>[] {
  const primaryByDate = normalizedCloseByDate(primaryRows);
  const comparisonByDate = normalizedCloseByDate(comparisonRows);
  const dates = [...primaryByDate.keys()].filter((date) => comparisonByDate.has(date)).sort();
  if (dates.length < 2) {
    return [];
  }
  const primaryBase = primaryByDate.get(dates[0]);
  const comparisonBase = comparisonByDate.get(dates[0]);
  if (!primaryBase || !comparisonBase) {
    return [];
  }
  return dates.map((date) => {
    const primary = primaryByDate.get(date) ?? primaryBase;
    const comparison = comparisonByDate.get(date) ?? comparisonBase;
    return {
      x: date,
      primary_return_pct: ((primary / primaryBase) - 1) * 100,
      comparison_return_pct: ((comparison / comparisonBase) - 1) * 100,
    };
  });
}

function normalizedCloseByDate(rows: Record<string, unknown>[]): Map<string, number> {
  const output = new Map<string, number>();
  rows.forEach((row) => {
    const close = numericValue(row.close);
    if (close === null || close <= 0) {
      return;
    }
    const rawDate = formatValue(row.date);
    const parsed = new Date(rawDate);
    if (Number.isNaN(parsed.getTime())) {
      return;
    }
    output.set(parsed.toISOString(), close);
  });
  return output;
}

function attentionReturnHref(origin: string | undefined, originView: string | undefined, originState: string | undefined): string | null {
  if (origin === "alert-manager" || originView === "alert-manager") {
    const input = new URLSearchParams(originState ?? "");
    const output = new URLSearchParams({ view: "alert-manager" });
    const mode = input.get("mode");
    if (["fixture", "cache"].includes(mode ?? "")) output.set("mode", mode as string);
    const tab = input.get("tab");
    if (["rules", "history", "runs"].includes(tab ?? "")) output.set("tab", tab as string);
    const selectedTrigger = input.get("selectedTrigger");
    if (/^[A-Za-z0-9_-]{3,80}$/.test(selectedTrigger ?? "")) output.set("selectedTrigger", selectedTrigger as string);
    return `/?${output}`;
  }
  if (origin !== "attention-desk" && originView !== "attention-desk") return null;
  const input = new URLSearchParams(originState ?? "");
  const output = new URLSearchParams({ view: "attention-desk" });
  const mode = input.get("mode");
  if (["fixture", "cache"].includes(mode ?? "")) output.set("mode", mode as string);
  const review = input.get("review");
  if (["needs-review", "all", "reviewed", "acknowledged"].includes(review ?? "")) output.set("review", review as string);
  return `/?${output}`;
}

function returnWorkspaceLabel(href: string): string {
  return href.includes("view=alert-manager") ? "Return to Alert Manager" : "Return to Attention Desk";
}

function compactAttentionEnvelope(envelope: ContractEnvelope): ContractEnvelope {
  const data = isRecord(envelope.data) ? envelope.data : {};
  const digest = isRecord(data.digest) ? data.digest : {};
  const summary = isRecord(data.summary) ? data.summary : {};
  const allItems = asRecordArray(data.all_items);
  const initialItems = allItems.slice(0, INITIAL_ATTENTION_ROW_LIMIT);
  return {
    ...envelope,
    data: {
      ...data,
      all_items: initialItems,
      items: [],
      digest: { ...digest, items: [] },
      summary: {
        ...summary,
        initial_row_limit: INITIAL_ATTENTION_ROW_LIMIT,
        total_row_count: allItems.length,
      },
    },
  } as ContractEnvelope;
}

function firstParam(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function panelForWorkspaceChange(value: string | undefined): string {
  if (value === "event" || value === "news") return "catalysts";
  if (value === "fundamental") return "financials";
  if (value === "source-status") return "sources";
  return "chart-core";
}

function normalizeMemorySurface(value: string | undefined): "inbox" | "watchlists" | "notes" | "reports" | "sources" {
  return value === "watchlists" || value === "notes" || value === "reports" || value === "sources" ? value : "inbox";
}

function normalizeNewsFilter(value: string | undefined): string {
  const normalized = String(value || "all").trim().toLowerCase();
  return /^[a-z0-9 _./-]{1,40}$/.test(normalized) ? normalized : "all";
}

function normalizeBriefPeriod(value: string | undefined): string {
  return value === "midday" || value === "close" || value === "weekly" ? value : "morning";
}

function normalizeBriefSection(value: string | undefined): string {
  return value === "cross_asset" || value === "global_risk" || value === "news_flow" || value === "watchlist" || value === "data_quality" ? value : "overview";
}

function normalizeResearchOrigin(value: string | undefined): string | null {
  const allowed = new Set(["aapl-equity", "btcusdt-crypto", "war-map", "market-map", "aapl-options", "demo-portfolio"]);
  const dynamicAsset = /^asset-(equity|etf|crypto)-[A-Z0-9._-]{1,24}$/.test(value || "");
  return value && (allowed.has(value) || dynamicAsset) ? value : null;
}

function researchOriginForFixture(key: FixtureKey): string | null {
  const origins: Partial<Record<FixtureKey, string>> = {
    "equity-intelligence": "aapl-equity",
    "crypto-intelligence": "btcusdt-crypto",
    "map-news-event-fusion": "war-map",
    "market-map-screener": "market-map",
    "options-quant": "aapl-options",
    "portfolio-risk": "demo-portfolio",
  };
  return origins[key] ?? null;
}
