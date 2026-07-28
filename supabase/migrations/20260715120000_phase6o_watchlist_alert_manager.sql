begin;

set local lock_timeout = '10s';

alter table public.global_terminal_observation_snapshots
  add constraint global_terminal_observation_snapshots_owner_key
  unique (tenant_id, owner_user_id, snapshot_id);

create table public.global_terminal_watchlist_alert_rules (
  resource_id text primary key check (char_length(resource_id) between 8 and 80),
  tenant_id uuid not null references public.global_terminal_tenants(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  watchlist_id uuid not null,
  symbol text not null check (char_length(symbol) between 1 and 32),
  asset_class text not null default '',
  rule_type text not null check (rule_type in ('price_above','price_below','absolute_percent_move','material_saved_change','source_degradation')),
  metric text not null check (char_length(metric) between 1 and 64),
  operator text not null check (char_length(operator) between 1 and 48),
  threshold jsonb not null,
  threshold_unit text not null default '',
  frequency text not null check (frequency in ('5m','15m','1h','4h','1d')),
  frequency_minutes integer not null check (frequency_minutes in (5,15,60,240,1440)),
  session_policy text not null check (session_policy in ('market-aware','regular-only','extended','continuous')),
  cooldown_minutes integer not null default 60 check (cooldown_minutes between 0 and 10080),
  severity text not null default 'watch' check (severity in ('info','watch','material','high','critical')),
  state text not null default 'active' check (state in ('active','paused','expired','cancelled','deleted')),
  fingerprint text not null check (char_length(fingerprint) = 64),
  next_due_at timestamptz,
  expires_at timestamptz,
  last_evaluated_at timestamptz,
  last_triggered_at timestamptz,
  last_snapshot_id text,
  last_observed_value jsonb,
  deleted_at timestamptz,
  version integer not null default 1 check (version > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, owner_user_id, resource_id),
  foreign key (tenant_id, watchlist_id)
    references public.global_terminal_watchlists(tenant_id, id) on delete cascade
);

create table public.global_terminal_watchlist_alert_evaluations (
  run_id text primary key check (char_length(run_id) between 8 and 80),
  tenant_id uuid not null references public.global_terminal_tenants(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  idempotency_key text not null check (char_length(idempotency_key) between 8 and 128),
  request_fingerprint text not null check (char_length(request_fingerprint) = 64),
  mode text not null default 'manual' check (mode in ('manual','worker')),
  status text not null check (status in ('no-due','completed','partial','cancelled','quota-blocked','failed')),
  due_count integer not null default 0 check (due_count between 0 and 50),
  evaluated_count integer not null default 0 check (evaluated_count between 0 and 50),
  triggered_count integer not null default 0 check (triggered_count between 0 and 50),
  deduped_count integer not null default 0 check (deduped_count between 0 and 50),
  data_gap_count integer not null default 0 check (data_gap_count between 0 and 50),
  quota_blocked_count integer not null default 0 check (quota_blocked_count between 0 and 50),
  provider_call_count integer not null default 0 check (provider_call_count between 0 and 16),
  source_clock jsonb not null default '{}'::jsonb check (jsonb_typeof(source_clock) = 'object'),
  detail jsonb not null default '{}'::jsonb check (jsonb_typeof(detail) = 'object'),
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  duration_ms integer not null default 0 check (duration_ms between 0 and 300000),
  created_at timestamptz not null default now(),
  unique (tenant_id, idempotency_key),
  unique (tenant_id, owner_user_id, run_id)
);

create table public.global_terminal_watchlist_alert_triggers (
  trigger_id text primary key check (char_length(trigger_id) between 8 and 80),
  tenant_id uuid not null references public.global_terminal_tenants(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  rule_id text not null,
  watchlist_id uuid not null,
  evaluation_run_id text not null,
  snapshot_id text not null,
  symbol text not null check (char_length(symbol) between 1 and 32),
  dedupe_key text not null check (char_length(dedupe_key) = 64),
  status text not null default 'triggered' check (status in ('triggered','resolved')),
  severity text not null default 'watch' check (severity in ('info','watch','material','high','critical')),
  review_state text not null default 'new' check (review_state in ('new','reviewed','acknowledged')),
  metric text not null,
  operator text not null,
  threshold jsonb not null,
  observed_value jsonb not null,
  source_status text not null,
  provider text not null default '',
  source_url text not null default '',
  observed_at timestamptz,
  retrieved_at timestamptz,
  evaluated_at timestamptz not null,
  triggered_at timestamptz not null,
  reviewed_at timestamptz,
  acknowledged_at timestamptz,
  message text not null check (char_length(message) between 1 and 280),
  caveat text not null default '',
  data_gap text not null default '',
  evidence jsonb not null default '{}'::jsonb check (jsonb_typeof(evidence) = 'object'),
  version integer not null default 1 check (version > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, dedupe_key),
  unique (tenant_id, owner_user_id, trigger_id),
  foreign key (tenant_id, watchlist_id)
    references public.global_terminal_watchlists(tenant_id, id) on delete cascade,
  foreign key (tenant_id, owner_user_id, rule_id)
    references public.global_terminal_watchlist_alert_rules(tenant_id, owner_user_id, resource_id) on delete cascade,
  foreign key (tenant_id, owner_user_id, evaluation_run_id)
    references public.global_terminal_watchlist_alert_evaluations(tenant_id, owner_user_id, run_id) on delete cascade,
  foreign key (tenant_id, owner_user_id, snapshot_id)
    references public.global_terminal_observation_snapshots(tenant_id, owner_user_id, snapshot_id) on delete restrict
);

create table public.global_terminal_watchlist_alert_audit (
  event_id text primary key check (char_length(event_id) between 8 and 80),
  tenant_id uuid not null references public.global_terminal_tenants(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  resource_type text not null check (resource_type in ('rule','evaluation','trigger','worker')),
  resource_id text not null check (char_length(resource_id) between 1 and 80),
  event_type text not null check (char_length(event_type) between 1 and 64),
  prior_state text not null default '',
  new_state text not null default '',
  detail jsonb not null default '{}'::jsonb check (jsonb_typeof(detail) = 'object'),
  created_at timestamptz not null default now()
);

create table public.global_terminal_watchlist_alert_worker_state (
  resource_id text primary key check (char_length(resource_id) between 8 and 80),
  tenant_id uuid not null references public.global_terminal_tenants(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  state text not null default 'stopped' check (state in ('starting','idle','running','stopped','offline','restarted')),
  enabled boolean not null default false,
  last_started_at timestamptz,
  last_heartbeat_at timestamptz,
  last_stopped_at timestamptz,
  last_evaluation_run_id text,
  restart_count integer not null default 0 check (restart_count between 0 and 1000000),
  error_code text not null default '',
  version integer not null default 1 check (version > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, owner_user_id),
  foreign key (tenant_id, owner_user_id, last_evaluation_run_id)
    references public.global_terminal_watchlist_alert_evaluations(tenant_id, owner_user_id, run_id) on delete set null
);

create index global_terminal_alert_rules_due_idx
  on public.global_terminal_watchlist_alert_rules (tenant_id, owner_user_id, state, next_due_at);
create index global_terminal_alert_triggers_review_idx
  on public.global_terminal_watchlist_alert_triggers (tenant_id, owner_user_id, review_state, triggered_at desc);
create index global_terminal_alert_evaluations_created_idx
  on public.global_terminal_watchlist_alert_evaluations (tenant_id, owner_user_id, created_at desc);
create index global_terminal_alert_audit_created_idx
  on public.global_terminal_watchlist_alert_audit (tenant_id, owner_user_id, created_at desc);

alter table public.global_terminal_watchlist_alert_rules enable row level security;
alter table public.global_terminal_watchlist_alert_evaluations enable row level security;
alter table public.global_terminal_watchlist_alert_triggers enable row level security;
alter table public.global_terminal_watchlist_alert_audit enable row level security;
alter table public.global_terminal_watchlist_alert_worker_state enable row level security;

revoke all on table public.global_terminal_watchlist_alert_rules from anon, authenticated;
revoke all on table public.global_terminal_watchlist_alert_evaluations from anon, authenticated;
revoke all on table public.global_terminal_watchlist_alert_triggers from anon, authenticated;
revoke all on table public.global_terminal_watchlist_alert_audit from anon, authenticated;
revoke all on table public.global_terminal_watchlist_alert_worker_state from anon, authenticated;

grant select, insert, update, delete on table public.global_terminal_watchlist_alert_rules to authenticated;
grant select, insert, delete on table public.global_terminal_watchlist_alert_evaluations to authenticated;
grant select, insert, update, delete on table public.global_terminal_watchlist_alert_triggers to authenticated;
grant select on table public.global_terminal_watchlist_alert_audit to authenticated;
grant select, insert, update, delete on table public.global_terminal_watchlist_alert_worker_state to authenticated;

do $$
declare
  table_name text;
begin
  foreach table_name in array array[
    'global_terminal_watchlist_alert_rules',
    'global_terminal_watchlist_alert_evaluations',
    'global_terminal_watchlist_alert_triggers',
    'global_terminal_watchlist_alert_worker_state'
  ] loop
    execute format(
      'create policy %I on public.%I for select to authenticated using (owner_user_id = (select auth.uid()) and exists (select 1 from public.global_terminal_tenant_memberships membership where membership.tenant_id = %I.tenant_id and membership.user_id = (select auth.uid())))',
      table_name || '_read', table_name, table_name
    );
    execute format(
      'create policy %I on public.%I for insert to authenticated with check (owner_user_id = (select auth.uid()) and exists (select 1 from public.global_terminal_tenant_memberships membership where membership.tenant_id = %I.tenant_id and membership.user_id = (select auth.uid()) and membership.role in (''owner'',''member'')))',
      table_name || '_insert', table_name, table_name
    );
    execute format(
      'create policy %I on public.%I for update to authenticated using (owner_user_id = (select auth.uid()) and exists (select 1 from public.global_terminal_tenant_memberships membership where membership.tenant_id = %I.tenant_id and membership.user_id = (select auth.uid()) and membership.role in (''owner'',''member''))) with check (owner_user_id = (select auth.uid()) and exists (select 1 from public.global_terminal_tenant_memberships membership where membership.tenant_id = %I.tenant_id and membership.user_id = (select auth.uid()) and membership.role in (''owner'',''member'')))',
      table_name || '_update', table_name, table_name, table_name
    );
    execute format(
      'create policy %I on public.%I for delete to authenticated using (owner_user_id = (select auth.uid()) and exists (select 1 from public.global_terminal_tenant_memberships membership where membership.tenant_id = %I.tenant_id and membership.user_id = (select auth.uid()) and membership.role in (''owner'',''member'')))',
      table_name || '_delete', table_name, table_name
    );
  end loop;
end $$;

create policy global_terminal_watchlist_alert_audit_read
  on public.global_terminal_watchlist_alert_audit for select to authenticated
  using (
    owner_user_id = (select auth.uid())
    and exists (
      select 1 from public.global_terminal_tenant_memberships membership
      where membership.tenant_id = global_terminal_watchlist_alert_audit.tenant_id
        and membership.user_id = (select auth.uid())
    )
  );

create or replace function public.global_terminal_record_watchlist_alert_audit()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  row_json jsonb;
  prior_json jsonb;
  resource_kind text;
  resource_key text;
  prior_value text;
  next_value text;
begin
  row_json := case when tg_op = 'DELETE' then to_jsonb(old) else to_jsonb(new) end;
  prior_json := case when tg_op = 'INSERT' then '{}'::jsonb else to_jsonb(old) end;
  resource_kind := case tg_table_name
    when 'global_terminal_watchlist_alert_rules' then 'rule'
    when 'global_terminal_watchlist_alert_evaluations' then 'evaluation'
    when 'global_terminal_watchlist_alert_triggers' then 'trigger'
    else 'worker'
  end;
  resource_key := coalesce(row_json->>'resource_id', row_json->>'run_id', row_json->>'trigger_id', 'unknown');
  prior_value := coalesce(prior_json->>'state', prior_json->>'status', prior_json->>'review_state', '');
  next_value := case when tg_op = 'DELETE' then '' else coalesce(row_json->>'state', row_json->>'status', row_json->>'review_state', '') end;

  insert into public.global_terminal_watchlist_alert_audit (
    event_id, tenant_id, owner_user_id, resource_type, resource_id,
    event_type, prior_state, new_state, detail, created_at
  ) values (
    'alaa_' || replace(gen_random_uuid()::text, '-', ''),
    (row_json->>'tenant_id')::uuid,
    (row_json->>'owner_user_id')::uuid,
    resource_kind,
    resource_key,
    resource_kind || '-' || lower(tg_op),
    prior_value,
    next_value,
    jsonb_build_object('operation', lower(tg_op), 'version', coalesce((row_json->>'version')::integer, 1)),
    now()
  );

  if tg_op = 'DELETE' then return old; end if;
  return new;
end;
$$;

revoke all on function public.global_terminal_record_watchlist_alert_audit()
from public, anon, authenticated;

create trigger global_terminal_watchlist_alert_rules_audit_trigger
after insert or update or delete on public.global_terminal_watchlist_alert_rules
for each row execute function public.global_terminal_record_watchlist_alert_audit();
create trigger global_terminal_watchlist_alert_evaluations_audit_trigger
after insert or delete on public.global_terminal_watchlist_alert_evaluations
for each row execute function public.global_terminal_record_watchlist_alert_audit();
create trigger global_terminal_watchlist_alert_triggers_audit_trigger
after insert or update or delete on public.global_terminal_watchlist_alert_triggers
for each row execute function public.global_terminal_record_watchlist_alert_audit();
create trigger global_terminal_watchlist_alert_worker_audit_trigger
after insert or update or delete on public.global_terminal_watchlist_alert_worker_state
for each row execute function public.global_terminal_record_watchlist_alert_audit();

commit;

