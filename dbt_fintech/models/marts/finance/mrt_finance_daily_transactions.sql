{{
    config(
        materialized = 'table'
    )
}}

with transactions as (

    select *
    from {{ ref('fct_transactions') }}

),

daily as (

    select
        transaction_date,
        currency,

        count(*) as transaction_count,
        count(distinct transaction_id) as distinct_transaction_count,
        count(distinct customer_id) as active_customer_count,
        count(distinct account_id) as active_account_count,

        sum(amount) as total_transaction_amount,
        avg(amount) as avg_transaction_amount,

        sum(successful_transaction_amount) as successful_transaction_amount,
        sum(failed_transaction_amount) as failed_transaction_amount,

        sum(
            case
                when is_successful_transaction then 1
                else 0
            end
        ) as successful_transaction_count,

        sum(
            case
                when not is_successful_transaction then 1
                else 0
            end
        ) as failed_transaction_count,

        round(
            sum(
                case
                    when is_successful_transaction then 1
                    else 0
                end
            )::numeric / nullif(count(*), 0),
            4
        ) as transaction_success_rate,

        min(transaction_timestamp) as first_transaction_at,
        max(transaction_timestamp) as last_transaction_at,
        min(loaded_at) as first_loaded_at,
        max(loaded_at) as last_loaded_at

    from transactions

    group by
        transaction_date,
        currency

)

select *
from daily