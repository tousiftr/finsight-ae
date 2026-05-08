-- FinSight live generator validation queries.
-- Run against Neon/Postgres after a few live-ingest batches have loaded.

-- 1) Customer IDs should increase by batch and should not restart at C00001.
select
    batch_id,
    count(*) as customers_loaded,
    min((substring(payload ->> 'customer_id' from 2))::int) as min_customer_number,
    max((substring(payload ->> 'customer_id' from 2))::int) as max_customer_number,
    min(payload ->> 'customer_id') as min_customer_id,
    max(payload ->> 'customer_id') as max_customer_id
from raw.raw_customers
where payload ->> 'customer_id' ~ '^C[0-9]{5}$'
group by batch_id
order by batch_id desc
limit 25;

-- 2) Account IDs should increase by batch.
select
    batch_id,
    count(*) as accounts_loaded,
    min((substring(payload ->> 'account_id' from 2))::int) as min_account_number,
    max((substring(payload ->> 'account_id' from 2))::int) as max_account_number,
    min(payload ->> 'account_id') as min_account_id,
    max(payload ->> 'account_id') as max_account_id
from raw.raw_accounts
where payload ->> 'account_id' ~ '^A[0-9]{6}$'
group by batch_id
order by batch_id desc
limit 25;

-- 3) Merchant IDs should increase by batch when new merchants are created.
select
    batch_id,
    count(*) as merchants_loaded,
    min((substring(coalesce(merchant_id, payload ->> 'merchant_id') from 2))::int) as min_merchant_number,
    max((substring(coalesce(merchant_id, payload ->> 'merchant_id') from 2))::int) as max_merchant_number,
    min(coalesce(merchant_id, payload ->> 'merchant_id')) as min_merchant_id,
    max(coalesce(merchant_id, payload ->> 'merchant_id')) as max_merchant_id
from raw.raw_merchants
where coalesce(merchant_id, payload ->> 'merchant_id') ~ '^M[0-9]{6}$'
group by batch_id
order by batch_id desc
limit 25;

-- 4) Transaction counts should vary by batch.
select
    batch_id,
    count(*) as transaction_count,
    min((payload ->> 'transaction_timestamp')::timestamptz) as first_transaction_at,
    max((payload ->> 'transaction_timestamp')::timestamptz) as last_transaction_at
from raw.raw_transactions
group by batch_id
order by batch_id desc
limit 25;

-- 5) Product event counts should vary by batch.
select
    batch_id,
    count(*) as product_event_count,
    min((payload ->> 'event_timestamp')::timestamptz) as first_event_at,
    max((payload ->> 'event_timestamp')::timestamptz) as last_event_at
from raw.raw_product_events
group by batch_id
order by batch_id desc
limit 25;

-- 6) Latest loaded_at should be recent after live ingest runs.
select
    max(latest_loaded_at) as latest_loaded_at,
    now() - max(latest_loaded_at) as age
from (
    select max(loaded_at) as latest_loaded_at from raw.raw_customers
    union all select max(loaded_at) from raw.raw_accounts
    union all select max(loaded_at) from raw.raw_merchants
    union all select max(loaded_at) from raw.raw_transactions
    union all select max(loaded_at) from raw.raw_product_events
    union all select max(loaded_at) from raw.raw_kyc_applications
) latest_by_table;

-- 7) Duplicate raw records by source_object_key and raw_record_hash should return zero rows.
select *
from (
    select 'raw.raw_customers' as table_name, source_object_key, raw_record_hash, count(*) as duplicate_count from raw.raw_customers group by source_object_key, raw_record_hash having count(*) > 1
    union all
    select 'raw.raw_accounts' as table_name, source_object_key, raw_record_hash, count(*) as duplicate_count from raw.raw_accounts group by source_object_key, raw_record_hash having count(*) > 1
    union all
    select 'raw.raw_merchants' as table_name, source_object_key, raw_record_hash, count(*) as duplicate_count from raw.raw_merchants group by source_object_key, raw_record_hash having count(*) > 1
    union all
    select 'raw.raw_transactions' as table_name, source_object_key, raw_record_hash, count(*) as duplicate_count from raw.raw_transactions group by source_object_key, raw_record_hash having count(*) > 1
    union all
    select 'raw.raw_product_events' as table_name, source_object_key, raw_record_hash, count(*) as duplicate_count from raw.raw_product_events group by source_object_key, raw_record_hash having count(*) > 1
    union all
    select 'raw.raw_kyc_applications' as table_name, source_object_key, raw_record_hash, count(*) as duplicate_count from raw.raw_kyc_applications group by source_object_key, raw_record_hash having count(*) > 1
) duplicates
order by table_name, duplicate_count desc, source_object_key;
