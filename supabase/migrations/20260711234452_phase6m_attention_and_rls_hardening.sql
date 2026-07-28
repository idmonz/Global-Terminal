-- Phase 6M hardening (migration version 20260711234452) fixes tenant policy and adds
-- tenant-private Attention review metadata. This migration stores no market
-- provider payload and does not enable hosted success by itself.

drop policy if exists "members can read tenant preferences"
  on public.global_terminal_workspace_preferences;
drop policy if exists "owners can insert tenant preferences"
  on public.global_terminal_workspace_preferences;
drop policy if exists "owners can update tenant preferences"
  on public.global_terminal_workspace_preferences;
drop policy if exists "owners can delete tenant preferences"
  on public.global_terminal_workspace_preferences;

create policy "members can read tenant preferences"
on public.global_terminal_workspace_preferences for select to authenticated
using (
  exists (
    select 1 from public.global_terminal_tenant_memberships m
    where m.tenant_id = global_terminal_workspace_preferences.tenant_id
      and m.user_id = (select auth.uid())
  )
);

create policy "owners can insert tenant preferences"
on public.global_terminal_workspace_preferences for insert to authenticated
with check (
  owner_user_id = (select auth.uid())
  and exists (
    select 1 from public.global_terminal_tenant_memberships m
    where m.tenant_id = global_terminal_workspace_preferences.tenant_id
      and m.user_id = (select auth.uid())
      and m.role in ('owner', 'member')
  )
);

create policy "owners can update tenant preferences"
on public.global_terminal_workspace_preferences for update to authenticated
using (
  exists (
    select 1 from public.global_terminal_tenant_memberships m
    where m.tenant_id = global_terminal_workspace_preferences.tenant_id
      and m.user_id = (select auth.uid())
      and m.role in ('owner', 'member')
  )
)
with check (
  owner_user_id = (select auth.uid())
  and exists (
    select 1 from public.global_terminal_tenant_memberships m
    where m.tenant_id = global_terminal_workspace_preferences.tenant_id
      and m.user_id = (select auth.uid())
      and m.role in ('owner', 'member')
  )
);

create policy "owners can delete tenant preferences"
on public.global_terminal_workspace_preferences for delete to authenticated
using (
  exists (
    select 1 from public.global_terminal_tenant_memberships m
    where m.tenant_id = global_terminal_workspace_preferences.tenant_id
      and m.user_id = (select auth.uid())
      and m.role in ('owner', 'member')
  )
);

create or replace function public.global_terminal_bootstrap_personal_tenant(
  requested_name text default 'Personal research'
) returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  current_user_id uuid := (select auth.uid());
  existing_tenant_id uuid;
  created_tenant_id uuid;
  safe_name text := left(coalesce(nullif(btrim(requested_name), ''), 'Personal research'), 120);
begin
  if current_user_id is null then
    raise exception 'authenticated user required';
  end if;

  perform pg_catalog.pg_advisory_xact_lock(
    pg_catalog.hashtextextended(current_user_id::text, 0)
  );

  select membership.tenant_id
    into existing_tenant_id
    from public.global_terminal_tenant_memberships membership
   where membership.user_id = current_user_id
   order by membership.created_at, membership.tenant_id
   limit 1;

  if existing_tenant_id is not null then
    return existing_tenant_id;
  end if;

  insert into public.global_terminal_tenants (name)
  values (safe_name)
  returning id into created_tenant_id;

  insert into public.global_terminal_tenant_memberships (tenant_id, user_id, role)
  values (created_tenant_id, current_user_id, 'owner');

  return created_tenant_id;
end;
$$;

revoke all on function public.global_terminal_bootstrap_personal_tenant(text) from public, anon;
grant execute on function public.global_terminal_bootstrap_personal_tenant(text) to authenticated;

create table if not exists public.global_terminal_attention_states (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.global_terminal_tenants(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  fingerprint text not null check (fingerprint ~ '^[0-9a-f]{64}$'),
  review_state text not null default 'new' check (review_state in ('new', 'reviewed', 'acknowledged', 'snoozed')),
  prior_state text not null default 'new' check (prior_state in ('new', 'reviewed', 'acknowledged')),
  snoozed_until timestamptz,
  reviewed_at timestamptz,
  acknowledged_at timestamptz,
  version integer not null default 1 check (version > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, fingerprint),
  unique (tenant_id, id)
);

create table if not exists public.global_terminal_attention_policies (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.global_terminal_tenants(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  minimum_severity text not null default 'material' check (minimum_severity in ('info', 'material', 'high', 'critical')),
  included_change_kinds jsonb not null default '["market-change","new-evidence","source-degradation","stale-evidence","resolved"]'::jsonb,
  source_health_handling text not null default 'include' check (source_health_handling in ('include', 'deprioritize', 'hide')),
  version integer not null default 1 check (version > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id),
  unique (tenant_id, id)
);

create table if not exists public.global_terminal_attention_checkpoints (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.global_terminal_tenants(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  reviewed_through_at timestamptz not null,
  version integer not null default 1 check (version > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id),
  unique (tenant_id, id)
);

create table if not exists public.global_terminal_attention_audit (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.global_terminal_tenants(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  event_type text not null check (char_length(event_type) between 1 and 48),
  status text not null check (char_length(status) between 1 and 32),
  fingerprint text not null default '' check (fingerprint = '' or fingerprint ~ '^[0-9a-f]{64}$'),
  created_at timestamptz not null default now(),
  unique (tenant_id, id)
);

create index if not exists global_terminal_attention_state_idx
  on public.global_terminal_attention_states (tenant_id, review_state, updated_at desc);
create index if not exists global_terminal_attention_snooze_idx
  on public.global_terminal_attention_states (tenant_id, snoozed_until);
create index if not exists global_terminal_attention_audit_idx
  on public.global_terminal_attention_audit (tenant_id, created_at desc);

alter table public.global_terminal_attention_states enable row level security;
alter table public.global_terminal_attention_policies enable row level security;
alter table public.global_terminal_attention_checkpoints enable row level security;
alter table public.global_terminal_attention_audit enable row level security;

revoke all on table public.global_terminal_attention_states from anon;
revoke all on table public.global_terminal_attention_policies from anon;
revoke all on table public.global_terminal_attention_checkpoints from anon;
revoke all on table public.global_terminal_attention_audit from anon;
grant select, insert, update, delete on table public.global_terminal_attention_states to authenticated;
grant select, insert, update, delete on table public.global_terminal_attention_policies to authenticated;
grant select, insert, update, delete on table public.global_terminal_attention_checkpoints to authenticated;
grant select, insert on table public.global_terminal_attention_audit to authenticated;

do $$
declare
  table_name text;
begin
  foreach table_name in array array[
    'global_terminal_attention_states',
    'global_terminal_attention_policies',
    'global_terminal_attention_checkpoints'
  ] loop
    execute format('drop policy if exists "tenant attention read" on public.%I', table_name);
    execute format(
      'create policy "tenant attention read" on public.%I for select to authenticated using (exists (select 1 from public.global_terminal_tenant_memberships membership where membership.tenant_id = %I.tenant_id and membership.user_id = (select auth.uid())))',
      table_name, table_name
    );
    execute format('drop policy if exists "tenant attention insert" on public.%I', table_name);
    execute format(
      'create policy "tenant attention insert" on public.%I for insert to authenticated with check (owner_user_id = (select auth.uid()) and exists (select 1 from public.global_terminal_tenant_memberships membership where membership.tenant_id = %I.tenant_id and membership.user_id = (select auth.uid()) and membership.role in (''owner'', ''member'')))',
      table_name, table_name
    );
    execute format('drop policy if exists "tenant attention update" on public.%I', table_name);
    execute format(
      'create policy "tenant attention update" on public.%I for update to authenticated using (owner_user_id = (select auth.uid()) and exists (select 1 from public.global_terminal_tenant_memberships membership where membership.tenant_id = %I.tenant_id and membership.user_id = (select auth.uid()))) with check (owner_user_id = (select auth.uid()) and exists (select 1 from public.global_terminal_tenant_memberships membership where membership.tenant_id = %I.tenant_id and membership.user_id = (select auth.uid()) and membership.role in (''owner'', ''member'')))',
      table_name, table_name, table_name
    );
    execute format('drop policy if exists "tenant attention delete" on public.%I', table_name);
    execute format(
      'create policy "tenant attention delete" on public.%I for delete to authenticated using (owner_user_id = (select auth.uid()) and exists (select 1 from public.global_terminal_tenant_memberships membership where membership.tenant_id = %I.tenant_id and membership.user_id = (select auth.uid()) and membership.role in (''owner'', ''member'')))',
      table_name, table_name
    );
  end loop;
end $$;

drop policy if exists "tenant attention audit read" on public.global_terminal_attention_audit;
create policy "tenant attention audit read"
on public.global_terminal_attention_audit for select to authenticated
using (
  owner_user_id = (select auth.uid())
  and exists (
    select 1 from public.global_terminal_tenant_memberships membership
    where membership.tenant_id = global_terminal_attention_audit.tenant_id
      and membership.user_id = (select auth.uid())
  )
);

drop policy if exists "tenant attention audit insert" on public.global_terminal_attention_audit;
create policy "tenant attention audit insert"
on public.global_terminal_attention_audit for insert to authenticated
with check (
  owner_user_id = (select auth.uid())
  and exists (
    select 1 from public.global_terminal_tenant_memberships membership
    where membership.tenant_id = global_terminal_attention_audit.tenant_id
      and membership.user_id = (select auth.uid())
      and membership.role in ('owner', 'member')
  )
);
