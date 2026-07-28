begin;

set local lock_timeout = '10s';

create table public.global_terminal_hosted_scheduler_control (
  singleton boolean primary key default true check (singleton),
  operator_enabled boolean not null default false,
  global_kill_switch boolean not null default true,
  hosted_scheduler_verified boolean not null default false,
  maximum_concurrency integer not null default 1 check (maximum_concurrency = 1),
  runner_kind text not null default 'github-actions-python' check (runner_kind = 'github-actions-python'),
  updated_at timestamptz not null default now()
);

insert into public.global_terminal_hosted_scheduler_control (
  singleton, operator_enabled, global_kill_switch, hosted_scheduler_verified
) values (true, false, true, false)
on conflict (singleton) do nothing;

create table public.global_terminal_hosted_observation_schedules (
  schedule_id text primary key check (char_length(schedule_id) between 8 and 80),
  tenant_id uuid not null references public.global_terminal_tenants(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  account_document_id uuid not null,
  account_document_version integer not null check (account_document_version > 0),
  watchlist_resource_id text not null check (char_length(watchlist_resource_id) between 3 and 80),
  alert_rule_resource_id text not null check (char_length(alert_rule_resource_id) between 3 and 80),
  state text not null default 'disabled' check (state in ('disabled','enabled','paused','killed','deleted')),
  timezone text not null default 'UTC' check (char_length(timezone) between 1 and 64),
  cadence_minutes integer not null default 60 check (cadence_minutes in (60,240,1440)),
  max_symbols integer not null default 1 check (max_symbols between 1 and 5),
  max_provider_calls integer not null default 4 check (max_provider_calls between 0 and 16),
  max_attempts integer not null default 2 check (max_attempts between 1 and 3),
  timeout_seconds integer not null default 90 check (timeout_seconds between 15 and 120),
  next_due_at timestamptz,
  last_attempted_at timestamptz,
  last_completed_at timestamptz,
  last_run_id text,
  last_lkg_run_id text,
  consented_at timestamptz,
  enabled_at timestamptz,
  paused_at timestamptz,
  killed_at timestamptz,
  deleted_at timestamptz,
  version integer not null default 1 check (version > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, owner_user_id, schedule_id),
  unique (tenant_id, owner_user_id),
  foreign key (tenant_id, owner_user_id, account_document_id)
    references public.global_terminal_account_documents(tenant_id, owner_user_id, document_id)
    on delete restrict,
  check (state not in ('enabled','paused') or consented_at is not null)
);

create table public.global_terminal_hosted_observation_schedule_runs (
  scheduler_run_id text primary key check (char_length(scheduler_run_id) between 8 and 80),
  tenant_id uuid not null references public.global_terminal_tenants(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  schedule_id text not null,
  due_window_at timestamptz not null,
  idempotency_key text not null check (char_length(idempotency_key) between 8 and 128),
  status text not null default 'leased' check (status in ('queued','leased','running','completed','partial','quota-blocked','provider-unavailable','cancelled','killed','failed')),
  lease_owner_hash text not null default '' check (lease_owner_hash = '' or lease_owner_hash ~ '^[a-f0-9]{64}$'),
  lease_token_hash text not null default '' check (lease_token_hash = '' or lease_token_hash ~ '^[a-f0-9]{64}$'),
  lease_acquired_at timestamptz,
  lease_expires_at timestamptz,
  heartbeat_at timestamptz,
  attempt_count integer not null default 0 check (attempt_count between 0 and 3),
  observation_run_id text,
  evaluation_run_id text,
  trigger_count integer not null default 0 check (trigger_count between 0 and 50),
  provider_call_budget integer not null default 0 check (provider_call_budget between 0 and 16),
  provider_call_count integer not null default 0 check (provider_call_count between 0 and 16),
  provider text not null default '',
  source_url text not null default '',
  source_status text not null default 'unavailable',
  observed_at timestamptz,
  retrieved_at timestamptz,
  evaluated_at timestamptz,
  triggered_at timestamptz,
  result jsonb not null default '{}'::jsonb check (jsonb_typeof(result) = 'object'),
  error_code text not null default '',
  duration_ms integer not null default 0 check (duration_ms between 0 and 300000),
  lkg_run_id text,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, schedule_id, due_window_at),
  unique (tenant_id, idempotency_key),
  unique (tenant_id, owner_user_id, scheduler_run_id),
  foreign key (tenant_id, owner_user_id, schedule_id)
    references public.global_terminal_hosted_observation_schedules(tenant_id, owner_user_id, schedule_id)
    on delete cascade
);

create table public.global_terminal_hosted_observation_schedule_audit (
  event_id text primary key check (char_length(event_id) between 8 and 80),
  tenant_id uuid not null references public.global_terminal_tenants(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  schedule_id text not null,
  scheduler_run_id text not null default '',
  event_type text not null check (char_length(event_type) between 1 and 64),
  prior_state text not null default '',
  new_state text not null default '',
  detail jsonb not null default '{}'::jsonb check (jsonb_typeof(detail) = 'object'),
  created_at timestamptz not null default now()
);

create index global_terminal_hosted_schedule_due_idx
  on public.global_terminal_hosted_observation_schedules (state, next_due_at, updated_at);
create index global_terminal_hosted_schedule_owner_idx
  on public.global_terminal_hosted_observation_schedules (tenant_id, owner_user_id, updated_at desc);
create index global_terminal_hosted_schedule_run_status_idx
  on public.global_terminal_hosted_observation_schedule_runs (status, lease_expires_at, updated_at);
create index global_terminal_hosted_schedule_run_owner_idx
  on public.global_terminal_hosted_observation_schedule_runs (tenant_id, owner_user_id, created_at desc);
create index global_terminal_hosted_schedule_audit_owner_idx
  on public.global_terminal_hosted_observation_schedule_audit (tenant_id, owner_user_id, created_at desc);

alter table public.global_terminal_hosted_scheduler_control enable row level security;
alter table public.global_terminal_hosted_observation_schedules enable row level security;
alter table public.global_terminal_hosted_observation_schedule_runs enable row level security;
alter table public.global_terminal_hosted_observation_schedule_audit enable row level security;

revoke all on table public.global_terminal_hosted_scheduler_control from public, anon, authenticated;
revoke all on table public.global_terminal_hosted_observation_schedules from public, anon, authenticated;
revoke all on table public.global_terminal_hosted_observation_schedule_runs from public, anon, authenticated;
revoke all on table public.global_terminal_hosted_observation_schedule_audit from public, anon, authenticated;

grant select on table public.global_terminal_hosted_observation_schedules to authenticated;
grant select on table public.global_terminal_hosted_observation_schedule_runs to authenticated;
grant select on table public.global_terminal_hosted_observation_schedule_audit to authenticated;
grant all on table public.global_terminal_hosted_scheduler_control to service_role;
grant all on table public.global_terminal_hosted_observation_schedules to service_role;
grant all on table public.global_terminal_hosted_observation_schedule_runs to service_role;
grant all on table public.global_terminal_hosted_observation_schedule_audit to service_role;

create policy global_terminal_hosted_schedules_read
  on public.global_terminal_hosted_observation_schedules for select to authenticated
  using (
    owner_user_id = (select auth.uid())
    and exists (
      select 1 from public.global_terminal_tenant_memberships membership
      where membership.tenant_id = global_terminal_hosted_observation_schedules.tenant_id
        and membership.user_id = (select auth.uid())
    )
  );

create policy global_terminal_hosted_schedule_runs_read
  on public.global_terminal_hosted_observation_schedule_runs for select to authenticated
  using (
    owner_user_id = (select auth.uid())
    and exists (
      select 1 from public.global_terminal_tenant_memberships membership
      where membership.tenant_id = global_terminal_hosted_observation_schedule_runs.tenant_id
        and membership.user_id = (select auth.uid())
    )
  );

create policy global_terminal_hosted_schedule_audit_read
  on public.global_terminal_hosted_observation_schedule_audit for select to authenticated
  using (
    owner_user_id = (select auth.uid())
    and exists (
      select 1 from public.global_terminal_tenant_memberships membership
      where membership.tenant_id = global_terminal_hosted_observation_schedule_audit.tenant_id
        and membership.user_id = (select auth.uid())
    )
  );

create or replace function public.global_terminal_phase6q_next_due(
  p_due timestamptz,
  p_cadence_minutes integer,
  p_timezone text,
  p_after timestamptz default now()
) returns timestamptz
language plpgsql
stable
set search_path = ''
as $$
declare
  candidate timestamptz;
begin
  if p_cadence_minutes = 1440 then
    candidate := ((p_due at time zone p_timezone) + interval '1 day') at time zone p_timezone;
  else
    candidate := p_due + make_interval(mins => p_cadence_minutes);
  end if;
  while candidate <= p_after loop
    if p_cadence_minutes = 1440 then
      candidate := ((candidate at time zone p_timezone) + interval '1 day') at time zone p_timezone;
    else
      candidate := candidate + make_interval(mins => p_cadence_minutes);
    end if;
  end loop;
  return candidate;
end;
$$;

revoke all on function public.global_terminal_phase6q_next_due(timestamptz, integer, text, timestamptz)
from public, anon, authenticated;

create or replace function public.global_terminal_apply_hosted_observation_schedule(
  p_schedule jsonb,
  p_expected_version integer
) returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  current_user_id uuid := auth.uid();
  current_tenant_id uuid;
  account_document public.global_terminal_account_documents%rowtype;
  current_schedule public.global_terminal_hosted_observation_schedules%rowtype;
  target_state text := coalesce(p_schedule->>'state', '');
  target_id text := coalesce(p_schedule->>'schedule_id', '');
  target_watchlist text := coalesce(p_schedule->>'watchlist_id', '');
  target_rule text := coalesce(p_schedule->>'alert_rule_id', '');
  target_version integer := coalesce((p_schedule->>'version')::integer, 0);
  v_now timestamptz := now();
begin
  if current_user_id is null then
    raise insufficient_privilege using message = 'authenticated user required';
  end if;
  if p_schedule ?| array['tenant_id','owner_user_id','user_id','lease_token','lease_owner'] then
    raise data_exception using message = 'schedule identity and lease scope are server-derived';
  end if;
  if target_id !~ '^[a-zA-Z0-9][a-zA-Z0-9_.:-]{7,79}$'
     or target_watchlist !~ '^[a-zA-Z0-9][a-zA-Z0-9_.:-]{2,79}$'
     or target_rule !~ '^[a-zA-Z0-9][a-zA-Z0-9_.:-]{2,79}$'
     or target_state not in ('disabled','enabled','paused','killed','deleted')
     or target_version < 1 then
    raise data_exception using message = 'invalid hosted schedule payload';
  end if;

  select membership.tenant_id into current_tenant_id
  from public.global_terminal_tenant_memberships membership
  where membership.user_id = current_user_id
    and membership.role in ('owner','member')
  order by membership.created_at, membership.tenant_id
  limit 1;
  if current_tenant_id is null then
    raise insufficient_privilege using message = 'tenant membership required';
  end if;

  select document.* into account_document
  from public.global_terminal_account_documents document
  where document.tenant_id = current_tenant_id
    and document.owner_user_id = current_user_id
    and document.document_key = 'research-continuity'
    and document.deleted = false
  limit 1;
  if account_document.document_id is null then
    raise foreign_key_violation using message = 'active account document required';
  end if;
  if not exists (
    select 1 from jsonb_array_elements(coalesce(account_document.payload #> '{tables,tenant_watchlists}', '[]'::jsonb)) row
    where row->>'resource_id' = target_watchlist
  ) or not exists (
    select 1 from jsonb_array_elements(coalesce(account_document.payload #> '{tables,tenant_watchlist_alert_rules}', '[]'::jsonb)) row
    where row->>'resource_id' = target_rule and row->>'watchlist_resource_id' = target_watchlist
  ) then
    raise foreign_key_violation using message = 'schedule parent is absent from the account document';
  end if;

  select schedule.* into current_schedule
  from public.global_terminal_hosted_observation_schedules schedule
  where schedule.tenant_id = current_tenant_id
    and schedule.owner_user_id = current_user_id
    and schedule.schedule_id = target_id
  for update;

  if current_schedule.schedule_id is null then
    if p_expected_version <> 0 or target_version <> 1 or target_state <> 'disabled' then
      return jsonb_build_object('status','conflict','current_version',0);
    end if;
    insert into public.global_terminal_hosted_observation_schedules (
      schedule_id, tenant_id, owner_user_id, account_document_id, account_document_version,
      watchlist_resource_id, alert_rule_resource_id, state, timezone, cadence_minutes,
      max_symbols, max_provider_calls, max_attempts, timeout_seconds, next_due_at,
      consented_at, enabled_at, paused_at, killed_at, deleted_at, version, created_at, updated_at
    ) values (
      target_id, current_tenant_id, current_user_id, account_document.document_id, account_document.version,
      target_watchlist, target_rule, 'disabled', coalesce(p_schedule->>'timezone','UTC'),
      coalesce((p_schedule->>'cadence_minutes')::integer,60),
      coalesce((p_schedule #>> '{bounds,max_symbols}')::integer,1),
      coalesce((p_schedule #>> '{bounds,max_provider_calls}')::integer,4),
      coalesce((p_schedule #>> '{bounds,max_attempts}')::integer,2),
      coalesce((p_schedule #>> '{bounds,timeout_seconds}')::integer,90),
      null, null, null, null, null, null, 1, v_now, v_now
    );
    return jsonb_build_object('status','applied','version',1,'state','disabled');
  end if;

  if current_schedule.version <> p_expected_version or target_version <> current_schedule.version + 1 then
    return jsonb_build_object('status','conflict','current_version',current_schedule.version);
  end if;
  if not (
    (current_schedule.state = 'disabled' and target_state in ('enabled','killed','deleted'))
    or (current_schedule.state = 'enabled' and target_state in ('enabled','paused','killed'))
    or (current_schedule.state = 'paused' and target_state in ('enabled','killed','deleted'))
    or (current_schedule.state = 'killed' and target_state in ('paused','deleted'))
  ) then
    raise check_violation using message = 'invalid hosted schedule transition';
  end if;
  if target_state in ('enabled','paused') and nullif(p_schedule->>'consented_at','') is null then
    raise check_violation using message = 'explicit schedule consent required';
  end if;

  update public.global_terminal_hosted_observation_schedules schedule
  set account_document_id = account_document.document_id,
      account_document_version = account_document.version,
      state = target_state,
      timezone = coalesce(p_schedule->>'timezone', schedule.timezone),
      cadence_minutes = coalesce((p_schedule->>'cadence_minutes')::integer, schedule.cadence_minutes),
      max_symbols = coalesce((p_schedule #>> '{bounds,max_symbols}')::integer, schedule.max_symbols),
      max_provider_calls = coalesce((p_schedule #>> '{bounds,max_provider_calls}')::integer, schedule.max_provider_calls),
      max_attempts = coalesce((p_schedule #>> '{bounds,max_attempts}')::integer, schedule.max_attempts),
      timeout_seconds = coalesce((p_schedule #>> '{bounds,timeout_seconds}')::integer, schedule.timeout_seconds),
      next_due_at = nullif(p_schedule->>'next_due_at','')::timestamptz,
      consented_at = coalesce(nullif(p_schedule->>'consented_at','')::timestamptz, schedule.consented_at),
      enabled_at = coalesce(nullif(p_schedule->>'enabled_at','')::timestamptz, schedule.enabled_at),
      paused_at = coalesce(nullif(p_schedule->>'paused_at','')::timestamptz, schedule.paused_at),
      killed_at = coalesce(nullif(p_schedule->>'killed_at','')::timestamptz, schedule.killed_at),
      deleted_at = coalesce(nullif(p_schedule->>'deleted_at','')::timestamptz, schedule.deleted_at),
      version = target_version,
      updated_at = v_now
  where schedule.schedule_id = target_id;
  return jsonb_build_object('status','applied','version',target_version,'state',target_state);
end;
$$;

revoke all on function public.global_terminal_apply_hosted_observation_schedule(jsonb, integer)
from public, anon;
grant execute on function public.global_terminal_apply_hosted_observation_schedule(jsonb, integer)
to authenticated;

create or replace function public.global_terminal_claim_hosted_observation_schedule(
  p_worker_hash text,
  p_lease_token_hash text,
  p_lease_seconds integer default 120
) returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  control public.global_terminal_hosted_scheduler_control%rowtype;
  schedule public.global_terminal_hosted_observation_schedules%rowtype;
  run public.global_terminal_hosted_observation_schedule_runs%rowtype;
  v_now timestamptz := now();
  run_id text;
  attempt integer;
  bounded_lease integer := greatest(30, least(coalesce(p_lease_seconds,120),300));
begin
  if auth.role() <> 'service_role' then raise insufficient_privilege; end if;
  if p_worker_hash !~ '^[a-f0-9]{64}$' or p_lease_token_hash !~ '^[a-f0-9]{64}$' then
    raise data_exception using message = 'invalid worker lease proof';
  end if;
  select * into control from public.global_terminal_hosted_scheduler_control where singleton = true;
  if not coalesce(control.operator_enabled,false) then
    return jsonb_build_object('claimed',false,'status','disabled','reason','operator-gate-disabled','provider_call_count',0);
  end if;
  if coalesce(control.global_kill_switch,true) then
    return jsonb_build_object('claimed',false,'status','killed','reason','global-kill-switch','provider_call_count',0);
  end if;

  select candidate.* into schedule
  from public.global_terminal_hosted_observation_schedules candidate
  where candidate.state = 'enabled' and candidate.next_due_at is not null and candidate.next_due_at <= v_now
  order by candidate.next_due_at, candidate.schedule_id
  for update skip locked
  limit 1;
  if schedule.schedule_id is null then
    return jsonb_build_object('claimed',false,'status','no-due','reason','no-enabled-due-schedule','provider_call_count',0);
  end if;

  select candidate.* into run
  from public.global_terminal_hosted_observation_schedule_runs candidate
  where candidate.tenant_id = schedule.tenant_id
    and candidate.schedule_id = schedule.schedule_id
    and candidate.due_window_at = schedule.next_due_at
  for update;

  if run.scheduler_run_id is not null then
    if run.status in ('completed','partial','quota-blocked','provider-unavailable','cancelled','killed','failed') then
      return jsonb_build_object('claimed',false,'status',run.status,'reason','idempotent-window-complete','idempotent_replay',true,'provider_call_count',0);
    end if;
    if run.lease_expires_at > v_now then
      return jsonb_build_object('claimed',false,'status','overlap','reason','lease-active','provider_call_count',0);
    end if;
    if run.attempt_count >= schedule.max_attempts then
      update public.global_terminal_hosted_observation_schedule_runs
      set status='failed', error_code='lease-attempts-exhausted', completed_at=v_now, updated_at=v_now
      where scheduler_run_id=run.scheduler_run_id;
      update public.global_terminal_hosted_observation_schedules
      set next_due_at=public.global_terminal_phase6q_next_due(schedule.next_due_at,schedule.cadence_minutes,schedule.timezone,v_now),
          last_attempted_at=v_now,last_run_id=run.scheduler_run_id,updated_at=v_now
      where schedule_id=schedule.schedule_id;
      return jsonb_build_object('claimed',false,'status','failed','reason','lease-attempts-exhausted','provider_call_count',0);
    end if;
    run_id := run.scheduler_run_id;
    attempt := run.attempt_count + 1;
    update public.global_terminal_hosted_observation_schedule_runs
    set status='leased',lease_owner_hash=p_worker_hash,lease_token_hash=p_lease_token_hash,
        lease_acquired_at=v_now,lease_expires_at=v_now+make_interval(secs=>bounded_lease),
        heartbeat_at=v_now,attempt_count=attempt,error_code='',updated_at=v_now
    where scheduler_run_id=run_id;
  else
    run_id := 'hsrun_' || replace(gen_random_uuid()::text,'-','');
    attempt := 1;
    insert into public.global_terminal_hosted_observation_schedule_runs (
      scheduler_run_id,tenant_id,owner_user_id,schedule_id,due_window_at,idempotency_key,status,
      lease_owner_hash,lease_token_hash,lease_acquired_at,lease_expires_at,heartbeat_at,attempt_count,
      provider_call_budget,created_at,updated_at
    ) values (
      run_id,schedule.tenant_id,schedule.owner_user_id,schedule.schedule_id,schedule.next_due_at,
      'hosted-schedule-' || md5(schedule.schedule_id || ':' || schedule.next_due_at::text),
      'leased',p_worker_hash,p_lease_token_hash,v_now,v_now+make_interval(secs=>bounded_lease),
      v_now,1,schedule.max_provider_calls,v_now,v_now
    );
  end if;
  update public.global_terminal_hosted_observation_schedules
  set last_attempted_at=v_now,last_run_id=run_id,updated_at=v_now
  where schedule_id=schedule.schedule_id;
  return jsonb_build_object(
    'claimed',true,'status','leased','scheduler_run_id',run_id,'schedule_id',schedule.schedule_id,
    'tenant_id',schedule.tenant_id,'owner_user_id',schedule.owner_user_id,
    'account_document_id',schedule.account_document_id,'account_document_version',schedule.account_document_version,
    'watchlist_id',schedule.watchlist_resource_id,'alert_rule_id',schedule.alert_rule_resource_id,
    'due_window_at',schedule.next_due_at,'lease_expires_at',v_now+make_interval(secs=>bounded_lease),
    'attempt_count',attempt,'bounds',jsonb_build_object('max_symbols',schedule.max_symbols,'max_provider_calls',schedule.max_provider_calls,'max_attempts',schedule.max_attempts,'timeout_seconds',schedule.timeout_seconds),
    'provider_call_count',0
  );
end;
$$;

revoke all on function public.global_terminal_claim_hosted_observation_schedule(text, text, integer)
from public, anon, authenticated;
grant execute on function public.global_terminal_claim_hosted_observation_schedule(text, text, integer)
to service_role;

create or replace function public.global_terminal_heartbeat_hosted_observation_schedule(
  p_scheduler_run_id text,
  p_lease_token_hash text,
  p_lease_seconds integer default 120
) returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  run public.global_terminal_hosted_observation_schedule_runs%rowtype;
  v_now timestamptz := now();
  bounded_lease integer := greatest(30, least(coalesce(p_lease_seconds,120),300));
begin
  if auth.role() <> 'service_role' then raise insufficient_privilege; end if;
  select candidate.* into run from public.global_terminal_hosted_observation_schedule_runs candidate
  where candidate.scheduler_run_id=p_scheduler_run_id for update;
  if run.scheduler_run_id is null then raise no_data_found; end if;
  if run.status not in ('leased','running') or run.lease_token_hash <> p_lease_token_hash or run.lease_expires_at <= v_now then
    raise insufficient_privilege using message='scheduler lease expired or invalid';
  end if;
  update public.global_terminal_hosted_observation_schedule_runs
  set status='running',heartbeat_at=v_now,
      lease_expires_at=v_now+make_interval(secs=>bounded_lease),updated_at=v_now
  where scheduler_run_id=run.scheduler_run_id;
  return jsonb_build_object('status','running','scheduler_run_id',run.scheduler_run_id,'heartbeat_at',v_now,'lease_expires_at',v_now+make_interval(secs=>bounded_lease),'provider_call_count',0);
end;
$$;

revoke all on function public.global_terminal_heartbeat_hosted_observation_schedule(text, text, integer)
from public, anon, authenticated;
grant execute on function public.global_terminal_heartbeat_hosted_observation_schedule(text, text, integer)
to service_role;

create or replace function public.global_terminal_apply_scheduler_account_document(
  p_scheduler_run_id text,
  p_lease_token_hash text,
  p_payload jsonb,
  p_document_fingerprint text,
  p_expected_version integer,
  p_idempotency_key text
) returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  run public.global_terminal_hosted_observation_schedule_runs%rowtype;
  schedule public.global_terminal_hosted_observation_schedules%rowtype;
  document public.global_terminal_account_documents%rowtype;
  receipt public.global_terminal_account_document_receipts%rowtype;
  v_now timestamptz := now();
  next_version integer;
begin
  if auth.role() <> 'service_role' then raise insufficient_privilege; end if;
  if jsonb_typeof(p_payload) <> 'object' or octet_length(p_payload::text) > 512000
     or p_document_fingerprint !~ '^[a-f0-9]{64}$'
     or p_idempotency_key !~ '^[a-zA-Z0-9][a-zA-Z0-9._:-]{7,127}$' then
    raise data_exception using message='invalid bounded account document payload';
  end if;
  select candidate.* into run from public.global_terminal_hosted_observation_schedule_runs candidate
  where candidate.scheduler_run_id=p_scheduler_run_id for update;
  if run.scheduler_run_id is null or run.status not in ('leased','running')
     or run.lease_token_hash <> p_lease_token_hash or run.lease_expires_at <= v_now then
    raise insufficient_privilege using message='scheduler lease expired or invalid';
  end if;
  select candidate.* into schedule from public.global_terminal_hosted_observation_schedules candidate
  where candidate.schedule_id=run.schedule_id for update;
  select candidate.* into document from public.global_terminal_account_documents candidate
  where candidate.document_id=schedule.account_document_id
    and candidate.tenant_id=run.tenant_id and candidate.owner_user_id=run.owner_user_id
    and candidate.deleted=false for update;
  if document.document_id is null then raise foreign_key_violation using message='active account document required'; end if;
  select candidate.* into receipt from public.global_terminal_account_document_receipts candidate
  where candidate.tenant_id=run.tenant_id and candidate.owner_user_id=run.owner_user_id
    and candidate.idempotency_key=p_idempotency_key;
  if receipt.receipt_id is not null then
    return jsonb_build_object('status','deduped','version',receipt.result_version,'document_fingerprint',p_document_fingerprint);
  end if;
  if document.version <> p_expected_version or schedule.account_document_version <> p_expected_version then
    return jsonb_build_object('status','conflict','current_version',document.version);
  end if;
  next_version := document.version + 1;
  update public.global_terminal_account_documents
  set payload=p_payload,document_fingerprint=p_document_fingerprint,version=next_version,updated_at=v_now
  where document_id=document.document_id;
  insert into public.global_terminal_account_document_receipts (
    receipt_id,tenant_id,owner_user_id,document_id,idempotency_key,operation,request_fingerprint,
    result_version,result_status,created_at
  ) values (
    'acreceipt_' || replace(gen_random_uuid()::text,'-',''),run.tenant_id,run.owner_user_id,document.document_id,
    p_idempotency_key,'apply',md5(p_idempotency_key || ':' || p_document_fingerprint) || md5(p_document_fingerprint || ':' || p_idempotency_key),
    next_version,'applied',v_now
  );
  insert into public.global_terminal_account_document_audit (
    event_id,tenant_id,owner_user_id,document_id,document_key,event_type,prior_version,new_version,
    prior_fingerprint,new_fingerprint,created_at
  ) values (
    'acaudit_' || replace(gen_random_uuid()::text,'-',''),run.tenant_id,run.owner_user_id,document.document_id,
    document.document_key,'document-updated',document.version,next_version,document.document_fingerprint,p_document_fingerprint,v_now
  );
  update public.global_terminal_hosted_observation_schedules
  set account_document_version=next_version,updated_at=v_now where schedule_id=schedule.schedule_id;
  return jsonb_build_object('status','applied','version',next_version,'document_fingerprint',p_document_fingerprint);
end;
$$;

revoke all on function public.global_terminal_apply_scheduler_account_document(text, text, jsonb, text, integer, text)
from public, anon, authenticated;
grant execute on function public.global_terminal_apply_scheduler_account_document(text, text, jsonb, text, integer, text)
to service_role;

create or replace function public.global_terminal_finish_hosted_observation_schedule(
  p_scheduler_run_id text,
  p_lease_token_hash text,
  p_result jsonb
) returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  run public.global_terminal_hosted_observation_schedule_runs%rowtype;
  schedule public.global_terminal_hosted_observation_schedules%rowtype;
  v_now timestamptz := now();
  final_status text := coalesce(p_result->>'status','failed');
  calls integer := coalesce((p_result->>'provider_call_count')::integer,0);
  valid_lkg boolean;
  next_due timestamptz;
begin
  if auth.role() <> 'service_role' then raise insufficient_privilege; end if;
  select candidate.* into run from public.global_terminal_hosted_observation_schedule_runs candidate
  where candidate.scheduler_run_id=p_scheduler_run_id for update;
  if run.scheduler_run_id is null then raise no_data_found; end if;
  if run.status in ('completed','partial','quota-blocked','provider-unavailable','cancelled','killed','failed') then
    return jsonb_build_object('status',run.status,'scheduler_run_id',run.scheduler_run_id,'idempotent_replay',true,'provider_call_count',run.provider_call_count);
  end if;
  if run.lease_token_hash <> p_lease_token_hash or run.lease_expires_at <= v_now then
    raise insufficient_privilege using message='scheduler lease expired or invalid';
  end if;
  if final_status not in ('completed','partial','quota-blocked','provider-unavailable','cancelled','killed','failed')
     or calls < 0 or calls > run.provider_call_budget then
    raise check_violation using message='invalid terminal scheduler result';
  end if;
  select candidate.* into schedule from public.global_terminal_hosted_observation_schedules candidate
  where candidate.schedule_id=run.schedule_id for update;
  if schedule.state='killed' then final_status := 'killed'; end if;
  valid_lkg := final_status in ('completed','partial') and coalesce(p_result->>'source_status','unavailable') not in ('','unavailable','provider-error','malformed');
  if schedule.state='enabled' then
    next_due := public.global_terminal_phase6q_next_due(run.due_window_at,schedule.cadence_minutes,schedule.timezone,v_now);
  end if;
  update public.global_terminal_hosted_observation_schedule_runs
  set status=final_status,lease_owner_hash='',lease_token_hash='',heartbeat_at=v_now,
      observation_run_id=nullif(p_result->>'observation_run_id',''),evaluation_run_id=nullif(p_result->>'evaluation_run_id',''),
      trigger_count=greatest(0,least(coalesce((p_result->>'trigger_count')::integer,0),50)),provider_call_count=calls,
      provider=left(coalesce(p_result->>'provider',''),80),source_url=left(coalesce(p_result->>'source_url',''),2000),
      source_status=left(coalesce(p_result->>'source_status','unavailable'),64),
      observed_at=nullif(p_result->>'observed_at','')::timestamptz,retrieved_at=nullif(p_result->>'retrieved_at','')::timestamptz,
      evaluated_at=nullif(p_result->>'evaluated_at','')::timestamptz,triggered_at=nullif(p_result->>'triggered_at','')::timestamptz,
      result=jsonb_build_object('status',final_status,'caveat',left(coalesce(p_result->>'caveat',''),1000),'data_gap',left(coalesce(p_result->>'data_gap',''),1000),'duplicate_suppressed',coalesce((p_result->>'duplicate_suppressed')::boolean,false)),
      error_code=left(coalesce(p_result->>'error_code',''),80),duration_ms=greatest(0,least(coalesce((p_result->>'duration_ms')::integer,0),300000)),
      lkg_run_id=case when valid_lkg then run.scheduler_run_id else schedule.last_lkg_run_id end,
      completed_at=v_now,updated_at=v_now
  where scheduler_run_id=run.scheduler_run_id;
  update public.global_terminal_hosted_observation_schedules
  set next_due_at=next_due,last_attempted_at=v_now,
      last_completed_at=case when final_status in ('completed','partial') then v_now else last_completed_at end,
      last_run_id=run.scheduler_run_id,last_lkg_run_id=case when valid_lkg then run.scheduler_run_id else last_lkg_run_id end,
      updated_at=v_now
  where schedule_id=schedule.schedule_id;
  return jsonb_build_object('status',final_status,'scheduler_run_id',run.scheduler_run_id,'idempotent_replay',false,'provider_call_count',calls,'trigger_count',coalesce((p_result->>'trigger_count')::integer,0),'next_due_at',next_due);
end;
$$;

revoke all on function public.global_terminal_finish_hosted_observation_schedule(text, text, jsonb)
from public, anon, authenticated;
grant execute on function public.global_terminal_finish_hosted_observation_schedule(text, text, jsonb)
to service_role;

create or replace function public.global_terminal_record_hosted_scheduler_audit()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  row_json jsonb := case when tg_op='DELETE' then to_jsonb(old) else to_jsonb(new) end;
  prior_json jsonb := case when tg_op='INSERT' then '{}'::jsonb else to_jsonb(old) end;
  schedule_key text;
  run_key text;
  prior_value text;
  next_value text;
begin
  schedule_key := coalesce(row_json->>'schedule_id','');
  run_key := case when tg_table_name='global_terminal_hosted_observation_schedule_runs' then coalesce(row_json->>'scheduler_run_id','') else '' end;
  prior_value := coalesce(prior_json->>'state',prior_json->>'status','');
  next_value := case when tg_op='DELETE' then '' else coalesce(row_json->>'state',row_json->>'status','') end;
  insert into public.global_terminal_hosted_observation_schedule_audit (
    event_id,tenant_id,owner_user_id,schedule_id,scheduler_run_id,event_type,prior_state,new_state,detail,created_at
  ) values (
    'hsaudit_' || replace(gen_random_uuid()::text,'-',''),(row_json->>'tenant_id')::uuid,(row_json->>'owner_user_id')::uuid,
    schedule_key,run_key,case when run_key='' then 'schedule-' else 'run-' end || lower(tg_op),prior_value,next_value,
    jsonb_build_object('operation',lower(tg_op),'version',coalesce((row_json->>'version')::integer,1),'attempt_count',coalesce((row_json->>'attempt_count')::integer,0)),now()
  );
  if tg_op='DELETE' then return old; end if;
  return new;
end;
$$;

revoke all on function public.global_terminal_record_hosted_scheduler_audit()
from public, anon, authenticated;

create trigger global_terminal_hosted_schedule_audit_trigger
after insert or update or delete on public.global_terminal_hosted_observation_schedules
for each row execute function public.global_terminal_record_hosted_scheduler_audit();
create trigger global_terminal_hosted_schedule_run_audit_trigger
after insert or update or delete on public.global_terminal_hosted_observation_schedule_runs
for each row execute function public.global_terminal_record_hosted_scheduler_audit();

commit;
