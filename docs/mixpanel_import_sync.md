# Mixpanel Import Sync (Local)

## What this script does
`product_analytics/sync_neon_to_mixpanel.py` reads a controlled batch of events from your Neon export table and sends them to the Mixpanel **Import API** using service account credentials from environment variables.

The script also creates and maintains a metadata log table:
- `metadata.mixpanel_sync_log`

This log table is used to:
- track successful/failed sends,
- store response status/body for troubleshooting,
- prevent re-importing events that already synced successfully.

## Required environment variables
- `NEON_DATABASE_URL`
- `MIXPANEL_PROJECT_ID`
- `MIXPANEL_SERVICE_ACCOUNT_USER`
- `MIXPANEL_SERVICE_ACCOUNT_SECRET`
- `MIXPANEL_REGION`
- `MIXPANEL_EXPORT_TABLE`

Optional but recommended:
- `MIXPANEL_BATCH_SIZE` (default: `20`)
- `MIXPANEL_DRY_RUN` (default: `true`)

## Dry run (safe default)
Dry run prepares events and prints a preview, but does **not** call Mixpanel and does **not** write sync logs.

```bash
set -a
source .env.mixpanel
set +a

export MIXPANEL_DRY_RUN=true
python product_analytics/sync_neon_to_mixpanel.py
```

## Real import
For real imports, explicitly disable dry run and set a controlled batch size.

```bash
set -a
source .env.mixpanel
set +a

export MIXPANEL_DRY_RUN=false
export MIXPANEL_BATCH_SIZE=100
python product_analytics/sync_neon_to_mixpanel.py
```

## How to check Mixpanel
1. Open your Mixpanel project.
2. Go to **Events** / event stream.
3. Confirm imported events appear with expected properties (`distinct_id`, `$insert_id`, `source_event_id`, etc.).

## Why `metadata.mixpanel_sync_log` exists
The sync log gives idempotency and observability:
- **Idempotency:** events with successful `insert_id` are skipped on future runs.
- **Observability:** each attempted event is recorded with `success` or `failed` and response details.

## Next step reminder
This workflow is intentionally local-first for safe testing. Airflow automation comes later.
