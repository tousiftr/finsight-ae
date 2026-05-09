{% snapshot snap_customers %}

{{
    config(
        target_schema='snapshots',
        unique_key='customer_id',
        strategy='timestamp',
        updated_at='updated_at'
    )
}}

select
    customer_id,
    first_name,
    last_name,
    email,
    phone,
    phone_number,
    date_of_birth,
    country,
    city,
    signup_channel,
    customer_segment,
    employment_status,
    income_band,
    risk_segment,
    kyc_status,
    created_at,
    updated_at,
    loaded_at
from {{ ref('stg_customers') }}

{% endsnapshot %}
