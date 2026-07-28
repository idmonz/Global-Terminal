\set ON_ERROR_STOP on

begin;

insert into auth.users (id, aud, role, created_at, updated_at) values
  ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'authenticated', 'authenticated', now(), now()),
  ('bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', 'authenticated', 'authenticated', now(), now());

insert into public.global_terminal_tenants (id, name) values
  ('11111111-1111-4111-8111-111111111111', 'Local Alert Account A'),
  ('22222222-2222-4222-8222-222222222222', 'Local Alert Account B');

insert into public.global_terminal_tenant_memberships (tenant_id, user_id, role) values
  ('11111111-1111-4111-8111-111111111111', 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'owner'),
  ('22222222-2222-4222-8222-222222222222', 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', 'owner');

set local role authenticated;
select set_config('request.jwt.claim.sub', 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', true);

insert into public.global_terminal_watchlists (
  id, tenant_id, owner_user_id, name, source_key, source_fingerprint
) values (
  '11111111-aaaa-4aaa-8aaa-111111111111',
  '11111111-1111-4111-8111-111111111111',
  'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  'Account A Alert List',
  'phase6o-alert-list-a',
  repeat('a', 64)
);

insert into public.global_terminal_observation_runs (
  run_id, tenant_id, owner_user_id, watchlist_resource_id,
  idempotency_key, request_fingerprint, status
) values (
  'obsrun-alert-a-001',
  '11111111-1111-4111-8111-111111111111',
  'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  '11111111-aaaa-4aaa-8aaa-111111111111',
  'phase6o-observation-a',
  repeat('b', 64),
  'completed'
);

insert into public.global_terminal_observation_snapshots (
  snapshot_id, tenant_id, owner_user_id, run_id, watchlist_resource_id,
  symbol, asset_class, snapshot_status, source_status, observed_at,
  retrieved_at, provider, content_hash, payload_json, caveat, data_gap
) values (
  'obssnap-alert-a-001',
  '11111111-1111-4111-8111-111111111111',
  'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  'obsrun-alert-a-001',
  '11111111-aaaa-4aaa-8aaa-111111111111',
  'AAPL',
  'equity',
  'fresh',
  'fixture',
  now(),
  now(),
  'phase6o-local-conformance',
  repeat('c', 64),
  '{"quote":{"last_price":212.5}}'::jsonb,
  'Synthetic local RLS evidence.',
  'No market-provider call was made.'
);

insert into public.global_terminal_watchlist_alert_rules (
  resource_id, tenant_id, owner_user_id, watchlist_id, symbol, asset_class,
  rule_type, metric, operator, threshold, threshold_unit, frequency,
  frequency_minutes, session_policy, cooldown_minutes, severity, state,
  fingerprint, next_due_at, expires_at
) values (
  'alert-rule-a-001',
  '11111111-1111-4111-8111-111111111111',
  'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  '11111111-aaaa-4aaa-8aaa-111111111111',
  'AAPL',
  'equity',
  'price_above',
  'last_price',
  'above',
  '200'::jsonb,
  'USD',
  '15m',
  15,
  'market-aware',
  60,
  'high',
  'active',
  repeat('d', 64),
  now(),
  now() + interval '7 days'
);

insert into public.global_terminal_watchlist_alert_evaluations (
  run_id, tenant_id, owner_user_id, idempotency_key, request_fingerprint,
  mode, status, due_count, evaluated_count, triggered_count,
  provider_call_count, source_clock, detail, completed_at
) values (
  'alert-eval-a-001',
  '11111111-1111-4111-8111-111111111111',
  'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  'phase6o-alert-eval-a',
  repeat('e', 64),
  'manual',
  'completed',
  1,
  1,
  1,
  0,
  jsonb_build_object('evaluated_at', now()),
  '{"market_provider_calls":0}'::jsonb,
  now()
);

insert into public.global_terminal_watchlist_alert_triggers (
  trigger_id, tenant_id, owner_user_id, rule_id, watchlist_id,
  evaluation_run_id, snapshot_id, symbol, dedupe_key, severity,
  metric, operator, threshold, observed_value, source_status, provider,
  evaluated_at, triggered_at, message, caveat, data_gap, evidence
) values (
  'alert-trigger-a-001',
  '11111111-1111-4111-8111-111111111111',
  'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  'alert-rule-a-001',
  '11111111-aaaa-4aaa-8aaa-111111111111',
  'alert-eval-a-001',
  'obssnap-alert-a-001',
  'AAPL',
  repeat('f', 64),
  'high',
  'last_price',
  'above',
  '200'::jsonb,
  '212.5'::jsonb,
  'fixture',
  'phase6o-local-conformance',
  now(),
  now(),
  'AAPL price condition matched a synthetic stored observation.',
  'Synthetic local RLS evidence.',
  'No market-provider call was made.',
  '{"snapshot_id":"obssnap-alert-a-001"}'::jsonb
);

insert into public.global_terminal_watchlist_alert_worker_state (
  resource_id, tenant_id, owner_user_id, state, enabled, last_heartbeat_at
) values (
  'alert-worker-a-001',
  '11111111-1111-4111-8111-111111111111',
  'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  'stopped',
  false,
  now()
);

do $test$
begin
  if (select count(*) from public.global_terminal_watchlist_alert_rules) <> 1
     or (select count(*) from public.global_terminal_watchlist_alert_evaluations) <> 1
     or (select count(*) from public.global_terminal_watchlist_alert_triggers) <> 1
     or (select count(*) from public.global_terminal_watchlist_alert_worker_state) <> 1 then
    raise exception 'Account A cannot read its Alert Manager data';
  end if;
  if (select count(*) from public.global_terminal_watchlist_alert_audit) < 4 then
    raise exception 'Alert Manager lifecycle audit evidence was not created';
  end if;
end
$test$;

select set_config('request.jwt.claim.sub', 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', true);

insert into public.global_terminal_watchlists (
  id, tenant_id, owner_user_id, name, source_key, source_fingerprint
) values (
  '22222222-bbbb-4bbb-8bbb-222222222222',
  '22222222-2222-4222-8222-222222222222',
  'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
  'Account B Alert List',
  'phase6o-alert-list-b',
  repeat('1', 64)
);

insert into public.global_terminal_watchlist_alert_evaluations (
  run_id, tenant_id, owner_user_id, idempotency_key, request_fingerprint,
  mode, status, provider_call_count
) values (
  'alert-eval-b-001',
  '22222222-2222-4222-8222-222222222222',
  'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
  'phase6o-alert-eval-b',
  repeat('2', 64),
  'manual',
  'no-due',
  0
);

do $test$
declare
  touched integer;
begin
  if (select count(*) from public.global_terminal_watchlist_alert_rules) <> 0
     or (select count(*) from public.global_terminal_watchlist_alert_triggers) <> 0
     or (select count(*) from public.global_terminal_watchlist_alert_worker_state) <> 0
     or (select count(*) from public.global_terminal_watchlist_alert_audit where owner_user_id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa') <> 0 then
    raise exception 'Account B can read Account A Alert Manager data';
  end if;

  update public.global_terminal_watchlist_alert_rules
  set state = 'cancelled', version = version + 1
  where resource_id = 'alert-rule-a-001';
  get diagnostics touched = row_count;
  if touched <> 0 then raise exception 'Account B updated Account A rule'; end if;

  delete from public.global_terminal_watchlist_alert_triggers
  where trigger_id = 'alert-trigger-a-001';
  get diagnostics touched = row_count;
  if touched <> 0 then raise exception 'Account B deleted Account A trigger'; end if;

  begin
    insert into public.global_terminal_watchlist_alert_rules (
      resource_id, tenant_id, owner_user_id, watchlist_id, symbol, rule_type,
      metric, operator, threshold, frequency, frequency_minutes,
      session_policy, fingerprint
    ) values (
      'alert-cross-tenant',
      '11111111-1111-4111-8111-111111111111',
      'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
      '11111111-aaaa-4aaa-8aaa-111111111111',
      'MSFT', 'price_above', 'last_price', 'above', '300'::jsonb,
      '15m', 15, 'market-aware', repeat('3', 64)
    );
    raise exception 'Cross-tenant rule insert unexpectedly succeeded';
  exception when insufficient_privilege then null;
  end;

  begin
    insert into public.global_terminal_watchlist_alert_triggers (
      trigger_id, tenant_id, owner_user_id, rule_id, watchlist_id,
      evaluation_run_id, snapshot_id, symbol, dedupe_key, metric, operator,
      threshold, observed_value, source_status, evaluated_at, triggered_at,
      message
    ) values (
      'alert-cross-parent',
      '22222222-2222-4222-8222-222222222222',
      'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
      'alert-rule-a-001',
      '22222222-bbbb-4bbb-8bbb-222222222222',
      'alert-eval-b-001',
      'obssnap-alert-a-001',
      'AAPL', repeat('4', 64), 'last_price', 'above', '200'::jsonb,
      '212.5'::jsonb, 'fixture', now(), now(),
      'Cross-parent linkage must fail.'
    );
    raise exception 'Cross-tenant alert parent linkage unexpectedly succeeded';
  exception when foreign_key_violation then null;
  end;

  begin
    insert into public.global_terminal_watchlist_alert_audit (
      event_id, tenant_id, owner_user_id, resource_type, resource_id,
      event_type
    ) values (
      'alert-audit-forged',
      '22222222-2222-4222-8222-222222222222',
      'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
      'rule', 'forged', 'forged'
    );
    raise exception 'Authenticated alert audit mutation unexpectedly succeeded';
  exception when insufficient_privilege then null;
  end;
end
$test$;

select set_config('request.jwt.claim.sub', 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', true);

update public.global_terminal_watchlist_alert_rules
set state = 'paused', version = 2, updated_at = now()
where resource_id = 'alert-rule-a-001' and version = 1;

do $test$
declare
  touched integer;
  audit_before integer;
begin
  update public.global_terminal_watchlist_alert_rules
  set state = 'cancelled', version = 3
  where resource_id = 'alert-rule-a-001' and version = 1;
  get diagnostics touched = row_count;
  if touched <> 0 then raise exception 'Stale optimistic rule update changed a row'; end if;

  update public.global_terminal_watchlist_alert_triggers
  set review_state = 'acknowledged', reviewed_at = now(), acknowledged_at = now(), version = 2
  where trigger_id = 'alert-trigger-a-001' and version = 1;
  get diagnostics touched = row_count;
  if touched <> 1 then raise exception 'Account A could not acknowledge its trigger'; end if;

  select count(*) into audit_before
  from public.global_terminal_watchlist_alert_audit
  where owner_user_id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
  if audit_before < 6 then raise exception 'Rule and trigger transitions were not audited'; end if;
end
$test$;

delete from public.global_terminal_watchlist_alert_rules
where resource_id = 'alert-rule-a-001';

do $test$
begin
  if (select count(*) from public.global_terminal_watchlist_alert_triggers where trigger_id = 'alert-trigger-a-001') <> 0 then
    raise exception 'Rule deletion did not remove bounded trigger data';
  end if;
  if (
    select count(*) from public.global_terminal_watchlist_alert_audit
    where owner_user_id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
  ) < 8 then
    raise exception 'Alert audit evidence did not survive parent deletion';
  end if;
end
$test$;

select set_config('request.jwt.claim.sub', 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', true);

do $test$
begin
  if (
    select count(*) from public.global_terminal_watchlist_alert_audit
    where owner_user_id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
  ) <> 0 then
    raise exception 'Account B can see Account A retained alert audit evidence';
  end if;
end
$test$;

rollback;

select 'phase6o_local_alert_rls_pass';
