with latest_raw as (
    select
        payload ->> 'account_id' as account_id,
        nullif(payload ->> 'plan_tier', '') as raw_plan_tier,
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
  and r.raw_plan_tier is not null
  and a.plan_tier is null
