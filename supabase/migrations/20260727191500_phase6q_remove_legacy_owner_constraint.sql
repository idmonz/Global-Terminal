begin;

set local lock_timeout = '10s';

-- PostgreSQL truncates long auto-generated constraint names. Resolve the
-- legacy UNIQUE (tenant_id, owner_user_id) constraint by its exact column set
-- instead of relying on a generated identifier, then retain the partial unique
-- index installed by the preceding migration.
do $$
declare
  legacy_constraint text;
begin
  select constraint_row.conname
    into legacy_constraint
    from pg_catalog.pg_constraint constraint_row
    join pg_catalog.pg_class relation_row
      on relation_row.oid = constraint_row.conrelid
    join pg_catalog.pg_namespace namespace_row
      on namespace_row.oid = relation_row.relnamespace
   where namespace_row.nspname = 'public'
     and relation_row.relname = 'global_terminal_hosted_observation_schedules'
     and constraint_row.contype = 'u'
     and (
       select array_agg(attribute_row.attname order by key_row.ordinality)
         from unnest(constraint_row.conkey) with ordinality as key_row(attnum, ordinality)
         join pg_catalog.pg_attribute attribute_row
           on attribute_row.attrelid = relation_row.oid
          and attribute_row.attnum = key_row.attnum
     ) = array['tenant_id', 'owner_user_id']::name[];

  if legacy_constraint is not null then
    execute format(
      'alter table public.global_terminal_hosted_observation_schedules drop constraint %I',
      legacy_constraint
    );
  end if;
end;
$$;

create unique index if not exists global_terminal_hosted_schedule_one_active_owner_idx
  on public.global_terminal_hosted_observation_schedules (tenant_id, owner_user_id)
  where state <> 'deleted';

commit;
