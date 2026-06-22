-- FinSight raw-layer diagnostics and Neon storage monitoring.
-- Run with psql against Neon. These queries only read Neon metadata/raw tables;
-- they never touch Cloudflare R2 objects.

-- 1) Database size for Neon free-tier monitoring.
select pg_size_pretty(pg_database_size(current_database())) as database_size;

-- 2) Raw table sizes, including indexes/toast via pg_total_relation_size.
select
    n.nspname as schema_name,
    c.relname as table_name,
    pg_size_pretty(pg_total_relation_size(c.oid)) as total_size,
    pg_size_pretty(pg_relation_size(c.oid)) as table_size,
    pg_size_pretty(pg_indexes_size(c.oid)) as index_size
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'raw'
  and c.relname in (
      'raw_customers',
      'raw_accounts',
      'raw_merchants',
      'raw_transactions',
      'raw_product_events',
      'raw_kyc_applications'
  )
  and c.relkind in ('r', 'p')
order by pg_total_relation_size(c.oid) desc;

-- 2b) Largest raw indexes. This helps confirm storage-heavy indexes were removed.
select
    schemaname as schema_name,
    tablename as table_name,
    indexname as index_name,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
from pg_stat_user_indexes
where schemaname = 'raw'
order by pg_relation_size(indexrelid) desc;

-- 3) Row counts by batch_id for every raw table.
select *
from (
    select 'raw.raw_customers' as table_name, batch_id, count(*) as row_count from raw.raw_customers group by batch_id
    union all
    select 'raw.raw_accounts' as table_name, batch_id, count(*) as row_count from raw.raw_accounts group by batch_id
    union all
    select 'raw.raw_merchants' as table_name, batch_id, count(*) as row_count from raw.raw_merchants group by batch_id
    union all
    select 'raw.raw_transactions' as table_name, batch_id, count(*) as row_count from raw.raw_transactions group by batch_id
    union all
    select 'raw.raw_product_events' as table_name, batch_id, count(*) as row_count from raw.raw_product_events group by batch_id
    union all
    select 'raw.raw_kyc_applications' as table_name, batch_id, count(*) as row_count from raw.raw_kyc_applications group by batch_id
) counts_by_batch
order by table_name, batch_id nulls first;

-- 4) Row counts by source_object_key for every raw table.
select *
from (
    select 'raw.raw_customers' as table_name, source_object_key, count(*) as row_count from raw.raw_customers group by source_object_key
    union all
    select 'raw.raw_accounts' as table_name, source_object_key, count(*) as row_count from raw.raw_accounts group by source_object_key
    union all
    select 'raw.raw_merchants' as table_name, source_object_key, count(*) as row_count from raw.raw_merchants group by source_object_key
    union all
    select 'raw.raw_transactions' as table_name, source_object_key, count(*) as row_count from raw.raw_transactions group by source_object_key
    union all
    select 'raw.raw_product_events' as table_name, source_object_key, count(*) as row_count from raw.raw_product_events group by source_object_key
    union all
    select 'raw.raw_kyc_applications' as table_name, source_object_key, count(*) as row_count from raw.raw_kyc_applications group by source_object_key
) counts_by_source_object
order by table_name, row_count desc, source_object_key nulls first;

-- 5) Duplicate detection on the idempotency key. A clean system returns zero rows.
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

-- 6) Required idempotency unique indexes. Run after removing any duplicates reported above.
create unique index if not exists ux_raw_customers_source_object_key_raw_record_hash
    on raw.raw_customers (source_object_key, raw_record_hash);
create unique index if not exists ux_raw_accounts_source_object_key_raw_record_hash
    on raw.raw_accounts (source_object_key, raw_record_hash);
create unique index if not exists ux_raw_merchants_source_object_key_raw_record_hash
    on raw.raw_merchants (source_object_key, raw_record_hash);
create unique index if not exists ux_raw_transactions_source_object_key_raw_record_hash
    on raw.raw_transactions (source_object_key, raw_record_hash);
create unique index if not exists ux_raw_product_events_source_object_key_raw_record_hash
    on raw.raw_product_events (source_object_key, raw_record_hash);
create unique index if not exists ux_raw_kyc_applications_source_object_key_raw_record_hash
    on raw.raw_kyc_applications (source_object_key, raw_record_hash);
