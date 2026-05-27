# FinSight Airflow Sidecar

This folder adds Apache Airflow as a safe sidecar for FinSight Analytics.

It is intentionally **not** the production scheduler yet.

## What this does

- Runs Airflow with Docker Compose.
- Mounts the existing repository into the Airflow containers at `/opt/finsight-ae`.
- Adds one manual-only DAG: `finsight_airflow_healthcheck`.
- Checks Python, dbt, dbt debug, dbt parse, and dbt ls.

## What this does not do

- Does not change GitHub Actions.
- Does not generate data.
- Does not upload files to Cloudflare R2.
- Does not load data into Neon.
- Does not run `dbt build`.
- Does not replace the existing working pipeline.

## First-time VM setup

Clone the repo on the VM:

```bash
cd /opt
sudo git clone https://github.com/tousiftr/finsight-ae.git
sudo chown -R $USER:$USER /opt/finsight-ae
cd /opt/finsight-ae
```

Create the Airflow environment file:

```bash
cd airflow
cp .env.example .env
```

Edit `.env` and set real values for:

- `AIRFLOW_ADMIN_PASSWORD`
- `AIRFLOW_SECRET_KEY`
- Neon/dbt environment variables
- R2 variables only when a future DAG needs R2 access

Start Airflow:

```bash
docker compose build
docker compose up airflow-init
docker compose up -d
```

Open Airflow locally on the VM:

```text
http://127.0.0.1:8082
```

The webserver is bound to localhost only:

```yaml
127.0.0.1:8082:8080
```

This prevents Docker from exposing Airflow directly to the internet.

## Updating code from GitHub

For now, update the VM manually:

```bash
cd /opt/finsight-ae
git pull origin main
cd airflow
docker compose restart airflow-scheduler
```

If requirements, Dockerfile, or Compose changed:

```bash
cd /opt/finsight-ae/airflow
docker compose build
docker compose up -d
```

## Recommended public URL later

Use a separate subdomain:

```text
https://airflow.iamrad.info
```

Recommended access chain:

```text
Nginx reverse proxy
→ optional Cloudflare Access or IP allowlist
→ Airflow login
```

Do not expose Airflow's container port directly to the public internet.

## Safe validation checklist

1. Airflow UI opens.
2. Login works.
3. DAG `finsight_airflow_healthcheck` appears.
4. DAG is paused by default.
5. Manual DAG run succeeds.
6. Existing GitHub Actions pipeline remains unchanged.

Only after this sidecar is stable should a separate pipeline DAG be added.

## Mixpanel hourly sync configuration (March 2026 onward)

Airflow runs the Mixpanel product analytics sync hourly using `airflow/dags/finsight_product_analytics_hourly.py`, which executes `product_analytics/sync_neon_to_mixpanel.py`.

Key environment controls:

- `MIXPANEL_BACKFILL_START_AT`: lower bound for eligible `event_time` rows (inclusive).
- `MIXPANEL_BATCH_SIZE`: max events sent per run.
- `MIXPANEL_DRY_RUN`: when `true`, prepares events without sending to Mixpanel.

Production target for this project is syncing events from **2026-03-01 00:00:00 onward** with **2000 events per hourly run**.

The sync is idempotent because successful `$insert_id` values are tracked in `metadata.mixpanel_sync_log`, and already successful rows are excluded from future sends.

### Safe validation command

```bash
cd /opt/finsight-dagster
set -a
source airflow/.env.airflow
set +a

python product_analytics/sync_neon_to_mixpanel.py
```

Expected dry-run output includes:

- `Batch size: 2000`
- `Backfill start at: 2026-03-01 00:00:00`
- `Dry run: True`
- `Prepared N event(s)`
- `MIXPANEL_DRY_RUN=true, no events sent.`

Expected real-sync output includes:

- `Batch size: 2000`
- `Backfill start at: 2026-03-01 00:00:00`
- `Dry run: False`
- `Prepared N event(s)`
- `Mixpanel response status: 200`
- `Successfully sent N events to Mixpanel.`

### VM deployment commands

Run after pulling latest code:

```bash
cd /opt/finsight-dagster
git pull origin main

grep -q '^MIXPANEL_BATCH_SIZE=' airflow/.env.airflow \
  && sed -i 's/^MIXPANEL_BATCH_SIZE=.*/MIXPANEL_BATCH_SIZE=2000/' airflow/.env.airflow \
  || echo 'MIXPANEL_BATCH_SIZE=2000' >> airflow/.env.airflow

grep -q '^MIXPANEL_BACKFILL_START_AT=' airflow/.env.airflow \
  && sed -i 's/^MIXPANEL_BACKFILL_START_AT=.*/MIXPANEL_BACKFILL_START_AT=2026-03-01 00:00:00/' airflow/.env.airflow \
  || echo 'MIXPANEL_BACKFILL_START_AT=2026-03-01 00:00:00' >> airflow/.env.airflow

grep -q '^MIXPANEL_DRY_RUN=' airflow/.env.airflow \
  && sed -i 's/^MIXPANEL_DRY_RUN=.*/MIXPANEL_DRY_RUN=true/' airflow/.env.airflow \
  || echo 'MIXPANEL_DRY_RUN=true' >> airflow/.env.airflow

grep -E "MIXPANEL_BATCH_SIZE|MIXPANEL_BACKFILL_START_AT|MIXPANEL_DRY_RUN" airflow/.env.airflow
```

### Safe dry-run then real-sync runbook

```bash
cd /opt/finsight-dagster
set -a
source airflow/.env.airflow
set +a
python product_analytics/sync_neon_to_mixpanel.py
```

If dry run output looks correct, enable real sync:

```bash
sed -i 's/^MIXPANEL_DRY_RUN=.*/MIXPANEL_DRY_RUN=false/' airflow/.env.airflow
```

Restart Airflow:

```bash
cd /opt/finsight-dagster/airflow
docker compose restart
docker compose ps
```

Run one manual real batch:

```bash
cd /opt/finsight-dagster
set -a
source airflow/.env.airflow
set +a
python product_analytics/sync_neon_to_mixpanel.py
```

### Optional March backfill loop

Stop early when output indicates no rows found.

```bash
cd /opt/finsight-dagster
set -a
source airflow/.env.airflow
set +a

for i in {1..20}; do
  echo "===== Mixpanel March backfill batch $i ====="
  python product_analytics/sync_neon_to_mixpanel.py
  echo
 done
```

### Verification helper

Use `scripts/check_mixpanel_sync_status.py` to verify sync coverage/status for events with `event_time >= 2026-03-01`.
