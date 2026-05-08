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


create table if not exists raw.raw_merchants (
    id bigserial primary key,
    raw_merchant_id text not null,
    merchant_id text,
    payload jsonb not null,
    source_system text not null default 'cloudflare_r2',
    source_bucket text not null,
    source_object_key text not null,
    source_file_path text not null,
    dt date not null,
    batch_id text not null,
    raw_record_hash text not null,
    loaded_at timestamptz not null default now(),
    constraint ck_raw_merchants_merchant_id_format
        check (merchant_id is null or merchant_id ~ '^M[0-9]{6}$'),
    constraint ck_raw_merchants_risk_tier
        check ((payload ->> 'risk_tier') in ('low', 'medium', 'high'))
);

-- Keep manually created raw.raw_merchants compatible with the ingestion-owned DDL.
alter table raw.raw_merchants add column if not exists raw_merchant_id text;
alter table raw.raw_merchants add column if not exists merchant_id text;
alter table raw.raw_merchants add column if not exists payload jsonb;
alter table raw.raw_merchants add column if not exists source_system text default 'cloudflare_r2';
alter table raw.raw_merchants add column if not exists source_bucket text;
alter table raw.raw_merchants add column if not exists source_object_key text;
alter table raw.raw_merchants add column if not exists source_file_path text;
alter table raw.raw_merchants add column if not exists dt date;
alter table raw.raw_merchants add column if not exists batch_id text;
alter table raw.raw_merchants add column if not exists raw_record_hash text;
alter table raw.raw_merchants add column if not exists loaded_at timestamptz default now();

alter table raw.raw_merchants alter column raw_merchant_id set not null;
alter table raw.raw_merchants alter column payload set not null;
alter table raw.raw_merchants alter column source_system set not null;
alter table raw.raw_merchants alter column source_system set default 'cloudflare_r2';
alter table raw.raw_merchants alter column source_bucket set not null;
alter table raw.raw_merchants alter column source_object_key set not null;
alter table raw.raw_merchants alter column source_file_path set not null;
alter table raw.raw_merchants alter column dt set not null;
alter table raw.raw_merchants alter column batch_id set not null;
alter table raw.raw_merchants alter column raw_record_hash set not null;
alter table raw.raw_merchants alter column loaded_at set not null;
alter table raw.raw_merchants alter column loaded_at set default now();

do $$
begin
    if not exists (
        select 1 from pg_constraint
        where conname = 'ck_raw_merchants_merchant_id_format'
          and conrelid = 'raw.raw_merchants'::regclass
    ) then
        alter table raw.raw_merchants
            add constraint ck_raw_merchants_merchant_id_format
            check (merchant_id is null or merchant_id ~ '^M[0-9]{6}$');
    end if;

    if not exists (
        select 1 from pg_constraint
        where conname = 'ck_raw_merchants_risk_tier'
          and conrelid = 'raw.raw_merchants'::regclass
    ) then
        alter table raw.raw_merchants
            add constraint ck_raw_merchants_risk_tier
            check ((payload ->> 'risk_tier') in ('low', 'medium', 'high'));
    end if;
end $$;

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

create unique index if not exists ux_raw_product_events_raw_product_event_id
    on raw.raw_product_events (raw_product_event_id);
create unique index if not exists ux_raw_kyc_applications_raw_kyc_application_id
    on raw.raw_kyc_applications (raw_kyc_application_id);

create index if not exists idx_raw_product_events_batch_id on raw.raw_product_events (batch_id);
create index if not exists idx_raw_product_events_dt on raw.raw_product_events (dt);

create index if not exists idx_raw_kyc_applications_batch_id on raw.raw_kyc_applications (batch_id);
create index if not exists idx_raw_kyc_applications_dt on raw.raw_kyc_applications (dt);
create index if not exists idx_raw_product_events_customer_id on raw.raw_product_events ((payload->>'customer_id'));
create index if not exists idx_raw_product_events_account_id on raw.raw_product_events ((payload->>'account_id'));
create index if not exists idx_raw_kyc_applications_customer_id on raw.raw_kyc_applications ((payload->>'customer_id'));


create index if not exists idx_raw_merchants_batch_id on raw.raw_merchants (batch_id);
create index if not exists idx_raw_merchants_dt on raw.raw_merchants (dt);
create index if not exists idx_raw_merchants_merchant_id on raw.raw_merchants (merchant_id);
