-- FinSight live snapshots and incremental intermediate validation queries.
-- Run against Neon/Postgres after live ingest, dbt staging, dbt intermediate, and dbt snapshot jobs run.

-- A. Latest raw transaction loads by batch.
select
    batch_id,
    count(*) as row_count,
    max(loaded_at) as latest_loaded_at
from raw.raw_transactions
group by batch_id
order by latest_loaded_at desc
limit 10;

-- B. Customer append-only updates exist when live batches have selected customers to update.
select
    payload ->> 'customer_id' as customer_id,
    count(*) as raw_versions,
    min(loaded_at) as first_loaded_at,
    max(loaded_at) as latest_loaded_at
from raw.raw_customers
group by payload ->> 'customer_id'
having count(*) > 1
order by latest_loaded_at desc
limit 20;

-- C. Transaction append-only status updates exist when live batches have pending transactions to update.
select
    payload ->> 'transaction_id' as transaction_id,
    count(*) as raw_versions,
    min(loaded_at) as first_loaded_at,
    max(loaded_at) as latest_loaded_at
from raw.raw_transactions
group by payload ->> 'transaction_id'
having count(*) > 1
order by latest_loaded_at desc
limit 20;

-- D. Snapshot tables exist. Only customer and transaction snapshots are expected right now.
select
    table_schema,
    table_name
from information_schema.tables
where table_schema = 'snapshots'
order by table_name;

-- E. Snapshot row counts.
select count(*) from snapshots.snap_customers;
select count(*) from snapshots.snap_transactions;

-- F. Intermediate models are not being dropped/rebuilt every scheduled run:
-- check dbt logs and confirm scheduled workflows do not use --full-refresh.
