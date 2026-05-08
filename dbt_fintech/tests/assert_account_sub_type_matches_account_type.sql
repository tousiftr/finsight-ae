select a.*
from {{ ref('stg_accounts') }} a
left join {{ ref('account_sub_types') }} s
  on a.account_sub_type = s.account_sub_type
 and a.account_type = s.account_type
where s.account_sub_type is null
