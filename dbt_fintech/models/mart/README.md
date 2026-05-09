# MART Folder Organization

All mart models live under this single `mart` root. This removes the previous split between `mart`, `marts`, and `mrt` folders so report consumers and future semantic-layer work have one predictable location.

## Current reporting marts

Reporting models are grouped by department under `report/<department>/` and follow this naming contract:

```text
mrt_rp_<dept>_<model_name>
```

Naming components:

- `mrt` = mart model
- `rp` = report-serving model
- `<dept>` = short department/domain code
- `<model_name>` = business-readable model name, optionally using `dim_` or `fct_` where helpful for future semantic/cube modeling

Current department codes:

- `core` for shared customer/account dimensions and summaries
- `fin` for finance reporting
- `prod` for product reporting
- `grw` for growth reporting
- `risk` for risk reporting

## Future semantic layer

Keep report-ready views thin and stable. If Cube or another semantic layer is added later, it should build from these consistently named mart views and/or a sibling semantic-serving area under this same `mart` root instead of creating another top-level `marts` or `mrt` folder.
