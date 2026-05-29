# FinSight Analytics

## Project overview
**FinSight Analytics: Live Fintech Analytics Engineering Platform** is a portfolio-grade analytics engineering project for a synthetic fintech company. It simulates customers, accounts, merchants, transactions, and product event data, then operationalizes that data across ingestion, transformation, orchestration, and activation workflows.

The platform now includes GitHub Actions, Python generators/loaders, Cloudflare R2, Neon Postgres, dbt, Airflow, Dagster, Mixpanel, Caddy, and orchestration email alerting.

## Latest milestone
- Airflow and Dagster are both implemented on VM infrastructure and are actively used for orchestration.
- Mixpanel Import API integration is working and successfully imported 100 product events with HTTP 200.
- Email alerting has been created for orchestration monitoring in both Airflow and Dagster contexts.
- Airflow Gmail SMTP alert test succeeded using a private recipient configured outside the repository, and logs confirmed: `Sent an alert email`.
- VM-hosted orchestration services are fronted by Caddy reverse proxy with protected access controls.

## What is working now
- [x] GitHub Actions ingestion workflows are active for synthetic data generation and raw loading.
- [x] Raw fintech batches land in Cloudflare R2.
- [x] Raw data loads into Neon Postgres `raw` schema.
- [x] dbt transformations run in `dbt_fs` using staging, intermediate, and reporting layers.
- [x] dbt source freshness checks, snapshots, model runs, and tests are orchestrated through Dagster.
- [x] Airflow is running in Docker on VM infrastructure for operational workflows.
- [x] Airflow Mixpanel sync orchestration is active with retries and logs.
- [x] Mixpanel product analytics activation is implemented through the Import API.
- [x] Mixpanel sync outcomes are tracked in `metadata.mixpanel_sync_log`.
- [x] Dagster UI is hosted at `dagster.iamrad.info` behind Caddy and Basic Auth.
- [x] Email alerting is configured and tested for orchestration observability.

## Current architecture
```text
GitHub Actions
  -> Python synthetic fintech micro-batch generator
  -> Cloudflare R2 raw landing zone
  -> Neon Postgres raw schema
  -> dbt models in dbt_fs
     -> stg_* views
     -> int_* truth tables
     -> mrt_rp_<dept>_<model> reporting views

Airflow (VM-hosted, Docker)
  -> Operational orchestration
  -> Mixpanel sync workflows
  -> Retries, logs, email alerts

Dagster (VM-hosted)
  -> dbt orchestration and lineage/asset graph
  -> Source freshness, snapshots, model runs, tests
  -> Orchestration observability and alerting

Mixpanel
  -> Import API activation target for product events
  -> Sync audit trail in metadata.mixpanel_sync_log

Caddy
  -> Reverse proxy, SSL termination, protected service access
```

## Tool responsibilities
- **GitHub Actions:** Ingestion orchestration and CI/CD-style pipeline automation.
- **Airflow:** Operational orchestration and Mixpanel sync execution.
- **Dagster:** dbt orchestration, lineage, asset visibility, and dbt-oriented scheduling.
- **dbt:** Transformations, tests, and strict modeling/materialization contract.
- **Neon Postgres:** Analytics warehouse for `raw` and `dbt_fs` schemas.
- **Cloudflare R2:** Raw object storage and landing zone for ingestion batches.
- **Mixpanel:** Product analytics activation destination.
- **Caddy:** Reverse proxy and SSL for VM-hosted UIs/services.

## Current workflows
### GitHub Actions
- Live ingestion
- Raw loading
- dbt source freshness workflow
- Staging builds
- Intermediate workflow
- Mart/reporting workflow

### Airflow
- Operational workflows
- Mixpanel sync
- Retries, logs, and email alerts

### Dagster
- dbt orchestration
- Lineage and asset graph
- Source freshness
- Snapshots
- Model and test execution
- Alerting and observability

## dbt modeling contract
### Schema ownership
- `raw` schema: ingestion-owned only
- `dbt_fs` schema: dbt-owned only

### Layering and naming
- `stg_*`: source-cleaned views
- `int_*`: trusted reusable business truth tables
- `mrt_rp_<dept>_<model>`: thin reporting/dashboard views

### Materialization contract
- Staging = `view`
- Intermediate = `table`
- Mart/reporting = `view`

## Operational observability and alerting
- Airflow operational runs include retry behavior, task logs, and email alerts for monitoring workflow health.
- Airflow Gmail SMTP delivery was tested successfully, with logs confirming alert dispatch.
- Dagster is used as an orchestration observability layer for dbt assets, lineage, scheduled execution, and monitoring context.
- Dagster alerting setup is documented as an internal orchestration monitoring capability, not a public feature endpoint.
- SMTP and notification credentials should be managed securely, preferably via Airflow connection or secret management patterns, not hardcoded configuration.

## Security notes
- No secrets are committed to the repository.
- No `.env` files are committed.
- No Neon credentials are committed.
- No Mixpanel secrets are committed.
- No SMTP credentials are committed.
- UI access is protected with Basic Auth where applicable.

## Public repo security
- This public repository uses example environment files only; real credentials must never be committed.
- Store real credentials in local `.env` files, GitHub Secrets, Airflow connections, or VM-only configuration.
- Never commit `dbt_fintech/profiles.yml`, `airflow/.env`, `airflow/.env.airflow`, `.streamlit/secrets.toml`, private keys, or production Caddy config.
- Run gitleaks before merging public PRs, and treat any finding as a release blocker until it is remediated.

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

## Next steps
- Finish README and docs cleanup so all documentation reflects current implemented orchestration state.
- Add screenshots for Airflow, Dagster, Mixpanel, and end-to-end pipeline status.
- Build BI/dashboard consumption from the current mart layer.
- Add a pipeline health dashboard for operations visibility.
- Expand automated data quality checks.
- Add failure and SLA alert documentation.
- Later, add a Cube semantic layer.
- Later, add an AI assistant layer.

## Documentation sync note
Some docs may still reflect earlier planning-state language for Airflow or Dagster. README now reflects the implemented state, and remaining docs should be synchronized in a follow-up documentation pass.
