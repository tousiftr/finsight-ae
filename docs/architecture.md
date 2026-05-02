# Architecture

## Current implemented architecture

```text
GitHub Actions
  -> Python micro-batch generator
  -> Cloudflare R2 (finsight-raw)
  -> Neon Postgres raw tables (schema: raw)
  -> dbt models in schema dbt_rad:
       - stg_* (views)
       - int_* (tables)
       - mrt_* (views)
```

## Component responsibilities
- **GitHub Actions**: schedules/runs ingestion and dbt workflows.
- **Python generators/loaders**: create raw micro-batches and execute load steps.
- **Cloudflare R2**: durable raw landing zone.
- **Neon Postgres (`raw`)**: ingestion-owned raw persistence.
- **dbt (`dbt_rad`)**: transformation and analytics-layer modeling.

## Data ownership and boundaries
- `raw` schema is ingestion-owned and should not be used for business logic.
- `dbt_rad` schema is dbt-owned and contains modeled analytics outputs.
- No extra schemas are part of current architecture.

## Future architecture (not implemented yet)
The following are planned later and are **not** currently implemented:
- Superset for dashboarding/BI consumption
- Cube for semantic serving
- Airflow and/or Dagster for advanced orchestration
- AI-assisted analytics capabilities
