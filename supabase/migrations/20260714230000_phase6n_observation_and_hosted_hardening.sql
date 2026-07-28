begin;

set local lock_timeout = '10s';

-- Earlier hosted tables were provisioned before CLI migration history was
-- adopted. Remove broad default grants while preserving the reviewed DML
-- surface used by the authenticated account APIs.
do $$
declare
  table_name text;
begin
  foreach table_name in array array[
    'global_terminal_tenants',
    'global_terminal_tenant_memberships',
    'global_terminal_workspace_preferences',
    'global_terminal_watchlists',
    'global_terminal_watchlist_items',
    'global_terminal_import_receipts',
    'global_terminal_alert_rules',
    'global_terminal_inbox_items',
    'global_terminal_sync_receipts',
    'global_terminal_deletion_tombstones',
    'global_terminal_attention_states',
    'global_terminal_attention_policies',
    'global_terminal_attention_checkpoints',
    'global_terminal_attention_audit'
  ] loop
    execute format('revoke all on table public.%I from anon', table_name);
    execute format('revoke all on table public.%I from authenticated', table_name);
  end loop;
end $$;

grant select on table
  public.global_terminal_tenants,
  public.global_terminal_tenant_memberships
to authenticated;

grant select, insert, update, delete on table
  public.global_terminal_workspace_preferences,
  public.global_terminal_watchlists,
  public.global_terminal_watchlist_items,
  public.global_terminal_import_receipts,
  public.global_terminal_alert_rules,
  public.global_terminal_inbox_items,
  public.global_terminal_sync_receipts,
  public.global_terminal_deletion_tombstones,
  public.global_terminal_attention_states,
  public.global_terminal_attention_policies,
  public.global_terminal_attention_checkpoints
to authenticated;

grant select, insert on table public.global_terminal_attention_audit
to authenticated;

create table public.global_terminal_observation_runs (
  run_id text primary key check (char_length(run_id) between 8 and 80),
  tenant_id uuid not null references public.global_terminal_tenants(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  watchlist_resource_id text not null check (char_length(watchlist_resource_id) between 1 and 120),
  idempotency_key text not null check (char_length(idempotency_key) between 8 and 128),
  request_fingerprint text not null check (char_length(request_fingerprint) = 64),
  status text not null check (status in ('queued','running','partial','completed','cancelled','failed')),
  request_json jsonb not null default '{}'::jsonb check (jsonb_typeof(request_json) = 'object'),
  plan_json jsonb not null default '{}'::jsonb check (jsonb_typeof(plan_json) = 'object'),
  result_json jsonb not null default '{}'::jsonb check (jsonb_typeof(result_json) = 'object'),
  cancellation_requested boolean not null default false,
  attempted_at timestamptz,
  started_at timestamptz,
  completed_at timestamptz,
  version integer not null default 1 check (version > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, idempotency_key),
  unique (tenant_id, owner_user_id, run_id)
);

create table public.global_terminal_observation_snapshots (
  snapshot_id text primary key check (char_length(snapshot_id) between 8 and 80),
  tenant_id uuid not null references public.global_terminal_tenants(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  run_id text not null,
  watchlist_resource_id text not null check (char_length(watchlist_resource_id) between 1 and 120),
  symbol text not null check (char_length(symbol) between 1 and 32),
  asset_class text not null default '',
  snapshot_status text not null,
  source_status text not null,
  observed_at timestamptz,
  retrieved_at timestamptz not null,
  provider text not null default '',
  source_url text not null default '',
  confidence double precision check (confidence is null or confidence between 0 and 1),
  content_hash text not null check (char_length(content_hash) = 64),
  payload_json jsonb not null check (jsonb_typeof(payload_json) = 'object'),
  caveat text not null default '',
  data_gap text not null default '',
  lkg_source_snapshot_id text,
  created_at timestamptz not null default now(),
  unique (tenant_id, run_id, symbol),
  foreign key (tenant_id, owner_user_id, run_id)
    references public.global_terminal_observation_runs(tenant_id, owner_user_id, run_id)
    on delete cascade
);

create table public.global_terminal_provider_quota_ledger (
  event_id text primary key check (char_length(event_id) between 8 and 80),
  tenant_id uuid not null references public.global_terminal_tenants(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  run_id text not null,
  provider text not null check (char_length(provider) between 1 and 80),
  operation text not null check (char_length(operation) between 1 and 120),
  call_count integer not null default 0 check (call_count between 0 and 1000),
  source_status text not null default 'unavailable',
  occurred_at timestamptz not null default now(),
  foreign key (tenant_id, owner_user_id, run_id)
    references public.global_terminal_observation_runs(tenant_id, owner_user_id, run_id)
    on delete cascade
);

-- Audit rows deliberately keep an opaque run_id without a parent foreign key.
-- Deleting a run may remove bounded snapshots/quota rows but cannot erase its
-- lifecycle evidence through a cascade.
create table public.global_terminal_observation_run_audit (
  event_id text primary key check (char_length(event_id) between 8 and 80),
  tenant_id uuid not null references public.global_terminal_tenants(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  run_id text not null check (char_length(run_id) between 8 and 80),
  event_type text not null check (char_length(event_type) between 1 and 48),
  prior_status text not null default '',
  new_status text not null default '',
  detail_json jsonb not null default '{}'::jsonb check (jsonb_typeof(detail_json) = 'object'),
  created_at timestamptz not null default now()
);

create index global_terminal_observation_runs_owner_idx
  on public.global_terminal_observation_runs (tenant_id, owner_user_id, created_at desc);
create index global_terminal_observation_snapshots_owner_idx
  on public.global_terminal_observation_snapshots (tenant_id, owner_user_id, watchlist_resource_id, symbol, created_at desc);
create index global_terminal_provider_quota_owner_idx
  on public.global_terminal_provider_quota_ledger (tenant_id, owner_user_id, provider, occurred_at desc);
create index global_terminal_observation_audit_owner_idx
  on public.global_terminal_observation_run_audit (tenant_id, owner_user_id, run_id, created_at desc);

alter table public.global_terminal_observation_runs enable row level security;
alter table public.global_terminal_observation_snapshots enable row level security;
alter table public.global_terminal_provider_quota_ledger enable row level security;
alter table public.global_terminal_observation_run_audit enable row level security;

revoke all on table public.global_terminal_observation_runs from anon, authenticated;
revoke all on table public.global_terminal_observation_snapshots from anon, authenticated;
revoke all on table public.global_terminal_provider_quota_ledger from anon, authenticated;
revoke all on table public.global_terminal_observation_run_audit from anon, authenticated;

grant select, insert, update, delete on table public.global_terminal_observation_runs to authenticated;
grant select, insert on table public.global_terminal_observation_snapshots to authenticated;
grant select, insert on table public.global_terminal_provider_quota_ledger to authenticated;
grant select on table public.global_terminal_observation_run_audit to authenticated;

create policy observation_runs_read on public.global_terminal_observation_runs
  for select to authenticated
  using (
    owner_user_id = (select auth.uid())
    and exists (
      select 1 from public.global_terminal_tenant_memberships membership
      where membership.tenant_id = global_terminal_observation_runs.tenant_id
        and membership.user_id = (select auth.uid())
    )
  );
create policy observation_runs_insert on public.global_terminal_observation_runs
  for insert to authenticated
  with check (
    owner_user_id = (select auth.uid())
    and exists (
      select 1 from public.global_terminal_tenant_memberships membership
      where membership.tenant_id = global_terminal_observation_runs.tenant_id
        and membership.user_id = (select auth.uid())
        and membership.role in ('owner', 'member')
    )
  );
create policy observation_runs_update on public.global_terminal_observation_runs
  for update to authenticated
  using (
    owner_user_id = (select auth.uid())
    and exists (
      select 1 from public.global_terminal_tenant_memberships membership
      where membership.tenant_id = global_terminal_observation_runs.tenant_id
        and membership.user_id = (select auth.uid())
        and membership.role in ('owner', 'member')
    )
  )
  with check (
    owner_user_id = (select auth.uid())
    and exists (
      select 1 from public.global_terminal_tenant_memberships membership
      where membership.tenant_id = global_terminal_observation_runs.tenant_id
        and membership.user_id = (select auth.uid())
        and membership.role in ('owner', 'member')
    )
  );
create policy observation_runs_delete on public.global_terminal_observation_runs
  for delete to authenticated
  using (
    owner_user_id = (select auth.uid())
    and exists (
      select 1 from public.global_terminal_tenant_memberships membership
      where membership.tenant_id = global_terminal_observation_runs.tenant_id
        and membership.user_id = (select auth.uid())
        and membership.role in ('owner', 'member')
    )
  );

create policy observation_snapshots_read on public.global_terminal_observation_snapshots
  for select to authenticated
  using (
    owner_user_id = (select auth.uid())
    and exists (
      select 1 from public.global_terminal_tenant_memberships membership
      where membership.tenant_id = global_terminal_observation_snapshots.tenant_id
        and membership.user_id = (select auth.uid())
    )
  );
create policy observation_snapshots_insert on public.global_terminal_observation_snapshots
  for insert to authenticated
  with check (
    owner_user_id = (select auth.uid())
    and exists (
      select 1 from public.global_terminal_tenant_memberships membership
      where membership.tenant_id = global_terminal_observation_snapshots.tenant_id
        and membership.user_id = (select auth.uid())
        and membership.role in ('owner', 'member')
    )
  );

create policy provider_quota_read on public.global_terminal_provider_quota_ledger
  for select to authenticated
  using (
    owner_user_id = (select auth.uid())
    and exists (
      select 1 from public.global_terminal_tenant_memberships membership
      where membership.tenant_id = global_terminal_provider_quota_ledger.tenant_id
        and membership.user_id = (select auth.uid())
    )
  );
create policy provider_quota_insert on public.global_terminal_provider_quota_ledger
  for insert to authenticated
  with check (
    owner_user_id = (select auth.uid())
    and exists (
      select 1 from public.global_terminal_tenant_memberships membership
      where membership.tenant_id = global_terminal_provider_quota_ledger.tenant_id
        and membership.user_id = (select auth.uid())
        and membership.role in ('owner', 'member')
    )
  );

create policy observation_audit_read on public.global_terminal_observation_run_audit
  for select to authenticated
  using (
    owner_user_id = (select auth.uid())
    and exists (
      select 1 from public.global_terminal_tenant_memberships membership
      where membership.tenant_id = global_terminal_observation_run_audit.tenant_id
        and membership.user_id = (select auth.uid())
    )
  );

create or replace function public.global_terminal_record_observation_run_audit()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  audit_row public.global_terminal_observation_runs%rowtype;
  audit_event_type text;
begin
  if tg_op = 'DELETE' then
    audit_row := old;
  else
    audit_row := new;
  end if;
  audit_event_type := case
    when tg_op = 'INSERT' then 'run-created'
    when tg_op = 'DELETE' then 'run-deleted'
    when old.status is distinct from new.status then 'run-status-changed'
    when old.cancellation_requested is distinct from new.cancellation_requested then 'cancellation-changed'
    else 'run-updated'
  end;

  insert into public.global_terminal_observation_run_audit (
    event_id,
    tenant_id,
    owner_user_id,
    run_id,
    event_type,
    prior_status,
    new_status,
    detail_json,
    created_at
  ) values (
    'ora_' || replace(gen_random_uuid()::text, '-', ''),
    audit_row.tenant_id,
    audit_row.owner_user_id,
    audit_row.run_id,
    audit_event_type,
    case when tg_op = 'INSERT' then '' else old.status end,
    case when tg_op = 'DELETE' then '' else new.status end,
    jsonb_build_object(
      'operation', lower(tg_op),
      'version', audit_row.version,
      'cancellation_requested', audit_row.cancellation_requested
    ),
    now()
  );

  return case when tg_op = 'DELETE' then old else new end;
end;
$$;

revoke all on function public.global_terminal_record_observation_run_audit()
from public, anon, authenticated;

create trigger global_terminal_observation_run_audit_trigger
after insert or update or delete on public.global_terminal_observation_runs
for each row execute function public.global_terminal_record_observation_run_audit();

commit;
