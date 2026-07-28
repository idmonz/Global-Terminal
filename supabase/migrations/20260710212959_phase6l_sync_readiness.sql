-- Phase 6L hosted synchronization readiness (migration version 20260710212959). Keep
-- `hosted_persistence=unavailable` until live auth, RLS A/B isolation, CRUD,
-- conflict, recovery, export, and deletion conformance passes.
--
-- Deliberately stores no synchronized payload. Account records remain in the
-- Phase 6K tenant tables; these rows only support bounded idempotency and
-- explicit deletion reconciliation.

create table if not exists public.global_terminal_sync_receipts (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.global_terminal_tenants(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  idempotency_key text not null check (char_length(idempotency_key) between 8 and 128),
  snapshot_fingerprint text not null check (char_length(snapshot_fingerprint) = 64),
  resource_count integer not null check (resource_count between 0 and 25),
  payload_bytes integer not null check (payload_bytes between 0 and 30000),
  result_status text not null check (result_status in ('applied', 'deduped', 'conflict', 'deleted')),
  remote_revision text not null default '',
  consented_at timestamptz not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, idempotency_key),
  unique (tenant_id, id)
);

create table if not exists public.global_terminal_deletion_tombstones (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.global_terminal_tenants(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  resource_type text not null check (resource_type in ('watchlist', 'watchlist-item', 'rule', 'inbox')),
  resource_id text not null check (char_length(resource_id) between 3 and 80),
  base_version integer not null check (base_version > 0),
  deletion_version integer not null check (deletion_version > base_version),
  deleted_at timestamptz not null default now(),
  retention_until timestamptz not null default (now() + interval '90 days'),
  unique (tenant_id, resource_type, resource_id),
  unique (tenant_id, id)
);

create index if not exists global_terminal_sync_receipts_tenant_created_idx
  on public.global_terminal_sync_receipts (tenant_id, created_at desc);
create index if not exists global_terminal_deletion_tombstones_tenant_retention_idx
  on public.global_terminal_deletion_tombstones (tenant_id, retention_until);

alter table public.global_terminal_sync_receipts enable row level security;
alter table public.global_terminal_deletion_tombstones enable row level security;

create policy "tenant members read" on public.global_terminal_sync_receipts
  for select to authenticated
  using (exists (
    select 1 from public.global_terminal_tenant_memberships membership
    where membership.tenant_id = global_terminal_sync_receipts.tenant_id
      and membership.user_id = (select auth.uid())
  ));
create policy "tenant owners insert" on public.global_terminal_sync_receipts
  for insert to authenticated
  with check (
    owner_user_id = (select auth.uid()) and exists (
      select 1 from public.global_terminal_tenant_memberships membership
      where membership.tenant_id = global_terminal_sync_receipts.tenant_id
        and membership.user_id = (select auth.uid())
        and membership.role in ('owner', 'member')
    )
  );
create policy "tenant owners update" on public.global_terminal_sync_receipts
  for update to authenticated
  using (owner_user_id = (select auth.uid()))
  with check (owner_user_id = (select auth.uid()));
create policy "tenant owners delete" on public.global_terminal_sync_receipts
  for delete to authenticated
  using (owner_user_id = (select auth.uid()));

create policy "tenant members read" on public.global_terminal_deletion_tombstones
  for select to authenticated
  using (exists (
    select 1 from public.global_terminal_tenant_memberships membership
    where membership.tenant_id = global_terminal_deletion_tombstones.tenant_id
      and membership.user_id = (select auth.uid())
  ));
create policy "tenant owners insert" on public.global_terminal_deletion_tombstones
  for insert to authenticated
  with check (
    owner_user_id = (select auth.uid()) and exists (
      select 1 from public.global_terminal_tenant_memberships membership
      where membership.tenant_id = global_terminal_deletion_tombstones.tenant_id
        and membership.user_id = (select auth.uid())
        and membership.role in ('owner', 'member')
    )
  );
create policy "tenant owners update" on public.global_terminal_deletion_tombstones
  for update to authenticated
  using (owner_user_id = (select auth.uid()))
  with check (owner_user_id = (select auth.uid()));
create policy "tenant owners delete" on public.global_terminal_deletion_tombstones
  for delete to authenticated
  using (owner_user_id = (select auth.uid()));
