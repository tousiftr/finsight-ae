with ranked_kyc as (
    select
        customer_id,
        kyc_application_id,
        kyc_status,
        kyc_level,
        document_type,
        review_channel,
        reviewer_type,
        risk_score,
        submitted_at,
        reviewed_at,
        rejection_reason,
        row_number() over (
            partition by customer_id
            order by coalesce(reviewed_at, submitted_at) desc
        ) as rn
    from {{ ref('stg_kyc_applications') }}
)

select
    customer_id,
    kyc_application_id,
    kyc_status,
    kyc_level,
    document_type,
    review_channel,
    reviewer_type,
    risk_score,
    submitted_at,
    reviewed_at,
    rejection_reason
from ranked_kyc
where rn = 1
