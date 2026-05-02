select
    transaction_id,
    amount
from {{ ref('int_transactions') }}
where amount < 0
