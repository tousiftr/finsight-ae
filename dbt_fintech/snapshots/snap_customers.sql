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
    date_of_birth,
    country,
    city,
    created_at,
    updated_at,
    signup_channel,
    customer_segment,
    employment_status,
    income_band,
    risk_segment,
    kyc_status,
    source_file_path,
    dt,
    batch_id,
    loaded_at,
    ingested_at
from {{ ref('stg_customers') }}
where customer_id is not null

{% endsnapshot %}
