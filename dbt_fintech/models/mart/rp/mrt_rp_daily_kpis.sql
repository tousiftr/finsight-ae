select
    transaction_date,
    currency,
    transaction_count,
    approved_transaction_count,
    declined_transaction_count,
    failed_transaction_count,
    approved_transaction_amount,
    average_approved_transaction_amount,
    transaction_success_rate
from {{ ref('int_daily_finance_metrics') }}
