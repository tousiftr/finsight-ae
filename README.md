# FinSight Analytics

## Project overview
FinSight Analytics is a live fintech analytics engineering platform that simulates fintech product, customer, account, transaction, and behavioral event data. The pipeline lands raw data into Cloudflare R2, loads it into Neon Postgres, transforms it with dbt, validates it with dbt tests, syncs product events to Mixpanel, and orchestrates operational/dbt workflows using Airflow and Dagster.

The project is designed as a portfolio-grade analytics engineering platform demonstrating ingestion, transformation, orchestration, observability, product analytics, and governed reporting.

## Architecture
### Core components
- **GitHub repository:** Main codebase and CI/CD control point.
- **GitHub Actions:** Raw data generation, Cloudflare R2 upload, and Neon raw loading.
- **Cloudflare R2:** Raw zone for landed synthetic fintech batches.
- **Neon Postgres:** Primary analytical warehouse (`raw` + `dbt_fs` modeling layers).
- **dbt:** Staging, intermediate, mart/reporting models, and data tests.
- **Airflow (VM-hosted):** Operational orchestration, especially Mixpanel sync.
- **Dagster (VM-hosted):** dbt asset/lineage orchestration, freshness, snapshots, model runs, and test orchestration.
- **Mixpanel Import API:** Product event delivery target for analytics activation.
- **Caddy:** Reverse proxy + SSL termination for VM-hosted services.

### Pipeline flow diagram (text)
```text
[GitHub Actions]
    -> Generate synthetic fintech raw batches
    -> Upload raw files to Cloudflare R2
    -> Load raw files into Neon Postgres (raw schema)

[Dagster]
    -> dbt source freshness checks (every 30 minutes)
    -> dbt snapshots (daily, pre-model run)
    -> dbt intermediate models (daily @ 12:30 PM Asia/Dhaka)
    -> dbt mart/reporting models (daily, after intermediate)
    -> dbt tests (post-refresh validation; separate from model builds)

[Airflow]
    -> Hourly Mixpanel operational sync orchestration
    -> Calls Mixpanel Import API for eligible events
    -> Writes sync metadata to metadata.mixpanel_sync_log

[Consumers]
    -> Analytics-ready marts in Neon
    -> Product analytics events in Mixpanel
```

## Latest milestone (Airflow + Dagster + Mixpanel)
- Airflow is running on VM infrastructure and actively orchestrating operational jobs.
- Mixpanel Import API integration is operational; 100 events were imported successfully with HTTP 200.
- Mixpanel sync observability is in place via `metadata.mixpanel_sync_log`.
- Dagster is installed, hosted, and connected to dbt orchestration workloads.
- `dagster.iamrad.info` is configured behind Caddy reverse proxy and protected with Basic Auth.
- Dagster code is committed/pushed and used for dbt lineage/asset-aware scheduled operations.

## What is working now
- [x] GitHub repo is active and used as the main codebase.
- [x] Synthetic fintech data pipeline is working.
- [x] Raw data lands in Cloudflare R2 before Neon loading.
- [x] Neon Postgres is the active warehouse.
- [x] dbt models run successfully.
- [x] dbt intermediate models build successfully.
- [x] dbt mart/reporting models build successfully.
- [x] dbt tests pass successfully.
- [x] Airflow is running on the VM.
- [x] Airflow is orchestrating Mixpanel sync and operations.
- [x] Mixpanel Import API integration is working.
- [x] Mixpanel imported 100 events successfully (status 200).
- [x] Mixpanel sync logs are tracked in `metadata.mixpanel_sync_log`.
- [x] Dagster is installed and hosted on VM.
- [x] `dagster.iamrad.info` is configured via Caddy + Basic Auth.
- [x] Dagster runs dbt orchestration jobs.
- [x] Dagster is used for dbt lineage/assets and scheduled dbt operations.
- [x] Dagster code has been committed and pushed to GitHub.
- [x] GitHub SSH authentication from VM is configured and working.

## Current orchestration strategy
### GitHub Actions (ingestion orchestration)
- Generates synthetic raw domain datasets.
- Uploads raw artifacts to Cloudflare R2.
- Loads raw datasets into Neon `raw` tables.

### Airflow (operational orchestration)
- Owns hourly Mixpanel synchronization and operational workflows.
- Manages resilient retries/logging around operational tasks.

### Dagster (dbt orchestration + lineage)
- Owns dbt-centric orchestration and asset-aware execution.
- Handles source freshness, snapshots, model runs, and post-run test scheduling.
- Provides lineage and software-defined asset visibility for dbt assets.

### Target Dagster schedule design
- **dbt source freshness:** every 30 minutes.
- **dbt snapshot:** daily before model runs.
- **dbt intermediate models:** daily at 12:30 PM Asia/Dhaka.
- **dbt mart/reporting models:** daily after intermediate models.
- **dbt tests:** run after intermediate and mart refresh; tests are intentionally decoupled from build runs.

## dbt layer design
### Schema strategy (strict)
- `raw` = ingestion-owned only
- `dbt_fs` = dbt-owned only
- No extra schemas

### Layering and naming
- `raw.raw_*`: landed raw source tables
- `dbt_fs.stg_*`: source-cleaned views (1-to-1 reshaping/typing)
- `dbt_fs.int_*`: trusted, reusable business truth tables
- `dbt_fs.mrt_rp_<dept>_<model>`: thin reporting/dashboard views

### Materialization contract
- Staging: `view`
- Intermediate: `table`
- MRT: `view`

### Modeling contract
All joins, calculations, enrichment, and reusable metric components belong in `int_*`. MRT models remain thin and expose reporting-ready selects from intermediate models.

## Tech stack
- **Code + CI/CD:** GitHub, GitHub Actions
- **Ingestion:** Python micro-batch generators/loaders
- **Object storage:** Cloudflare R2
- **Warehouse:** Neon Postgres
- **Transformations:** dbt (Postgres adapter)
- **Operational orchestration:** Airflow
- **Analytics engineering orchestration + lineage:** Dagster
- **Product analytics activation:** Mixpanel Import API
- **Edge/reverse proxy:** Caddy

## Repository structure
```text
.
├── data_generator/                  # Synthetic/source-like batch generation
├── object_storage/                  # R2 upload and manifest helpers
├── loaders/                         # Raw table DDL and load/verify scripts
├── product_analytics/               # Mixpanel sync logic
├── scripts/                         # Local/ops helper scripts
├── airflow/                         # Airflow DAGs + deployment assets
├── dagster_project/                 # Dagster definitions and jobs
├── dbt_fintech/
│   ├── models/
│   │   ├── sources/                 # source() declarations for raw schema
│   │   ├── staging/                 # stg_* source-cleaned views
│   │   ├── intermediate/            # int_* trusted business truth tables
│   │   └── mart/report/             # reporting views: mrt_rp_<dept>_<model>
│   ├── snapshots/
│   ├── tests/                       # custom dbt tests
│   ├── macros/
│   └── profiles.yml.example
└── docs/                            # runbooks, architecture, milestones, next steps
```

## Security notes
- `.env` files and real environment-specific secrets are **not** committed.
- Neon credentials are **not** committed.
- Mixpanel project secrets/tokens are **not** committed.
- UI authentication passwords (Airflow/Dagster access controls) are **not** committed.
- Example configuration files remain sanitized for safe repository sharing.

## How to run dbt locally
From repository root:

```bash
cd dbt_fintech
cp profiles.yml.example profiles.yml
# set env vars: DBT_PG_HOST, DBT_PG_USER, DBT_PG_PASSWORD, DBT_PG_PORT, DBT_PG_DATABASE
dbt debug
dbt parse
dbt ls
dbt build
```

## How to validate Neon outputs
Use SQL checks after `dbt build`:
1. Validate expected materializations in `dbt_fs`:
   - `stg_*` => `VIEW`
   - `int_*` => `BASE TABLE`
   - `mrt_rp_*` => `VIEW`
2. Validate row counts between critical lineage steps.
3. Validate relationship integrity (e.g., transactions to accounts/customers).

See `docs/dbt_validation_runbook.md` for exact commands and SQL.

## Next steps
- Finalize and harden production Dagster schedules (freshness/snapshot/model/test cadence).
- Expand automated data quality checks and anomaly detection coverage.
- Add alerting/notification hooks for orchestration failures and SLA misses.
- Extend product analytics event taxonomy and downstream dashboard use-cases.
- Add curated BI consumption layer/documentation on top of current marts.
- Continue strengthening runbooks, observability, and incident response workflows.
