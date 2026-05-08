# dbt Modeling Contract

## Schema ownership
- `raw` is ingestion-owned.
- `dbt_rad` is dbt-owned.
- No extra schemas may be introduced.

## Account subtype contract
- `account_type` remains the broad account category.
- `account_sub_type` is the canonical subtype used by intermediate models and marts.
- `plan_tier` is modeled separately from account type/subtype.
- Raw payloads may still include legacy `investment_sub_type`; staging may only use it to backfill missing investment `account_sub_type`.
- `account_sub_types` maps each subtype to exactly one valid parent `account_type`; the subtype/account-type consistency test enforces that mapping.
- `is_investment_sub_type` is intentionally not created or used.

## Layer definitions
- `stg_*`: 1-to-1 source-cleaned views.
- `int_*`: trusted business truth tables.
- `mrt_*`: reporting views only.

## Materialization rules
- Staging (`stg_*`) => `view`
- Intermediate (`int_*`) => `table`
- MRT (`mrt_*`) => `view`

## Logic placement rules
- All joins belong in `int_*` models.
- All calculations and enrichment belong in `int_*` models.
- Reusable metric components belong in `int_*` models.
- `mrt_*` must remain thin (report-ready projection only).

## Naming rules
- Do not use the word `mart` in model naming.
- Use `mrt` naming only for reporting layer models.
