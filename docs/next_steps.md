# Next Steps

1. Improve dbt tests
   - Expand singular and generic tests around business rules.
   - Add edge-case tests for transaction statuses and metric stability.

2. Improve model and column documentation
   - Add richer descriptions in schema YAML files.
   - Improve ownership and semantic clarity for each column.

3. Generate and review dbt docs
   - Run `dbt docs generate` and `dbt docs serve` during review cycles.
   - Validate lineage graph and exposures for consistency.

4. Add more source domains later
   - Incrementally onboard additional raw domains.
   - Keep schema and layering contracts unchanged (`raw`, `dbt_rad`).

5. After dbt quality is stable, move to Superset
   - Begin BI/dashboard integration only after dbt test/documentation maturity is achieved.
