-- Phase 6J hosted persistence boundary (migration version 20260710105056).
-- Apply only after an explicit Supabase project/security review.

create table if not exists public.global_terminal_tenants (
  id uuid primary key default gen_random_uuid(),
  name text not null check (char_length(name) between 1 and 120),
  created_at timestamptz not null default now()
);

create table if not exists public.global_terminal_tenant_memberships (
  tenant_id uuid not null references public.global_terminal_tenants(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('owner', 'member', 'viewer')),
  created_at timestamptz not null default now(),
  primary key (tenant_id, user_id)
);

create table if not exists public.global_terminal_workspace_preferences (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.global_terminal_tenants(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  preference_key text not null check (preference_key ~ '^[a-z][a-z0-9-]{0,63}$'),
  value jsonb not null default '{}'::jsonb,
  version integer not null default 1 check (version > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, preference_key)
);

alter table public.global_terminal_tenants enable row level security;
alter table public.global_terminal_tenant_memberships enable row level security;
alter table public.global_terminal_workspace_preferences enable row level security;

create policy "members can read their tenant"
on public.global_terminal_tenants for select to authenticated
using (
  exists (
    select 1 from public.global_terminal_tenant_memberships m
    where m.tenant_id = id and m.user_id = (select auth.uid())
  )
);

create policy "members can read their membership"
on public.global_terminal_tenant_memberships for select to authenticated
using (user_id = (select auth.uid()));

create policy "members can read tenant preferences"
on public.global_terminal_workspace_preferences for select to authenticated
using (
  exists (
    select 1 from public.global_terminal_tenant_memberships m
    where m.tenant_id = tenant_id and m.user_id = (select auth.uid())
  )
);

create policy "owners can insert tenant preferences"
on public.global_terminal_workspace_preferences for insert to authenticated
with check (
  owner_user_id = (select auth.uid())
  and exists (
    select 1 from public.global_terminal_tenant_memberships m
    where m.tenant_id = tenant_id
      and m.user_id = (select auth.uid())
      and m.role in ('owner', 'member')
  )
);

create policy "owners can update tenant preferences"
on public.global_terminal_workspace_preferences for update to authenticated
using (
  exists (
    select 1 from public.global_terminal_tenant_memberships m
    where m.tenant_id = tenant_id
      and m.user_id = (select auth.uid())
      and m.role in ('owner', 'member')
  )
)
with check (owner_user_id = (select auth.uid()));

create policy "owners can delete tenant preferences"
on public.global_terminal_workspace_preferences for delete to authenticated
using (
  exists (
    select 1 from public.global_terminal_tenant_memberships m
    where m.tenant_id = tenant_id
      and m.user_id = (select auth.uid())
      and m.role in ('owner', 'member')
  )
);
