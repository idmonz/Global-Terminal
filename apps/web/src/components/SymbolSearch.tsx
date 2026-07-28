"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useMemo, useState } from "react";

import type { RuntimeMode } from "@/lib/contracts";
import {
  canonicalAssetHref,
  type ProductAssetClass,
  type ProductAssetContext,
} from "@/lib/product-routes";

type Row = Record<string, unknown>;

export function SymbolSearch({
  identities,
  context,
  runtimeMode,
}: {
  identities: Row[];
  context: ProductAssetContext;
  runtimeMode: RuntimeMode;
}) {
  const router = useRouter();
  const [query, setQuery] = useState(context.symbol);
  const [expanded, setExpanded] = useState(false);
  const results = useMemo(() => rank(identities, query).slice(0, 8), [identities, query]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const target = results[0];
    if (!target) {
      setExpanded(true);
      return;
    }
    router.push(href(target, context, runtimeMode));
  }

  return (
    <form
      className="symbol-search"
      role="search"
      onSubmit={submit}
      onBlur={(event) => {
        const next = event.relatedTarget;
        if (!(next instanceof Node) || !event.currentTarget.contains(next)) setExpanded(false);
      }}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          event.stopPropagation();
          setExpanded(false);
        }
      }}
      data-symbol-search-state="ready"
      data-symbol-result-count={String(results.length)}
    >
      <label htmlFor="global-symbol-search">Search markets</label>
      <div className="symbol-search-field">
        <input
          id="global-symbol-search"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value.slice(0, 64));
            setExpanded(true);
          }}
          onFocus={() => setExpanded(true)}
          autoComplete="off"
          spellCheck={false}
          role="combobox"
          aria-autocomplete="list"
          aria-controls="global-symbol-results"
          aria-expanded={expanded}
          placeholder="Symbol or company"
        />
        <button type="submit" title="Open highest-ranked symbol">Open</button>
      </div>
      {expanded ? (
        <div className="symbol-search-results" id="global-symbol-results" role="listbox">
          {results.length ? results.map((row) => (
            <Link
              key={`${text(row.asset_class)}-${text(row.symbol)}`}
              href={href(row, context, runtimeMode)}
              role="option"
              onClick={() => setExpanded(false)}
            >
              <span className="symbol-search-code">{text(row.symbol)}</span>
              <span><strong>{text(row.name)}</strong><small>{text(row.exchange)} / {text(row.asset_class)}</small></span>
              <span className="symbol-search-state">{text(row.source_status)}</span>
            </Link>
          )) : (
            <div className="symbol-search-empty" role="status">
              <strong>No bounded-registry match</strong>
              <small>Try a symbol, company, ETF, or crypto asset name.</small>
            </div>
          )}
        </div>
      ) : null}
    </form>
  );
}

function href(row: Row, context: ProductAssetContext, mode: RuntimeMode) {
  return canonicalAssetHref(
    text(row.symbol),
    text(row.asset_class) as ProductAssetClass,
    context.interval,
    mode,
    "overview",
    context.range,
  );
}

function rank(rows: Row[], rawQuery: string): Row[] {
  const query = rawQuery.trim().toLowerCase().replace(/[^a-z0-9 ._=/\-]/g, "");
  if (!query) return rows;
  const compact = query.replace(/[^a-z0-9]/g, "");
  const words = query.split(/\s+/).filter(Boolean);
  return rows
    .map((row) => ({ row, score: score(row, compact, words) }))
    .filter((entry) => entry.score < 99)
    .sort((left, right) => left.score - right.score || text(left.row.symbol).localeCompare(text(right.row.symbol)))
    .map((entry) => entry.row);
}

function score(row: Row, compact: string, words: string[]) {
  const symbol = text(row.symbol).toLowerCase();
  const symbolCompact = symbol.replace(/[^a-z0-9]/g, "");
  const aliases = Array.isArray(row.aliases) ? row.aliases.map((item) => text(item).toLowerCase().replace(/[^a-z0-9]/g, "")) : [];
  const name = text(row.name).toLowerCase();
  if (symbolCompact === compact) return 0;
  if (aliases.includes(compact)) return 1;
  if (symbolCompact.startsWith(compact)) return 2;
  if (words.some((word) => name.startsWith(word))) return 3;
  if (words.every((word) => `${symbol} ${name}`.includes(word))) return 4;
  return 99;
}

function text(value: unknown, fallback = "") {
  return value === null || value === undefined || typeof value === "object" ? fallback : String(value);
}
