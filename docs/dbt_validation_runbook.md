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
where table_schema = 'dbt_fs'
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
select 'stg_transactions' as model, count(*) as row_count from dbt_fs.stg_transactions
union all
select 'int_transactions', count(*) from dbt_fs.int_transactions
union all
select 'int_transactions_enriched', count(*) from dbt_fs.int_transactions_enriched
union all
select 'mrt_rp__finance_daily_transactions', count(*) from dbt_fs.mrt_rp__finance_daily_transactions;
```

Review for expected continuity across lineage. Minor differences are only expected when model logic intentionally changes grain.

## 4) Relationship validation SQL

```sql
-- transactions -> accounts
select count(*) as orphan_transactions_to_accounts
from dbt_fs.int_transactions_enriched t
left join dbt_fs.int_accounts a
  on t.account_id = a.account_id
where a.account_id is null;

-- transactions -> customers
select count(*) as orphan_transactions_to_customers
from dbt_fs.int_transactions_enriched t
left join dbt_fs.int_customers c
  on t.customer_id = c.customer_id
where c.customer_id is null;
```

Expected: orphan counts should be `0` under normal validated runs.

## 5) Raw transaction account referential integrity

Use this query after loading generated raw data to confirm every raw transaction account ID exists in `raw.raw_accounts` before running dbt staging relationship tests:

```sql
select
    t.payload ->> 'account_id' as account_id,
    count(*) as orphan_transaction_count
from raw.raw_transactions t
left join raw.raw_accounts a
    on t.payload ->> 'account_id' = a.payload ->> 'account_id'
where a.payload ->> 'account_id' is null
group by t.payload ->> 'account_id'
order by orphan_transaction_count desc;
```

Expected: `0` rows.

## 6) dbt schema consolidation validation SQL

Use this query after rebuilding dbt to confirm new dbt-owned objects land in `dbt_fs` instead of legacy dbt schemas:

```sql
select
    table_schema,
    table_name,
    table_type
from information_schema.tables
where table_schema in (
    'dbt_fs',
    'dbt_rad',
    'mart_core',
    'mart_finance',
    'mart_product',
    'mart_risk',
    'mart_growth',
    'snapshots'
)
order by table_schema, table_name;
```

Expected: new dbt objects should appear in `dbt_fs`. Old schemas may still exist from previous runs, but new builds should not create or update them.

## 7) Optional legacy schema cleanup SQL

Only run this manually after validating `dbt_fs` contains the expected staging, intermediate, mart, seed, and snapshot objects:

```sql
drop schema if exists dbt_rad cascade;
drop schema if exists mart_core cascade;
drop schema if exists mart_finance cascade;
drop schema if exists mart_product cascade;
drop schema if exists mart_risk cascade;
drop schema if exists mart_growth cascade;
drop schema if exists snapshots cascade;
```
