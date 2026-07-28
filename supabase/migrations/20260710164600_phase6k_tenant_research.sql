-- Phase 6K hosted persistence schema (migration version 20260710164600). This migration is readiness
-- evidence only; the product must remain `hosted_persistence=unavailable`
-- until auth, RLS, CRUD, recovery, and A/B isolation are live-tested.

create table if not exists public.global_terminal_watchlists (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.global_terminal_tenants(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  name text not null check (char_length(name) between 1 and 80),
  source_key text not null check (char_length(source_key) between 1 and 120),
  source_fingerprint text not null,
  version integer not null default 1 check (version > 0),
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, source_key),
  unique (tenant_id, id)
);

create table if not exists public.global_terminal_watchlist_items (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.global_terminal_tenants(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  watchlist_id uuid not null,
  symbol text not null check (char_length(symbol) between 1 and 32),
  asset_class text not null default '',
  display_name text not null check (char_length(display_name) between 1 and 160),
  exchange text not null default '',
  position integer not null default 0 check (position >= 0),
  provider text not null default '',
  source_url text not null default '',
  source_status text not null default 'unavailable',
  observed_at timestamptz,
  retrieved_at timestamptz,
  evidence jsonb not null default '{}'::jsonb,
  version integer not null default 1 check (version > 0),
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, watchlist_id, symbol),
  foreign key (tenant_id, watchlist_id)
    references public.global_terminal_watchlists(tenant_id, id) on delete cascade
);

create table if not exists public.global_terminal_import_receipts (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.global_terminal_tenants(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  idempotency_key text not null check (char_length(idempotency_key) between 8 and 128),
  request_fingerprint text not null,
  preview_id text not null,
  watchlist_id uuid not null,
  selected_count integer not null default 0 check (selected_count between 0 and 25),
  excluded_fields jsonb not null default '[]'::jsonb,
  consented_at timestamptz not null default now(),
  retention_until timestamptz not null default (now() + interval '365 days'),
  unique (tenant_id, idempotency_key),
  foreign key (tenant_id, watchlist_id)
    references public.global_terminal_watchlists(tenant_id, id) on delete cascade
);

create table if not exists public.global_terminal_alert_rules (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.global_terminal_tenants(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  watchlist_id uuid not null,
  enabled boolean not null default false,
  minimum_severity text not null default 'material' check (minimum_severity in ('info', 'material', 'high', 'critical')),
  cooldown_minutes integer not null default 60 check (cooldown_minutes between 0 and 10080),
  expires_at timestamptz,
  last_triggered_at timestamptz,
  version integer not null default 1 check (version > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, watchlist_id),
  unique (tenant_id, id),
  foreign key (tenant_id, watchlist_id)
    references public.global_terminal_watchlists(tenant_id, id) on delete cascade
);

create table if not exists public.global_terminal_inbox_items (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.global_terminal_tenants(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  watchlist_id uuid not null,
  rule_id uuid not null,
  dedupe_key text not null,
  symbol text not null check (char_length(symbol) between 1 and 32),
  change_id text not null,
  change_type text not null,
  state text not null default 'new' check (state in ('new', 'reviewed', 'acknowledged')),
  severity text not null default 'material' check (severity in ('info', 'material', 'high', 'critical')),
  title text not null check (char_length(title) between 1 and 180),
  summary text not null default '',
  evidence jsonb not null default '{}'::jsonb,
  source_status text not null default 'unavailable',
  observed_at timestamptz,
  retrieved_at timestamptz,
  expires_at timestamptz not null default (now() + interval '90 days'),
  reviewed_at timestamptz,
  acknowledged_at timestamptz,
  version integer not null default 1 check (version > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, dedupe_key),
  foreign key (tenant_id, watchlist_id)
    references public.global_terminal_watchlists(tenant_id, id) on delete cascade,
  foreign key (tenant_id, rule_id)
    references public.global_terminal_alert_rules(tenant_id, id) on delete cascade
);

create index if not exists global_terminal_watchlists_tenant_updated_idx
  on public.global_terminal_watchlists (tenant_id, active, updated_at desc);
create index if not exists global_terminal_watchlist_items_parent_idx
  on public.global_terminal_watchlist_items (tenant_id, watchlist_id, active, position);
create index if not exists global_terminal_import_receipts_tenant_idx
  on public.global_terminal_import_receipts (tenant_id, consented_at desc);
create index if not exists global_terminal_alert_rules_parent_idx
  on public.global_terminal_alert_rules (tenant_id, watchlist_id, enabled);
create index if not exists global_terminal_inbox_tenant_state_idx
  on public.global_terminal_inbox_items (tenant_id, state, created_at desc);

alter table public.global_terminal_watchlists enable row level security;
alter table public.global_terminal_watchlist_items enable row level security;
alter table public.global_terminal_import_receipts enable row level security;
alter table public.global_terminal_alert_rules enable row level security;
alter table public.global_terminal_inbox_items enable row level security;

do $$
declare
  table_name text;
begin
  foreach table_name in array array[
    'global_terminal_watchlists',
    'global_terminal_watchlist_items',
    'global_terminal_import_receipts',
    'global_terminal_alert_rules',
    'global_terminal_inbox_items'
  ] loop
    execute format('drop policy if exists "tenant members read" on public.%I', table_name);
    execute format(
      'create policy "tenant members read" on public.%I for select to authenticated using (exists (select 1 from public.global_terminal_tenant_memberships m where m.tenant_id = %I.tenant_id and m.user_id = (select auth.uid())))',
      table_name, table_name
    );
    execute format('drop policy if exists "tenant members insert" on public.%I', table_name);
    execute format(
      'create policy "tenant members insert" on public.%I for insert to authenticated with check (owner_user_id = (select auth.uid()) and exists (select 1 from public.global_terminal_tenant_memberships m where m.tenant_id = %I.tenant_id and m.user_id = (select auth.uid()) and m.role in (''owner'', ''member'')))',
      table_name, table_name
    );
    execute format('drop policy if exists "tenant members update" on public.%I', table_name);
    execute format(
      'create policy "tenant members update" on public.%I for update to authenticated using (exists (select 1 from public.global_terminal_tenant_memberships m where m.tenant_id = %I.tenant_id and m.user_id = (select auth.uid()) and m.role in (''owner'', ''member''))) with check (owner_user_id = (select auth.uid()) and exists (select 1 from public.global_terminal_tenant_memberships m where m.tenant_id = %I.tenant_id and m.user_id = (select auth.uid()) and m.role in (''owner'', ''member'')))',
      table_name, table_name, table_name
    );
    execute format('drop policy if exists "tenant members delete" on public.%I', table_name);
    execute format(
      'create policy "tenant members delete" on public.%I for delete to authenticated using (exists (select 1 from public.global_terminal_tenant_memberships m where m.tenant_id = %I.tenant_id and m.user_id = (select auth.uid()) and m.role in (''owner'', ''member'')))',
      table_name, table_name
    );
  end loop;
end $$;
