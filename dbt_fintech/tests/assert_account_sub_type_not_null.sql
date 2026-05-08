with latest_raw as (
    select
        payload ->> 'account_id' as account_id,
        nullif(payload ->> 'account_sub_type', '') as raw_account_sub_type,
        nullif(payload ->> 'investment_sub_type', '') as raw_investment_sub_type,
        row_number() over (
            partition by payload ->> 'account_id'
            order by loaded_at desc, dt desc, batch_id desc
        ) as rn
    from {{ source('raw', 'raw_accounts') }}
)
select a.*
from {{ ref('stg_accounts') }} a
inner join latest_raw r
    on a.account_id = r.account_id
where r.rn = 1
  and a.account_sub_type is null
  and (
      r.raw_account_sub_type is not null
      or (
          a.account_type = 'investment'
          and r.raw_investment_sub_type is not null
      )
  )
