{{
    config(
        materialized = 'table'
    )
}}

with customers as (

    select *
    from {{ ref('stg_customers') }}

),

accounts as (

    select *
    from {{ ref('stg_accounts') }}

),

transactions as (

    select *
    from {{ ref('fct_transactions') }}

),

account_summary as (

    select
        customer_id,

        count(*) as account_count,
        count(distinct account_id) as distinct_account_count,

        count(
            case
                when lower(account_status) in ('active', 'open') then 1
            end
        ) as active_account_count,

        min(opened_at) as first_account_opened_at,
        max(opened_at) as latest_account_opened_at

    from accounts

    group by customer_id

),

transaction_summary as (

    select
        customer_id,

        count(*) as transaction_count,
        count(distinct transaction_id) as distinct_transaction_count,

        count(
            case
                when is_successful_transaction then 1
            end
        ) as successful_transaction_count,

        count(
            case
                when not is_successful_transaction then 1
            end
        ) as failed_transaction_count,

        sum(amount) as gross_transaction_volume,
        sum(successful_transaction_amount) as successful_transaction_volume,
        sum(failed_transaction_amount) as failed_transaction_volume,

        avg(amount) as avg_transaction_amount,
        min(transaction_timestamp) as first_transaction_at,
        max(transaction_timestamp) as latest_transaction_at

    from transactions

    group by customer_id

),

final as (

    select
        c.customer_id,

        coalesce(a.account_count, 0) as account_count,
        coalesce(a.distinct_account_count, 0) as distinct_account_count,
        coalesce(a.active_account_count, 0) as active_account_count,
        a.first_account_opened_at,
        a.latest_account_opened_at,

        coalesce(t.transaction_count, 0) as transaction_count,
        coalesce(t.distinct_transaction_count, 0) as distinct_transaction_count,
        coalesce(t.successful_transaction_count, 0) as successful_transaction_count,
        coalesce(t.failed_transaction_count, 0) as failed_transaction_count,

        coalesce(t.gross_transaction_volume, 0) as gross_transaction_volume,
        coalesce(t.successful_transaction_volume, 0) as successful_transaction_volume,
        coalesce(t.failed_transaction_volume, 0) as failed_transaction_volume,
        t.avg_transaction_amount,
        t.first_transaction_at,
        t.latest_transaction_at,

        case
            when coalesce(a.account_count, 0) > 0 then true
            else false
        end as has_accounts,

        case
            when coalesce(t.transaction_count, 0) > 0 then true
            else false
        end as has_transactions,

        current_timestamp as modeled_at

    from customers c

    left join account_summary a
        on c.customer_id = a.customer_id

    left join transaction_summary t
        on c.customer_id = t.customer_id

)

select *
from final