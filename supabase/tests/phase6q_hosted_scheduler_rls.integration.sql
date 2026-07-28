\set ON_ERROR_STOP on

begin;

insert into auth.users (id, aud, role, created_at, updated_at) values
  ('cccccccc-cccc-4ccc-8ccc-cccccccccccc', 'authenticated', 'authenticated', now(), now()),
  ('dddddddd-dddd-4ddd-8ddd-dddddddddddd', 'authenticated', 'authenticated', now(), now());

insert into public.global_terminal_tenants (id, name) values
  ('33333333-3333-4333-8333-333333333333', 'Phase 6Q Local Account A'),
  ('44444444-4444-4444-8444-444444444444', 'Phase 6Q Local Account B');

insert into public.global_terminal_tenant_memberships (tenant_id, user_id, role) values
  ('33333333-3333-4333-8333-333333333333', 'cccccccc-cccc-4ccc-8ccc-cccccccccccc', 'owner'),
  ('44444444-4444-4444-8444-444444444444', 'dddddddd-dddd-4ddd-8ddd-dddddddddddd', 'owner');

insert into public.global_terminal_account_documents (
  document_id, tenant_id, owner_user_id, document_key, payload,
  document_fingerprint, version, deleted
) values (
  '33333333-aaaa-4aaa-8aaa-333333333333',
  '33333333-3333-4333-8333-333333333333',
  'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
  'research-continuity',
  '{"account_continuity_version":"account_continuity.v1","tables":{"tenant_watchlists":[{"resource_id":"twl_phase6q"}],"tenant_watchlist_alert_rules":[{"resource_id":"alrule_phase6q","watchlist_resource_id":"twl_phase6q"}]}}'::jsonb,
  repeat('c', 64),
  1,
  false
);

create temporary table phase6q_results (name text primary key, payload jsonb);
grant all on table phase6q_results to authenticated, service_role;

set local role authenticated;
select set_config('request.jwt.claim.sub', 'cccccccc-cccc-4ccc-8ccc-cccccccccccc', true);
select set_config('request.jwt.claim.role', 'authenticated', true);

insert into phase6q_results values (
  'create',
  public.global_terminal_apply_hosted_observation_schedule(
    '{"schedule_id":"hsched_phase6q_local","watchlist_id":"twl_phase6q","alert_rule_id":"alrule_phase6q","state":"disabled","timezone":"UTC","cadence_minutes":60,"bounds":{"max_symbols":1,"max_provider_calls":4,"max_attempts":2,"timeout_seconds":90},"version":1}'::jsonb,
    0
  )
);

do $$
begin
  if (select payload->>'status' from phase6q_results where name='create') <> 'applied' then
    raise exception 'Phase 6Q schedule create failed';
  end if;
  if (select count(*) from public.global_terminal_hosted_observation_schedules) <> 1 then
    raise exception 'Account A cannot read its schedule';
  end if;
end;
$$;

insert into phase6q_results values (
  'enable',
  public.global_terminal_apply_hosted_observation_schedule(
    jsonb_build_object(
      'schedule_id','hsched_phase6q_local','watchlist_id','twl_phase6q','alert_rule_id','alrule_phase6q',
      'state','enabled','timezone','UTC','cadence_minutes',60,
      'bounds',jsonb_build_object('max_symbols',1,'max_provider_calls',4,'max_attempts',2,'timeout_seconds',90),
      'version',2,'consented_at',now(),'enabled_at',now(),'next_due_at',now()-interval '1 minute'
    ),
    1
  )
);

reset role;
set local role service_role;
select set_config('request.jwt.claim.sub', '', true);
select set_config('request.jwt.claim.role', 'service_role', true);

insert into phase6q_results values (
  'default-kill',
  public.global_terminal_claim_hosted_observation_schedule(repeat('a',64),repeat('b',64),120)
);

do $$
begin
  if (select payload->>'status' from phase6q_results where name='default-kill') <> 'disabled' then
    raise exception 'Safe default did not block claim';
  end if;
end;
$$;

update public.global_terminal_hosted_scheduler_control
set operator_enabled=true, global_kill_switch=false, hosted_scheduler_verified=false, updated_at=now()
where singleton=true;

insert into phase6q_results values (
  'claim-1',
  public.global_terminal_claim_hosted_observation_schedule(repeat('a',64),repeat('b',64),120)
);
insert into phase6q_results values (
  'overlap-1',
  public.global_terminal_claim_hosted_observation_schedule(repeat('d',64),repeat('e',64),120)
);

do $$
begin
  if (select payload->>'claimed' from phase6q_results where name='claim-1') <> 'true' then
    raise exception 'First due schedule was not claimed';
  end if;
  if (select payload->>'status' from phase6q_results where name='overlap-1') <> 'overlap' then
    raise exception 'Active lease did not suppress overlap';
  end if;
end;
$$;

insert into phase6q_results values (
  'heartbeat-1',
  public.global_terminal_heartbeat_hosted_observation_schedule(
    (select payload->>'scheduler_run_id' from phase6q_results where name='claim-1'),
    repeat('b',64),
    120
  )
);

insert into phase6q_results values (
  'document-1',
  public.global_terminal_apply_scheduler_account_document(
    (select payload->>'scheduler_run_id' from phase6q_results where name='claim-1'),
    repeat('b',64),
    '{"account_continuity_version":"account_continuity.v1","tables":{"tenant_watchlists":[{"resource_id":"twl_phase6q"}],"tenant_watchlist_alert_rules":[{"resource_id":"alrule_phase6q","watchlist_resource_id":"twl_phase6q"}],"tenant_observation_runs":[{"run_id":"obsrun_phase6q_local"}]}}'::jsonb,
    repeat('d',64),
    1,
    'phase6q-local-document-001'
  )
);
insert into phase6q_results values (
  'document-replay',
  public.global_terminal_apply_scheduler_account_document(
    (select payload->>'scheduler_run_id' from phase6q_results where name='claim-1'),
    repeat('b',64),
    '{"account_continuity_version":"account_continuity.v1","tables":{"tenant_watchlists":[{"resource_id":"twl_phase6q"}],"tenant_watchlist_alert_rules":[{"resource_id":"alrule_phase6q","watchlist_resource_id":"twl_phase6q"}],"tenant_observation_runs":[{"run_id":"obsrun_phase6q_local"}]}}'::jsonb,
    repeat('d',64),
    1,
    'phase6q-local-document-001'
  )
);

do $$
begin
  if (select payload->>'status' from phase6q_results where name='document-1') <> 'applied' then
    raise exception 'Scheduler account document was not persisted';
  end if;
  if (select payload->>'status' from phase6q_results where name='document-replay') <> 'deduped' then
    raise exception 'Account document replay was not deduplicated';
  end if;
end;
$$;

insert into phase6q_results values (
  'finish-1',
  public.global_terminal_finish_hosted_observation_schedule(
    (select payload->>'scheduler_run_id' from phase6q_results where name='claim-1'),
    repeat('b',64),
    jsonb_build_object(
      'status','completed','observation_run_id','obsrun_phase6q_local','evaluation_run_id','alertrun_phase6q_local',
      'trigger_count',1,'provider_call_count',1,'provider','yfinance','source_url','https://finance.yahoo.com/quote/BTC-USD',
      'source_status','live/fresh','observed_at',now(),'retrieved_at',now(),'evaluated_at',now(),'triggered_at',now(),
      'duration_ms',1200,'caveat','Public delayed source.','data_gap','No licensed realtime stream.','duplicate_suppressed',false
    )
  )
);
insert into phase6q_results values (
  'finish-replay',
  public.global_terminal_finish_hosted_observation_schedule(
    (select payload->>'scheduler_run_id' from phase6q_results where name='claim-1'),
    repeat('b',64),
    '{"status":"completed","provider_call_count":1}'::jsonb
  )
);

do $$
begin
  if (select payload->>'status' from phase6q_results where name='finish-1') <> 'completed' then
    raise exception 'Source-backed completion did not persist';
  end if;
  if (select payload->>'idempotent_replay' from phase6q_results where name='finish-replay') <> 'true' then
    raise exception 'Terminal replay was not idempotent';
  end if;
  if (select last_lkg_run_id is null from public.global_terminal_hosted_observation_schedules where schedule_id='hsched_phase6q_local') then
    raise exception 'Completed source evidence did not establish LKG';
  end if;
end;
$$;

update public.global_terminal_hosted_observation_schedules
set next_due_at=(
      select due_window_at + interval '30 seconds'
      from public.global_terminal_hosted_observation_schedule_runs
      where scheduler_run_id=(select payload->>'scheduler_run_id' from phase6q_results where name='claim-1')
    ),
    updated_at=now()
where schedule_id='hsched_phase6q_local';

insert into phase6q_results values (
  'claim-2',
  public.global_terminal_claim_hosted_observation_schedule(repeat('a',64),repeat('f',64),120)
);
insert into phase6q_results values (
  'finish-2',
  public.global_terminal_finish_hosted_observation_schedule(
    (select payload->>'scheduler_run_id' from phase6q_results where name='claim-2'),
    repeat('f',64),
    '{"status":"provider-unavailable","provider_call_count":0,"source_status":"unavailable","error_code":"provider-unavailable","caveat":"Provider unavailable.","data_gap":"Prior LKG retained."}'::jsonb
  )
);

do $$
declare
  first_run text := (select payload->>'scheduler_run_id' from phase6q_results where name='claim-1');
begin
  if (select payload->>'status' from phase6q_results where name='finish-2') <> 'provider-unavailable' then
    raise exception 'Provider failure did not persist honestly';
  end if;
  if (select last_lkg_run_id from public.global_terminal_hosted_observation_schedules where schedule_id='hsched_phase6q_local') <> first_run then
    raise exception 'Provider failure replaced the last-known-good run';
  end if;
end;
$$;

update public.global_terminal_hosted_scheduler_control
set global_kill_switch=true, updated_at=now()
where singleton=true;
insert into phase6q_results values (
  'global-kill',
  public.global_terminal_claim_hosted_observation_schedule(repeat('a',64),repeat('1',64),120)
);

do $$
begin
  if (select payload->>'status' from phase6q_results where name='global-kill') <> 'killed' then
    raise exception 'Global kill switch did not block claim';
  end if;
end;
$$;

reset role;
set local role authenticated;
select set_config('request.jwt.claim.sub', 'dddddddd-dddd-4ddd-8ddd-dddddddddddd', true);
select set_config('request.jwt.claim.role', 'authenticated', true);

do $$
begin
  if (select count(*) from public.global_terminal_hosted_observation_schedules) <> 0
     or (select count(*) from public.global_terminal_hosted_observation_schedule_runs) <> 0
     or (select count(*) from public.global_terminal_hosted_observation_schedule_audit) <> 0 then
    raise exception 'Account B can read Account A scheduler evidence';
  end if;
  begin
    insert into public.global_terminal_hosted_observation_schedules (
      schedule_id,tenant_id,owner_user_id,account_document_id,account_document_version,
      watchlist_resource_id,alert_rule_resource_id
    ) values (
      'hsched_phase6q_forge','33333333-3333-4333-8333-333333333333',
      'cccccccc-cccc-4ccc-8ccc-cccccccccccc','33333333-aaaa-4aaa-8aaa-333333333333',2,
      'twl_phase6q','alrule_phase6q'
    );
    raise exception 'Authenticated direct schedule forge was accepted';
  exception when insufficient_privilege then
    null;
  end;
end;
$$;

reset role;
set local role authenticated;
select set_config('request.jwt.claim.sub', 'cccccccc-cccc-4ccc-8ccc-cccccccccccc', true);
select set_config('request.jwt.claim.role', 'authenticated', true);

insert into phase6q_results values (
  'kill-schedule',
  public.global_terminal_apply_hosted_observation_schedule(
    '{"schedule_id":"hsched_phase6q_local","watchlist_id":"twl_phase6q","alert_rule_id":"alrule_phase6q","state":"killed","timezone":"UTC","cadence_minutes":60,"bounds":{"max_symbols":1,"max_provider_calls":4,"max_attempts":2,"timeout_seconds":90},"version":3,"killed_at":"2026-07-27T00:00:00Z"}'::jsonb,
    2
  )
);
insert into phase6q_results values (
  'delete-schedule',
  public.global_terminal_apply_hosted_observation_schedule(
    '{"schedule_id":"hsched_phase6q_local","watchlist_id":"twl_phase6q","alert_rule_id":"alrule_phase6q","state":"deleted","timezone":"UTC","cadence_minutes":60,"bounds":{"max_symbols":1,"max_provider_calls":4,"max_attempts":2,"timeout_seconds":90},"version":4,"deleted_at":"2026-07-27T00:01:00Z"}'::jsonb,
    3
  )
);

do $$
begin
  if (select payload->>'status' from phase6q_results where name='delete-schedule') <> 'applied' then
    raise exception 'Stopped schedule cleanup transition failed';
  end if;
  if (select count(*) from public.global_terminal_hosted_observation_schedule_audit) < 8 then
    raise exception 'Immutable scheduler audit evidence is incomplete';
  end if;
end;
$$;

insert into phase6q_results values (
  'replacement-create',
  public.global_terminal_apply_hosted_observation_schedule(
    '{"schedule_id":"hsched_phase6q_replacement","watchlist_id":"twl_phase6q","alert_rule_id":"alrule_phase6q","state":"disabled","timezone":"UTC","cadence_minutes":60,"bounds":{"max_symbols":1,"max_provider_calls":4,"max_attempts":2,"timeout_seconds":90},"version":1}'::jsonb,
    0
  )
);
insert into phase6q_results values (
  'replacement-delete',
  public.global_terminal_apply_hosted_observation_schedule(
    '{"schedule_id":"hsched_phase6q_replacement","watchlist_id":"twl_phase6q","alert_rule_id":"alrule_phase6q","state":"deleted","timezone":"UTC","cadence_minutes":60,"bounds":{"max_symbols":1,"max_provider_calls":4,"max_attempts":2,"timeout_seconds":90},"version":2,"deleted_at":"2026-07-27T00:02:00Z"}'::jsonb,
    1
  )
);

do $$
begin
  if (select payload->>'status' from phase6q_results where name='replacement-create') <> 'applied'
     or (select payload->>'status' from phase6q_results where name='replacement-delete') <> 'applied' then
    raise exception 'A deleted schedule blocked its bounded replacement';
  end if;
  if (select count(*) from public.global_terminal_hosted_observation_schedules where state <> 'deleted') <> 0 then
    raise exception 'Replacement schedule did not return to a safe deleted state';
  end if;
end;
$$;

select 'PHASE6Q_LOCAL_CONFORMANCE_PASS' as result;

rollback;
