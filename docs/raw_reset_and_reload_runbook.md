# Raw Reset and Reload Runbook

This runbook resets Neon `raw` tables, regenerates one clean local seed batch, optionally uploads it to Cloudflare R2, loads it into Neon idempotently, and rebuilds dbt models in `dbt_fs`.

## Safety boundaries

- Do not commit `.env`, `.env.dbt`, `dbt_fintech/profiles.yml`, generated `data/raw`, or `dbt_fintech/target` artifacts.
- The `raw` schema is ingestion-owned. The `dbt_fs` schema is dbt-owned.
- Local reloads use `pg8000`; do not use `psycopg2` on Windows ARM64.
- The loader uses `on conflict (source_object_key, raw_record_hash) do nothing`, so rerunning it against the same files skips duplicates.

## Reset helper SQL

### Check existing raw tables

```sql
select table_name
from information_schema.tables
where table_schema = 'raw'
order by table_name;
```

### Truncate raw tables

```sql
truncate table
    raw.raw_product_events,
    raw.raw_kyc_applications,
    raw.raw_transactions,
    raw.raw_accounts,
    raw.raw_customers,
    raw.raw_merchants
restart identity;
```

### Check counts

```sql
select 'raw_customers' as table_name, count(*) from raw.raw_customers
union all
select 'raw_accounts', count(*) from raw.raw_accounts
union all
select 'raw_merchants', count(*) from raw.raw_merchants
union all
select 'raw_transactions', count(*) from raw.raw_transactions
union all
select 'raw_product_events', count(*) from raw.raw_product_events
union all
select 'raw_kyc_applications', count(*) from raw.raw_kyc_applications;
```

### Check database size

```sql
select pg_size_pretty(pg_database_size(current_database())) as database_size;
```

## Clean local seed reload sequence

Use this sequence for a one-time clean seed batch on the Windows workstation:

```powershell
cd C:\Users\Rad\OneDrive\Documents\Desktop\finsight-analytics-engineering

python scripts/apply_raw_ddl.py

python data_generator/main.py --customer-count 1500 --merchant-count 500 --output-dir data/raw

python scripts/upload_local_raw_to_r2.py --raw-root data/raw

python scripts/load_local_raw_to_neon.py --raw-root data/raw

docker run --rm `
  --env-file .env.dbt `
  -v "${PWD}/dbt_fintech:/usr/app" `
  -w /usr/app `
  finsight-dbt:local build --profiles-dir . --full-refresh
```

If R2 upload is not needed locally, skip the upload step and load Neon directly:

```powershell
python scripts/load_local_raw_to_neon.py --raw-root data/raw
```

## Domain-scoped commands

Load one local raw domain into Neon:

```powershell
python scripts/load_local_raw_to_neon.py --raw-root data/raw --domain transactions
```

Upload one local raw domain to R2:

```powershell
python scripts/upload_local_raw_to_r2.py --raw-root data/raw --domain transactions
```

Supported domains are `customers`, `accounts`, `merchants`, `transactions`, `product_events`, and `kyc_applications`.

## Validation SQL

### Raw counts

```sql
select 'raw_customers' as table_name, count(*) from raw.raw_customers
union all
select 'raw_accounts', count(*) from raw.raw_accounts
union all
select 'raw_merchants', count(*) from raw.raw_merchants
union all
select 'raw_transactions', count(*) from raw.raw_transactions;
```

### dbt staging counts

```sql
select 'stg_customers' as model_name, count(*) from dbt_fs.stg_customers
union all
select 'stg_accounts', count(*) from dbt_fs.stg_accounts
union all
select 'stg_merchants', count(*) from dbt_fs.stg_merchants
union all
select 'stg_transactions', count(*) from dbt_fs.stg_transactions;
```

### Duplicate check

```sql
select
    source_object_key,
    raw_record_hash,
    count(*) as duplicate_count
from raw.raw_transactions
group by source_object_key, raw_record_hash
having count(*) > 1
limit 50;
```

Expected duplicate result: `0 rows`.

## dbt docs

After a successful build, generate docs:

```powershell
docker run --rm `
  --env-file .env.dbt `
  -v "${PWD}/dbt_fintech:/usr/app" `
  -w /usr/app `
  finsight-dbt:local docs generate --profiles-dir .
```

## Neon free-tier retention

Delete old Neon raw rows without deleting anything from R2:

```powershell
python scripts/cleanup_neon_raw_retention.py
```

Preview rows that would be deleted:

```powershell
python scripts/cleanup_neon_raw_retention.py --dry-run
```

Default retention windows:

| Raw table | Retention |
| --- | ---: |
| `raw.raw_transactions` | 7 days |
| `raw.raw_product_events` | 7 days |
| `raw.raw_kyc_applications` | 14 days |
| `raw.raw_customers` | 30 days |
| `raw.raw_accounts` | 30 days |
| `raw.raw_merchants` | 30 days |

## Seed batch versus scheduled live batches

The clean seed batch can be relatively large because it is a one-time baseline reload. Scheduled live batches should stay small because Neon free storage is limited and raw rows are retained only for a short operational window.

Suggested live batch sizes:

- `customers`: 5 to 20
- `accounts`: 5 to 40
- `merchants`: 0 to 5
- `transactions`: 100 to 300
- `product_events`: 200 to 500
- `kyc_applications`: only for new customers
