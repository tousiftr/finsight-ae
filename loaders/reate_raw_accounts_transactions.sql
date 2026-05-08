create schema if not exists raw;

create table if not exists raw.raw_accounts (
    id bigserial primary key,
    source_system text not null default 'cloudflare_r2',
    source_bucket text,
    source_object_key text,
    source_file_path text,
    payload jsonb not null,
    dt date,
    batch_id text,
    raw_record_hash text not null,
    loaded_at timestamptz not null default now()
);

create unique index if not exists ux_raw_accounts_source_object_key_raw_record_hash
on raw.raw_accounts (source_object_key, raw_record_hash);

create index if not exists ix_raw_accounts_dt_batch
on raw.raw_accounts (dt, batch_id);


create table if not exists raw.raw_transactions (
    id bigserial primary key,
    source_system text not null default 'cloudflare_r2',
    source_bucket text,
    source_object_key text,
    source_file_path text,
    payload jsonb not null,
    dt date,
    batch_id text,
    raw_record_hash text not null,
    loaded_at timestamptz not null default now()
);

create unique index if not exists ux_raw_transactions_source_object_key_raw_record_hash
on raw.raw_transactions (source_object_key, raw_record_hash);

create index if not exists ix_raw_transactions_dt_batch
on raw.raw_transactions (dt, batch_id);