with latest_raw_accounts as (
    select
        payload ->> 'account_id' as account_id,
        lower(nullif(payload ->> 'account_type', '')) as account_type,
        nullif(payload ->> 'account_sub_type', '') as raw_account_sub_type,
        nullif(payload ->> 'investment_sub_type', '') as raw_investment_sub_type,
        row_number() over (
            partition by payload ->> 'account_id'
            order by loaded_at desc, dt desc, batch_id desc
        ) as rn
    from {{ source('raw', 'raw_accounts') }}
)

select
    s.account_id,
    s.account_type,
    s.account_sub_type,
    r.raw_account_sub_type,
    r.raw_investment_sub_type
from {{ ref('stg_accounts') }} s
inner join latest_raw_accounts r
    on s.account_id = r.account_id
    and r.rn = 1
where s.account_sub_type is null
  and (
      r.raw_account_sub_type is not null
      or (r.account_type = 'investment' and r.raw_investment_sub_type is not null)
  )
