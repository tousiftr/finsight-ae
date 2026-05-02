{{
    config(
        materialized = 'incremental',
        unique_key = 'transaction_id',
        on_schema_change = 'append_new_columns'
    )
}}

with transactions as (

    select *
    from {{ ref('int_transactions_enriched') }}

    {% if is_incremental() %}
        where loaded_at > (
            select coalesce(max(loaded_at), '1900-01-01'::timestamptz)
            from {{ this }}
        )
    {% endif %}

),

final as (

    select
        transaction_id,
        account_id,
        customer_id,

        transaction_timestamp,
        transaction_timestamp::date as transaction_date,
        extract(hour from transaction_timestamp)::int as transaction_hour,

        amount,
        currency,
        transaction_type,
        transaction_status,

        account_type,
        account_status,
        account_opened_at,

        is_positive_amount,
        is_successful_transaction,

        case
            when is_successful_transaction then amount
            else 0
        end as successful_transaction_amount,

        case
            when not is_successful_transaction then amount
            else 0
        end as failed_transaction_amount,

        dt as source_dt,
        batch_id,
        source_object_key,
        source_file_path,
        raw_record_hash,
        loaded_at

    from transactions

)

select *
from final