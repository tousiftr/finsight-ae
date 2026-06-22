create schema if not exists raw;

create table if not exists raw.raw_customers (
    raw_customer_id bigserial primary key,

    customer_id text,
    payload jsonb not null,

    source_system text not null default 'cloudflare_r2',
    source_bucket text not null,
    source_object_key text not null,
    source_file_path text not null,

    dt date,
    batch_id text,

    raw_record_hash text not null,
    loaded_at timestamptz not null default now(),

    constraint uq_raw_customers_source_record
        unique (source_object_key, raw_record_hash)
);

create index if not exists idx_raw_customers_customer_id
    on raw.raw_customers (customer_id);

create index if not exists idx_raw_customers_batch_id
    on raw.raw_customers (batch_id);

create index if not exists idx_raw_customers_dt
    on raw.raw_customers (dt);

create table if not exists raw.raw_ingestion_log (
    ingestion_log_id bigserial primary key,

    source_system text not null,
    source_bucket text not null,
    source_object_key text not null,
    target_table text not null,

    dt date,
    batch_id text,

    rows_read integer not null,
    rows_inserted integer not null,
    rows_skipped integer not null,

    status text not null,
    error_message text,

    started_at timestamptz not null,
    finished_at timestamptz not null default now()
);
