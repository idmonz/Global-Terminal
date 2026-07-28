begin;

create table public.global_terminal_account_documents (
  document_id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references public.global_terminal_tenants(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  document_key text not null check (document_key ~ '^[a-z][a-z0-9-]{0,63}$'),
  payload jsonb not null default '{}'::jsonb check (jsonb_typeof(payload) = 'object'),
  document_fingerprint text not null check (document_fingerprint ~ '^[a-f0-9]{64}$'),
  version integer not null default 1 check (version > 0),
  deleted boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, owner_user_id, document_key),
  unique (tenant_id, owner_user_id, document_id),
  check (octet_length(payload::text) <= 512000)
);

create table public.global_terminal_account_document_receipts (
  receipt_id text primary key check (char_length(receipt_id) between 8 and 80),
  tenant_id uuid not null references public.global_terminal_tenants(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  document_id uuid not null,
  idempotency_key text not null check (char_length(idempotency_key) between 8 and 128),
  operation text not null check (operation in ('apply','delete')),
  request_fingerprint text not null check (request_fingerprint ~ '^[a-f0-9]{64}$'),
  result_version integer not null check (result_version > 0),
  result_status text not null check (result_status in ('applied','deleted')),
  created_at timestamptz not null default now(),
  unique (tenant_id, owner_user_id, idempotency_key),
  foreign key (tenant_id, owner_user_id, document_id)
    references public.global_terminal_account_documents(tenant_id, owner_user_id, document_id)
    on delete restrict
);

create table public.global_terminal_account_document_audit (
  event_id text primary key check (char_length(event_id) between 8 and 80),
  tenant_id uuid not null references public.global_terminal_tenants(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  document_id uuid not null,
  document_key text not null,
  event_type text not null check (event_type in ('document-created','document-updated','document-deleted')),
  prior_version integer not null default 0 check (prior_version >= 0),
  new_version integer not null check (new_version > 0),
  prior_fingerprint text not null default '',
  new_fingerprint text not null default '',
  created_at timestamptz not null default now()
);

create index global_terminal_account_documents_owner_idx
  on public.global_terminal_account_documents (tenant_id, owner_user_id, updated_at desc);
create index global_terminal_account_document_receipts_owner_idx
  on public.global_terminal_account_document_receipts (tenant_id, owner_user_id, created_at desc);
create index global_terminal_account_document_audit_owner_idx
  on public.global_terminal_account_document_audit (tenant_id, owner_user_id, created_at desc);

alter table public.global_terminal_account_documents enable row level security;
alter table public.global_terminal_account_document_receipts enable row level security;
alter table public.global_terminal_account_document_audit enable row level security;

revoke all on table public.global_terminal_account_documents from anon, authenticated;
revoke all on table public.global_terminal_account_document_receipts from anon, authenticated;
revoke all on table public.global_terminal_account_document_audit from anon, authenticated;

grant select on table public.global_terminal_account_documents to authenticated;
grant select on table public.global_terminal_account_document_receipts to authenticated;
grant select on table public.global_terminal_account_document_audit to authenticated;

create policy global_terminal_account_documents_read
  on public.global_terminal_account_documents for select to authenticated
  using (
    owner_user_id = (select auth.uid())
    and exists (
      select 1 from public.global_terminal_tenant_memberships membership
      where membership.tenant_id = global_terminal_account_documents.tenant_id
        and membership.user_id = (select auth.uid())
    )
  );

create policy global_terminal_account_document_receipts_read
  on public.global_terminal_account_document_receipts for select to authenticated
  using (
    owner_user_id = (select auth.uid())
    and exists (
      select 1 from public.global_terminal_tenant_memberships membership
      where membership.tenant_id = global_terminal_account_document_receipts.tenant_id
        and membership.user_id = (select auth.uid())
    )
  );

create policy global_terminal_account_document_audit_read
  on public.global_terminal_account_document_audit for select to authenticated
  using (
    owner_user_id = (select auth.uid())
    and exists (
      select 1 from public.global_terminal_tenant_memberships membership
      where membership.tenant_id = global_terminal_account_document_audit.tenant_id
        and membership.user_id = (select auth.uid())
    )
  );

create or replace function public.global_terminal_apply_account_document(
  p_document_key text,
  p_payload jsonb,
  p_document_fingerprint text,
  p_expected_version integer,
  p_idempotency_key text
)
returns table(status text, version integer, document_fingerprint text)
language plpgsql
security definer
set search_path = ''
as $$
declare
  current_user_id uuid := (select auth.uid());
  current_tenant_id uuid;
  current_document public.global_terminal_account_documents%rowtype;
  existing_receipt public.global_terminal_account_document_receipts%rowtype;
  next_document_id uuid;
  next_version integer;
  next_event text;
begin
  if current_user_id is null then
    raise exception 'authenticated-session-required' using errcode = '42501';
  end if;
  if p_document_key !~ '^[a-z][a-z0-9-]{0,63}$'
     or p_document_fingerprint !~ '^[a-f0-9]{64}$'
     or p_expected_version < 0
     or char_length(p_idempotency_key) not between 8 and 128
     or jsonb_typeof(p_payload) <> 'object'
     or octet_length(p_payload::text) > 512000
     or p_payload ? 'tenant_id'
     or p_payload ? 'owner_user_id'
     or p_payload ? 'user_id' then
    raise exception 'invalid-account-document' using errcode = '22023';
  end if;

  select membership.tenant_id
    into current_tenant_id
    from public.global_terminal_tenant_memberships membership
   where membership.user_id = current_user_id
     and membership.role in ('owner','member')
   order by membership.created_at, membership.tenant_id
   limit 1;
  if current_tenant_id is null then
    raise exception 'account-membership-required' using errcode = '42501';
  end if;

  select receipt.*
    into existing_receipt
    from public.global_terminal_account_document_receipts receipt
   where receipt.tenant_id = current_tenant_id
     and receipt.owner_user_id = current_user_id
     and receipt.idempotency_key = p_idempotency_key;
  if found then
    if existing_receipt.request_fingerprint <> p_document_fingerprint
       or existing_receipt.operation <> 'apply' then
      raise exception 'idempotency-key-reused' using errcode = '23505';
    end if;
    return query
      select 'deduped'::text,
             existing_receipt.result_version,
             document.document_fingerprint
        from public.global_terminal_account_documents document
       where document.document_id = existing_receipt.document_id;
    return;
  end if;

  select document.*
    into current_document
    from public.global_terminal_account_documents document
   where document.tenant_id = current_tenant_id
     and document.owner_user_id = current_user_id
     and document.document_key = p_document_key
   for update;

  if found and current_document.version <> p_expected_version then
    return query select 'document-version-conflict'::text,
                        current_document.version,
                        current_document.document_fingerprint;
    return;
  end if;
  if not found and p_expected_version <> 0 then
    return query select 'document-version-conflict'::text, 0, ''::text;
    return;
  end if;

  if current_document.document_id is null then
    next_document_id := gen_random_uuid();
    next_version := 1;
    next_event := 'document-created';
    insert into public.global_terminal_account_documents (
      document_id, tenant_id, owner_user_id, document_key, payload,
      document_fingerprint, version, deleted, created_at, updated_at
    ) values (
      next_document_id, current_tenant_id, current_user_id, p_document_key,
      p_payload, p_document_fingerprint, next_version, false, now(), now()
    );
  else
    next_document_id := current_document.document_id;
    next_version := current_document.version + 1;
    next_event := 'document-updated';
    update public.global_terminal_account_documents
       set payload = p_payload,
           document_fingerprint = p_document_fingerprint,
           version = next_version,
           deleted = false,
           updated_at = now()
     where document_id = next_document_id;
  end if;

  insert into public.global_terminal_account_document_audit (
    event_id, tenant_id, owner_user_id, document_id, document_key,
    event_type, prior_version, new_version, prior_fingerprint,
    new_fingerprint, created_at
  ) values (
    'acda_' || replace(gen_random_uuid()::text, '-', ''),
    current_tenant_id, current_user_id, next_document_id, p_document_key,
    next_event, coalesce(current_document.version, 0), next_version,
    coalesce(current_document.document_fingerprint, ''), p_document_fingerprint,
    now()
  );
  insert into public.global_terminal_account_document_receipts (
    receipt_id, tenant_id, owner_user_id, document_id, idempotency_key,
    operation, request_fingerprint, result_version, result_status, created_at
  ) values (
    'acdr_' || replace(gen_random_uuid()::text, '-', ''),
    current_tenant_id, current_user_id, next_document_id, p_idempotency_key,
    'apply', p_document_fingerprint, next_version, 'applied', now()
  );

  return query select 'applied'::text, next_version, p_document_fingerprint;
end;
$$;

create or replace function public.global_terminal_delete_account_document(
  p_document_key text,
  p_expected_version integer,
  p_idempotency_key text
)
returns table(status text, version integer, document_fingerprint text)
language plpgsql
security definer
set search_path = ''
as $$
declare
  current_user_id uuid := (select auth.uid());
  current_tenant_id uuid;
  current_document public.global_terminal_account_documents%rowtype;
  existing_receipt public.global_terminal_account_document_receipts%rowtype;
  tombstone_fingerprint text := repeat('0', 64);
  next_version integer;
begin
  if current_user_id is null then
    raise exception 'authenticated-session-required' using errcode = '42501';
  end if;
  if p_document_key !~ '^[a-z][a-z0-9-]{0,63}$'
     or p_expected_version < 0
     or char_length(p_idempotency_key) not between 8 and 128 then
    raise exception 'invalid-account-document-delete' using errcode = '22023';
  end if;
  select membership.tenant_id
    into current_tenant_id
    from public.global_terminal_tenant_memberships membership
   where membership.user_id = current_user_id
     and membership.role in ('owner','member')
   order by membership.created_at, membership.tenant_id
   limit 1;
  if current_tenant_id is null then
    raise exception 'account-membership-required' using errcode = '42501';
  end if;

  select receipt.*
    into existing_receipt
    from public.global_terminal_account_document_receipts receipt
   where receipt.tenant_id = current_tenant_id
     and receipt.owner_user_id = current_user_id
     and receipt.idempotency_key = p_idempotency_key;
  if found then
    if existing_receipt.operation <> 'delete' then
      raise exception 'idempotency-key-reused' using errcode = '23505';
    end if;
    return query select 'deduped'::text, existing_receipt.result_version, tombstone_fingerprint;
    return;
  end if;

  select document.*
    into current_document
    from public.global_terminal_account_documents document
   where document.tenant_id = current_tenant_id
     and document.owner_user_id = current_user_id
     and document.document_key = p_document_key
   for update;
  if not found then
    return query select 'not-found'::text, 0, tombstone_fingerprint;
    return;
  end if;
  if current_document.version <> p_expected_version then
    return query select 'document-version-conflict'::text,
                        current_document.version,
                        current_document.document_fingerprint;
    return;
  end if;
  next_version := current_document.version + 1;
  update public.global_terminal_account_documents
     set payload = '{}'::jsonb,
         document_fingerprint = tombstone_fingerprint,
         version = next_version,
         deleted = true,
         updated_at = now()
   where document_id = current_document.document_id;
  insert into public.global_terminal_account_document_audit (
    event_id, tenant_id, owner_user_id, document_id, document_key,
    event_type, prior_version, new_version, prior_fingerprint,
    new_fingerprint, created_at
  ) values (
    'acda_' || replace(gen_random_uuid()::text, '-', ''),
    current_tenant_id, current_user_id, current_document.document_id,
    p_document_key, 'document-deleted', current_document.version, next_version,
    current_document.document_fingerprint, tombstone_fingerprint, now()
  );
  insert into public.global_terminal_account_document_receipts (
    receipt_id, tenant_id, owner_user_id, document_id, idempotency_key,
    operation, request_fingerprint, result_version, result_status, created_at
  ) values (
    'acdr_' || replace(gen_random_uuid()::text, '-', ''),
    current_tenant_id, current_user_id, current_document.document_id,
    p_idempotency_key, 'delete', tombstone_fingerprint, next_version, 'deleted', now()
  );
  return query select 'deleted'::text, next_version, tombstone_fingerprint;
end;
$$;

revoke all on function public.global_terminal_apply_account_document(text, jsonb, text, integer, text)
  from public, anon;
revoke all on function public.global_terminal_delete_account_document(text, integer, text)
  from public, anon;
grant execute on function public.global_terminal_apply_account_document(text, jsonb, text, integer, text)
  to authenticated;
grant execute on function public.global_terminal_delete_account_document(text, integer, text)
  to authenticated;

commit;
