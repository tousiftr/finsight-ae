# dbt Validation Runbook

## 1) dbt project validation commands
Run from `dbt_fintech/`:

```bash
dbt debug
dbt parse
dbt ls
dbt build
```

## 2) Neon materialization validation SQL

```sql
select
  table_schema,
  table_name,
  table_type
from information_schema.tables
where table_schema = 'dbt_rad'
  and (
    table_name like 'stg\_%' escape '\\'
    or table_name like 'int\_%' escape '\\'
    or table_name like 'mrt\_%' escape '\\'
  )
order by table_name;
```

Expected pattern:
- `stg_*` => `VIEW`
- `int_*` => `BASE TABLE`
- `mrt_*` => `VIEW`

## 3) Row count validation SQL

```sql
select 'stg_transactions' as model, count(*) as row_count from dbt_rad.stg_transactions
union all
select 'int_transactions', count(*) from dbt_rad.int_transactions
union all
select 'int_transactions_enriched', count(*) from dbt_rad.int_transactions_enriched
union all
select 'mrt_rp__finance_daily_transactions', count(*) from dbt_rad.mrt_rp__finance_daily_transactions;
```

Review for expected continuity across lineage. Minor differences are only expected when model logic intentionally changes grain.

## 4) Relationship validation SQL

```sql
-- transactions -> accounts
select count(*) as orphan_transactions_to_accounts
from dbt_rad.int_transactions_enriched t
left join dbt_rad.int_accounts a
  on t.account_id = a.account_id
where a.account_id is null;

-- transactions -> customers
select count(*) as orphan_transactions_to_customers
from dbt_rad.int_transactions_enriched t
left join dbt_rad.int_customers c
  on t.customer_id = c.customer_id
where c.customer_id is null;
```

Expected: orphan counts should be `0` under normal validated runs.
