select *
from {{ ref('stg_accounts') }}
where
    (account_type = 'investment' and investment_sub_type is null)
    or (account_type <> 'investment' and investment_sub_type is not null)
