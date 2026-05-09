# Current Project State

## Raw ingestion status
- Raw micro-ingestion is active via GitHub Actions.
- Schedule cadence is every 10 minutes.
- Ingestion produces raw micro-batch files for loading.
- Merchant and transaction generators use hourly UTC batch partitions with randomized event timestamps inside the batch window.

## Object storage (R2)
- Active bucket: `finsight-raw`.
- Raw batch files land in R2 before warehouse loading.

## Raw tables (Neon)
Raw data is loaded into the `raw` schema:
- `raw.raw_customers`
- `raw.raw_accounts`
- `raw.raw_merchants`
- `raw.raw_transactions`

## dbt workflow status
- dbt runs in its own GitHub Actions workflow.
- Local dbt build has been validated.
- Neon materialization expectations have been validated.
- Row-count and relationship validations have been executed.
- GitHub dbt workflow run has been triggered and checked.

## Current schema strategy
Only two schemas are used:
- `raw` (ingestion-owned)
- `dbt_fs` (dbt-owned)

No additional schemas are allowed.

## Current model layers
Within `dbt_fs`:
- `stg_*` = source-cleaned views
- `int_*` = trusted base-truth tables
- `mrt_*` = reporting/dashboard views

## Validated materializations
- `stg_*` models materialize as `VIEW`
- `int_*` models materialize as `BASE TABLE`
- `mrt_*` models materialize as `VIEW`

## Completed validation checklist
- [x] `dbt debug`
- [x] `dbt parse`
- [x] `dbt ls`
- [x] `dbt build`
- [x] Materialization type checks in Neon
- [x] Row count checks
- [x] Relationship integrity checks
- [x] GitHub dbt workflow verification

## Not started yet
- Superset implementation
- Cube implementation
- Airflow orchestration
- Dagster orchestration
- AI layer / ML-assisted analytics components
