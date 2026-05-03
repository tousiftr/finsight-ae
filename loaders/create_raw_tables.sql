create schema if not exists raw;

create table if not exists raw.raw_customers (
    id bigserial primary key,
    raw_customer_id text not null,
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
    constraint ck_raw_customers_customer_id_format
        check (customer_id is null or customer_id ~ '^C[0-9]{5}$')
);

create table if not exists raw.raw_accounts (
    id bigserial primary key,
    raw_account_id text not null,
    payload jsonb not null,
    source_system text not null default 'cloudflare_r2',
    source_bucket text not null,
    source_object_key text not null,
    source_file_path text not null,
    dt date not null,
    batch_id text not null,
    raw_record_hash text not null,
    loaded_at timestamptz not null default now(),
    constraint ck_raw_accounts_account_id_format
        check ((payload ->> 'account_id') ~ '^A[0-9]{6}$'),
    constraint ck_raw_accounts_customer_id_format
        check ((payload ->> 'customer_id') ~ '^C[0-9]{5}$'),
    constraint ck_raw_accounts_account_type
        check ((payload ->> 'account_type') in ('savings', 'plus', 'investment', 'super', 'salary')),
    constraint ck_raw_accounts_investment_sub_type
        check (
            (
                (payload ->> 'account_type') = 'investment'
                and (payload ->> 'investment_sub_type') in ('crypto', 'etf', 'cfd', 'fx')
            )
            or (
                (payload ->> 'account_type') <> 'investment'
                and nullif(payload ->> 'investment_sub_type', '') is null
            )
        )
);

create table if not exists raw.raw_transactions (
    id bigserial primary key,
    raw_transaction_id text not null,
    payload jsonb not null,
    source_system text not null default 'cloudflare_r2',
    source_bucket text not null,
    source_object_key text not null,
    source_file_path text not null,
    dt date not null,
    batch_id text not null,
    raw_record_hash text not null,
    loaded_at timestamptz not null default now(),
    constraint ck_raw_transactions_account_id_format
        check ((payload ->> 'account_id') ~ '^A[0-9]{6}$'),
    constraint ck_raw_transactions_customer_id_format
        check ((payload ->> 'customer_id') ~ '^C[0-9]{5}$')
);

create table if not exists raw.raw_product_events (
    id bigserial primary key,
    raw_product_event_id text not null,
    payload jsonb not null,
    source_system text not null default 'cloudflare_r2',
    source_bucket text not null,
    source_object_key text not null,
    source_file_path text not null,
    dt date not null,
    batch_id text not null,
    raw_record_hash text not null,
    loaded_at timestamptz not null default now()
);

create table if not exists raw.raw_kyc_applications (
    id bigserial primary key,
    raw_kyc_application_id text not null,
    payload jsonb not null,
    source_system text not null default 'cloudflare_r2',
    source_bucket text not null,
    source_object_key text not null,
    source_file_path text not null,
    dt date not null,
    batch_id text not null,
    raw_record_hash text not null,
    loaded_at timestamptz not null default now()
);
