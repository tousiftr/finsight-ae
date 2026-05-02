{{
    config(
        materialized = 'table'
    )
}}

with daily_transactions as (

    select *
    from {{ ref('mrt_finance_daily_transactions') }}

),

daily_kpis as (

    select
        transaction_date,

        sum(transaction_count) as total_transactions,
        sum(distinct_transaction_count) as distinct_transactions,
        sum(active_customer_count) as active_customers,
        sum(active_account_count) as active_accounts,

        sum(total_transaction_amount) as gross_transaction_volume,
        sum(total_transaction_amount) / nullif(sum(transaction_count), 0) as avg_transaction_amount,

        sum(successful_transaction_amount) as successful_transaction_volume,
        sum(failed_transaction_amount) as failed_transaction_volume,

        sum(successful_transaction_count) as successful_transactions,
        sum(failed_transaction_count) as failed_transactions,

        round(
            sum(successful_transaction_count)::numeric / nullif(sum(transaction_count), 0),
            4
        ) as transaction_success_rate,

        min(first_transaction_at) as first_transaction_at,
        max(last_transaction_at) as last_transaction_at,
        min(first_loaded_at) as first_loaded_at,
        max(last_loaded_at) as last_loaded_at

    from daily_transactions
    group by transaction_date

)

select *
from daily_kpis
