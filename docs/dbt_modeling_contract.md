# dbt Modeling Contract

## Schema ownership
- `raw` is ingestion-owned.
- `dbt_fs` is dbt-owned.
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
- `mrt_rp_<dept>_<model>`: reporting views only, organized under `models/mart/report/<department>/`.

## Materialization rules
- Staging (`stg_*`) => `view`
- Intermediate (`int_*`) => `table`
- MART/report (`mrt_rp_<dept>_<model>`) => `view`

## Logic placement rules
- All joins belong in `int_*` models.
- All calculations and enrichment belong in `int_*` models.
- Reusable metric components belong in `int_*` models.
- `mrt_rp_<dept>_<model>` models must remain thin (report-ready projection only).

## Naming rules
- Use one mart root folder: `models/mart/`. Do not create parallel `models/marts/` or `models/mrt/` roots.
- Use `mrt_rp_<dept>_<model>` for report-serving mart models.
- Department code examples: `core`, `fin`, `prod`, `grw`, and `risk`.
- Use `dim_` and `fct_` after the department code when it helps future semantic-layer or Cube modeling.
