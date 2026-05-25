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
