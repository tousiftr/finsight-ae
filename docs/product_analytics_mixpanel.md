# Product Analytics Hourly Lane + Mixpanel Export

## Architecture
- **Daily warehouse lane**: keep broad intermediate/mart refreshes on daily cadence.
- **Hourly product analytics lane**: run only dbt models tagged `product_analytics_hourly`, then run optional Python sync.
- **Mixpanel integration path**: Airflow runs Python script that reads modeled events from Neon/dbt output and sends to Mixpanel Import API (future implementation).

## dbt hourly tag strategy
The following models are tagged `product_analytics_hourly` and intended for hourly refresh:
- `int_kyc_funnel`
- `int_daily_user_activity`
- `mrt_rp_prod_activation`
- `mrt_rp_prod_daily_active_users`
- `mrt_rp_prod_fct_daily_product_activity`
- `mixpanel_events_export`

Use selector:
```bash
dbt build --select tag:product_analytics_hourly
```

For daily broad refreshes (if/when wired in Airflow):
```bash
dbt build --select path:models/intermediate path:models/mart --exclude tag:product_analytics_hourly
```

## Mixpanel export model columns
`mixpanel_events_export` emits one event row per record with:
- `source_event_id`
- `event_name`
- `distinct_id` (customer_id as text)
- `event_time`
- `insert_id` (deterministic md5 hash)
- `event_source`
- `event_properties` (JSONB context, no direct PII)

Supported normalized event names (only when source data exists):
- User Registered
- KYC Submitted
- KYC Approved
- KYC Rejected
- Account Activated
- Feature Used
- Transaction Started
- Transaction Completed

## Airflow hourly DAG
DAG: `finsight_product_analytics_hourly`
- Schedule: hourly (`0 * * * *`)
- `catchup=False`
- `max_active_runs=1`
- Task order: `dbt_build_product_analytics >> sync_mixpanel_events`

Environment variable defaults:
- `DBT_PROJECT_DIR=/opt/finsight-ae/dbt_fintech`
- `DBT_PRODUCT_ANALYTICS_SELECTOR=tag:product_analytics_hourly`
- `MIXPANEL_SYNC_SCRIPT=/opt/finsight-ae/product_analytics/sync_neon_to_mixpanel.py`

## Environment variables
- `NEON_DATABASE_URL`
- `MIXPANEL_PROJECT_ID`
- `MIXPANEL_SERVICE_ACCOUNT_USER`
- `MIXPANEL_SERVICE_ACCOUNT_SECRET`
- `MIXPANEL_REGION` (default `api`)
- `MIXPANEL_BATCH_SIZE` (default `1000`)

## Local test flow
1. `dbt ls --select tag:product_analytics_hourly`
2. `dbt build --select tag:product_analytics_hourly`
3. `python /opt/finsight-ae/product_analytics/sync_neon_to_mixpanel.py`
4. `airflow dags test finsight_product_analytics_hourly 2026-05-25`

## PII safety guardrails
Do **not** send:
- Full names
- Email addresses
- Phone numbers
- Postal addresses
- Government/document numbers

Only include operational/product context needed for analytics.

## Example Mixpanel funnels
1. `User Registered -> KYC Submitted -> KYC Approved -> Account Activated`
2. `Account Activated -> Feature Used -> Transaction Completed`
