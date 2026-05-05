select *
from {{ ref('stg_accounts') }}
where
    (account_type <> 'investment' and investment_sub_type is not null)
    or (account_type = 'investment' and investment_sub_type not in ('crypto', 'etf', 'cfd', 'fx'))
    or (account_type = 'investment' and investment_sub_type is null)
