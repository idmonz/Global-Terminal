\set ON_ERROR_STOP on

begin;

insert into auth.users (id, aud, role, created_at, updated_at) values
  ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'authenticated', 'authenticated', now(), now()),
  ('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', 'authenticated', 'authenticated', now(), now());

insert into public.global_terminal_tenants (id, name) values
  ('11111111-1111-4111-8111-111111111111', 'Local Account A'),
  ('22222222-2222-4222-8222-222222222222', 'Local Account B');

insert into public.global_terminal_tenant_memberships (tenant_id, user_id, role) values
  ('11111111-1111-4111-8111-111111111111', 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'owner'),
  ('22222222-2222-4222-8222-222222222222', 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', 'owner');

set local role authenticated;
select set_config(
  'request.jwt.claim.sub',
  'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  true
);

insert into public.global_terminal_observation_runs (
  run_id,
  tenant_id,
  owner_user_id,
  watchlist_resource_id,
  idempotency_key,
  request_fingerprint,
  status
) values (
  'run-local-a-001',
  '11111111-1111-4111-8111-111111111111',
  'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  'watchlist-a',
  'idem-local-a-001',
  repeat('a', 64),
  'queued'
);

insert into public.global_terminal_observation_snapshots (
  snapshot_id,
  tenant_id,
  owner_user_id,
  run_id,
  watchlist_resource_id,
  symbol,
  snapshot_status,
  source_status,
  retrieved_at,
  content_hash,
  payload_json
) values (
  'snapshot-a-001',
  '11111111-1111-4111-8111-111111111111',
  'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  'run-local-a-001',
  'watchlist-a',
  'AAPL',
  'fresh',
  'fixture',
  now(),
  repeat('b', 64),
  '{"price": 100}'::jsonb
);

insert into public.global_terminal_provider_quota_ledger (
  event_id,
  tenant_id,
  owner_user_id,
  run_id,
  provider,
  operation,
  call_count,
  source_status
) values (
  'quota-a-001',
  '11111111-1111-4111-8111-111111111111',
  'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  'run-local-a-001',
  'fixture-provider',
  'quote',
  1,
  'fixture'
);

do $test$
begin
  if (select count(*) from public.global_terminal_observation_runs) <> 1 then
    raise exception 'Account A cannot read its run';
  end if;
  if (
    select count(*)
    from public.global_terminal_observation_run_audit
    where event_type = 'run-created'
  ) <> 1 then
    raise exception 'Insert audit was not created';
  end if;
end
$test$;

select set_config(
  'request.jwt.claim.sub',
  'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
  true
);

do $test$
begin
  if (select count(*) from public.global_terminal_observation_runs) <> 0
     or (select count(*) from public.global_terminal_observation_snapshots) <> 0
     or (select count(*) from public.global_terminal_provider_quota_ledger) <> 0
     or (select count(*) from public.global_terminal_observation_run_audit) <> 0 then
    raise exception 'Account B can see Account A observation data';
  end if;

  begin
    insert into public.global_terminal_observation_runs (
      run_id,
      tenant_id,
      owner_user_id,
      watchlist_resource_id,
      idempotency_key,
      request_fingerprint,
      status
    ) values (
      'run-cross-tenant',
      '11111111-1111-4111-8111-111111111111',
      'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
      'watchlist-b',
      'idem-cross-tenant',
      repeat('c', 64),
      'queued'
    );
    raise exception 'Cross-tenant run insert unexpectedly succeeded';
  exception
    when insufficient_privilege then null;
  end;

  begin
    insert into public.global_terminal_provider_quota_ledger (
      event_id,
      tenant_id,
      owner_user_id,
      run_id,
      provider,
      operation
    ) values (
      'quota-cross-001',
      '22222222-2222-4222-8222-222222222222',
      'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
      'run-local-a-001',
      'fixture-provider',
      'quote'
    );
    raise exception 'Cross-tenant child reference unexpectedly succeeded';
  exception
    when foreign_key_violation then null;
  end;

  begin
    insert into public.global_terminal_observation_run_audit (
      event_id,
      tenant_id,
      owner_user_id,
      run_id,
      event_type
    ) values (
      'audit-direct-001',
      '22222222-2222-4222-8222-222222222222',
      'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
      'run-local-b-001',
      'forged'
    );
    raise exception 'Authenticated audit mutation unexpectedly succeeded';
  exception
    when insufficient_privilege then null;
  end;
end
$test$;

select set_config(
  'request.jwt.claim.sub',
  'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  true
);

update public.global_terminal_observation_runs
set
  status = 'completed',
  version = version + 1,
  completed_at = now(),
  updated_at = now()
where run_id = 'run-local-a-001'
  and version = 1;

do $test$
declare
  touched integer;
begin
  update public.global_terminal_observation_runs
  set status = 'failed'
  where run_id = 'run-local-a-001'
    and version = 1;
  get diagnostics touched = row_count;
  if touched <> 0 then
    raise exception 'Stale optimistic update unexpectedly changed a row';
  end if;
  if (select count(*) from public.global_terminal_observation_run_audit) <> 2 then
    raise exception 'Status update audit was not created';
  end if;
end
$test$;

delete from public.global_terminal_observation_runs
where run_id = 'run-local-a-001';

do $test$
begin
  if (select count(*) from public.global_terminal_observation_snapshots) <> 0
     or (select count(*) from public.global_terminal_provider_quota_ledger) <> 0 then
    raise exception 'Run child rows did not cascade';
  end if;
  if (select count(*) from public.global_terminal_observation_run_audit) <> 3 then
    raise exception 'Audit evidence did not survive run deletion';
  end if;
end
$test$;

select set_config(
  'request.jwt.claim.sub',
  'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
  true
);

do $test$
begin
  if (select count(*) from public.global_terminal_observation_run_audit) <> 0 then
    raise exception 'Account B can see Account A retained audit evidence';
  end if;
end
$test$;

rollback;

select 'phase6n_local_rls_pass';
