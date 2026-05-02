{{
    config(
        materialized = 'incremental',
        unique_key = 'transaction_id',
        on_schema_change = 'append_new_columns'
    )
}}

with transactions as (

    select *
    from {{ ref('stg_transactions') }}

    {% if is_incremental() %}
        where loaded_at > (
            select coalesce(max(loaded_at), '1900-01-01'::timestamptz)
            from {{ this }}
        )
    {% endif %}

),

accounts as (

    select *
    from {{ ref('stg_accounts') }}

),

customers as (

    select *
    from {{ ref('stg_customers') }}

),

enriched as (

    select
        t.transaction_id,
        t.account_id,
        t.customer_id,

        t.transaction_timestamp,
        t.amount,
        t.currency,
        t.transaction_type,
        t.transaction_status,

        a.account_type,
        a.account_status,
        a.opened_at as account_opened_at,

        case
            when t.amount > 0 then true
            else false
        end as is_positive_amount,

        case
            when lower(t.transaction_status) in ('completed', 'success', 'succeeded', 'approved')
                then true
            else false
        end as is_successful_transaction,

        t.dt,
        t.batch_id,
        t.source_object_key,
        t.source_file_path,
        t.raw_record_hash,
        t.loaded_at

    from transactions t

    left join accounts a
        on t.account_id = a.account_id

    left join customers c
        on t.customer_id = c.customer_id

)

select *
from enriched