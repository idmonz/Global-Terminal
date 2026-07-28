begin;

set local lock_timeout = '10s';

-- The pilot permits one non-deleted schedule per account. The original table
-- constraint also counted soft-deleted rows, which prevented a user from ever
-- creating a replacement after deletion. Preserve the single-active-schedule
-- boundary while allowing an intentionally deleted schedule to remain as
-- immutable operational evidence.
alter table public.global_terminal_hosted_observation_schedules
  drop constraint if exists global_terminal_hosted_observation_schedules_tenant_id_owner_user_key;

create unique index if not exists global_terminal_hosted_schedule_one_active_owner_idx
  on public.global_terminal_hosted_observation_schedules (tenant_id, owner_user_id)
  where state <> 'deleted';

commit;
