# FinSight Analytics

## Project overview
FinSight Analytics is a data platform project focused on reliable raw ingestion and governed analytics modeling in Neon Postgres using dbt. The current implementation is production-oriented for ingestion and transformation foundations, with strict schema and modeling contracts.

## Current architecture
Current implemented flow:

1. GitHub Actions schedules and runs ingestion jobs (every 10 minutes).
2. Python micro-batch generators create raw domain files.
3. Raw files are uploaded to Cloudflare R2 bucket `finsight-raw`.
4. Raw files are loaded into Neon Postgres `raw` schema tables.
5. dbt transforms raw data into `stg_*`, `int_*`, and `mrt_*` models in `dbt_fs`.

## Current pipeline status
- ✅ Raw micro-ingestion is running through GitHub Actions.
- ✅ Raw ingestion cadence is every 10 minutes.
- ✅ Raw objects land in Cloudflare R2 (`finsight-raw`).
- ✅ Raw data loads into Neon `raw` tables.
- ✅ dbt is executed through a separate GitHub Actions workflow.
- ✅ Local dbt build has been validated.
- ✅ Neon materializations are validated.
- ✅ Row counts and relationships are validated.
- ✅ GitHub dbt workflow has been triggered and checked.

## Tech stack
- **Orchestration (current):** GitHub Actions
- **Ingestion:** Python micro-batch scripts
- **Object storage:** Cloudflare R2
- **Warehouse:** Neon Postgres
- **Transformations:** dbt (Postgres adapter)
- **Quality checks:** dbt tests + SQL validation queries

## Repository structure
```text
.
├── data_generator/                  # Synthetic/source-like batch generation
├── object_storage/                  # R2 upload and manifest helpers
├── loaders/                         # Raw table DDL and load/verify scripts
├── scripts/                         # Local/ops helper scripts
├── dbt_fintech/
│   ├── models/
│   │   ├── sources/                 # source() declarations for raw schema
│   │   ├── staging/                 # stg_* source-cleaned views
│   │   ├── intermediate/            # int_* trusted business truth tables
│   │   └── mrt/
│   │       └── rp/                  # current reporting mrt_* views
│   ├── tests/                       # custom dbt tests
│   ├── macros/
│   └── profiles.yml.example
└── docs/
    ├── architecture.md
    ├── current_state.md
    ├── data_dictionary.md
    ├── dbt_modeling_contract.md
    ├── dbt_validation_runbook.md
    ├── metric_definitions.md
    └── next_steps.md
```

## dbt layer design
### Schema strategy (strict)
- `raw` = ingestion-owned only
- `dbt_fs` = dbt-owned only
- No extra schemas

### Layering and naming
- `raw.raw_*`: landed raw source tables
- `dbt_fs.stg_*`: source-cleaned views (1-to-1 reshaping/typing)
- `dbt_fs.int_*`: trusted, reusable business truth tables
- `dbt_fs.mrt_*`: thin reporting/dashboard views

### Materialization contract
- Staging: `view`
- Intermediate: `table`
- MRT: `view`

### Modeling contract
All joins, calculations, enrichment, and reusable metric components belong in `int_*`. MRT models must remain thin and only expose reporting-ready selects from intermediate models.

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
   - `mrt_*` => `VIEW`
2. Validate row counts between critical lineage steps.
3. Validate relationship integrity (e.g., transactions to accounts/customers).

See `docs/dbt_validation_runbook.md` for exact commands and SQL.

## Completed milestones
- Raw micro-batch ingestion pipeline implemented and scheduled.
- R2 raw landing operational (`finsight-raw`).
- Neon raw loading and validations operational.
- dbt source/staging/intermediate/mrt layers implemented.
- Core relationship and data quality tests implemented.
- Local and GitHub dbt executions validated.

## Next planned steps
- Improve dbt test depth and coverage.
- Improve model and column-level documentation.
- Generate and review dbt docs regularly.
- Add additional source domains incrementally.
- Move to BI serving only after dbt quality is stable.

## Planned MRT organization
Current MRT models live under `dbt_fintech/models/mrt/rp/`. To keep growth organized while preserving current naming contracts, the intended folder strategy is:

- `models/mrt/mrt_report/finance/` for finance reporting views
- `models/mrt/mrt_report/project/` for project/ops reporting views
- `models/mrt/mrt_cube/` reserved for semantic/analytics-serving preparation later

This is a planned organizational structure; no new tool stack is implemented yet.

## Explicitly not implemented yet
Superset, Cube, Airflow, Dagster, and AI components are intentionally deferred until the dbt core is mature and stable.
