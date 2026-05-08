# Data Dictionary

## Raw layer (`raw` schema)

### raw.raw_customers
- **Purpose:** Landed raw customer payloads from R2.
- **Grain:** One ingested raw customer record.
- **Source models:** Ingestion pipeline (R2 object payload).
- **Materialization:** Physical raw table (ingestion-managed).
- **Key columns:** `dt`, `batch_id`, `payload`, `source_object_key`, `raw_record_hash`.
- **Important tests:** `dt`/`batch_id`/`payload`/`source_object_key` not null; `raw_record_hash` not null + unique.

### raw.raw_accounts
- **Purpose:** Landed raw account payloads from R2.
- **Grain:** One ingested raw account record.
- **Source models:** Ingestion pipeline (R2 object payload).
- **Materialization:** Physical raw table (ingestion-managed).
- **Key columns:** `dt`, `batch_id`, `payload`, `source_object_key`, `raw_record_hash`.
- **Important tests:** `dt`/`batch_id`/`payload`/`source_object_key` not null; `raw_record_hash` not null + unique.

### raw.raw_transactions
- **Purpose:** Landed raw transaction payloads from R2.
- **Grain:** One ingested raw transaction record.
- **Source models:** Ingestion pipeline (R2 object payload).
- **Materialization:** Physical raw table (ingestion-managed).
- **Key columns:** `dt`, `batch_id`, `payload`, `source_object_key`, `raw_record_hash`.
- **Important tests:** `dt`/`batch_id`/`payload`/`source_object_key` not null; `raw_record_hash` not null + unique.

## Staging layer (`dbt_rad.stg_*`)

### stg_customers
- **Purpose:** Typed/cleaned customer records from raw source payload.
- **Grain:** One row per customer.
- **Source models:** `source('raw', 'raw_customers')`.
- **Materialization:** `view`.
- **Key columns:** `customer_id`.
- **Important tests:** `customer_id` not null + unique.

### stg_accounts
- **Purpose:** Typed/cleaned account records with customer linkage and canonical subtype fallback logic.
- **Grain:** One row per account, deduped by `account_id` using latest `loaded_at`, `dt`, and `batch_id` ordering.
- **Source models:** `source('raw', 'raw_accounts')`.
- **Materialization:** `view`.
- **Key columns:** `account_id`, `customer_id`, `account_type`, `account_sub_type`, `plan_tier`.
- **Subtype contract:** `account_type` stays broad, `account_sub_type` is canonical, and `plan_tier` is independent. Legacy raw `investment_sub_type` may backfill missing investment subtypes only; `is_investment_sub_type` is intentionally not used.
- **Important tests:** `account_id` not null + unique; `customer_id` relationships to `stg_customers.customer_id`; `account_type`, `account_sub_type`, and `plan_tier` relationships to lookup seeds; account subtype/account type consistency test.

### stg_transactions
- **Purpose:** Typed/cleaned transaction records with account/customer linkage.
- **Grain:** One row per transaction, deduped by `transaction_id` using latest `loaded_at`, `dt`, and `batch_id` ordering.
- **Source models:** `source('raw', 'raw_transactions')`.
- **Materialization:** `view`.
- **Key columns:** `transaction_id`, `account_id`, `customer_id`, `amount`, `transaction_status`.
- **Important tests:** `transaction_id` not null + unique; `account_id` and `customer_id` relationship tests; accepted status domain.

## Reference seeds (`dbt_rad` seed tables)

### account_types
- **Purpose:** Lookup for broad account types and their labels/groups.
- **Grain:** One row per `account_type`.

### account_sub_types
- **Purpose:** Lookup for canonical account subtypes. Every `account_sub_type` maps to exactly one valid parent `account_type`, replacing any need for investment-subtype flags.
- **Grain:** One row per `account_sub_type`.

### plan_tiers
- **Purpose:** Lookup for plan tiers and paid-tier attributes. Plan tier is separate from account type and subtype.
- **Grain:** One row per `plan_tier`.

### transaction_types, transaction_statuses, signup_channels, kyc_statuses
- **Purpose:** Domain lookups used by staging relationship tests and downstream labels/status attributes.
- **Grain:** One row per domain value.

## Intermediate layer (`dbt_rad.int_*`)

### int_customers
- **Purpose:** Trusted customer base table for downstream joins.
- **Grain:** One row per customer.
- **Source models:** `stg_customers`.
- **Materialization:** `table`.
- **Key columns:** `customer_id`.
- **Important tests:** `customer_id` not null + unique.

### int_accounts
- **Purpose:** Trusted account base table enriched with account type, account subtype, and plan tier lookup labels/groups.
- **Grain:** One row per account.
- **Source models:** `stg_accounts`.
- **Materialization:** `table`.
- **Key columns:** `account_id`.
- **Important tests:** `account_id` not null + unique.

### int_transactions
- **Purpose:** Trusted transaction base table.
- **Grain:** One row per transaction.
- **Source models:** `stg_transactions`.
- **Materialization:** `table`.
- **Key columns:** `transaction_id`.
- **Important tests:** `transaction_id` not null + unique; custom non-negative amount test.

### int_customer_accounts
- **Purpose:** Canonical customer-account relationship table.
- **Grain:** One row per customer-account pair.
- **Source models:** `int_customers`, `int_accounts`.
- **Materialization:** `table`.
- **Key columns:** `customer_id`, `account_id`.
- **Important tests:** Inherited via source integrity and join logic checks.

### int_transactions_enriched
- **Purpose:** Transaction-level truth table enriched with account/customer context.
- **Grain:** One row per transaction.
- **Source models:** `int_transactions`, `int_account_enriched`, `int_customers`, transaction lookup seeds.
- **Materialization:** `table`.
- **Key columns:** `transaction_id`, `account_id`, `customer_id`, `transaction_date`, `amount`, `transaction_status`.
- **Important tests:** `transaction_id` not null + unique.

### int_daily_finance_metrics
- **Purpose:** Daily/currency financial KPI components and metrics.
- **Grain:** One row per (`transaction_date`, `currency`).
- **Source models:** `int_transactions_enriched`.
- **Materialization:** `table`.
- **Key columns:** `transaction_date`, `currency`, KPI columns.
- **Important tests:** `transaction_date` not null; `currency` not null.

## MRT layer (`dbt_rad.mrt_*`)

### mrt_rp__finance_daily_transactions
- **Purpose:** Reporting-ready transaction detail view for finance use cases.
- **Grain:** One row per transaction.
- **Source models:** `int_transactions_enriched`.
- **Materialization:** `view`.
- **Key columns:** `transaction_id`, dimensional and status fields.
- **Important tests:** `transaction_id` not null.

### mrt_rp__daily_kpis
- **Purpose:** Reporting view of daily KPI metrics.
- **Grain:** One row per (`transaction_date`, `currency`).
- **Source models:** `int_daily_finance_metrics`.
- **Materialization:** `view`.
- **Key columns:** `transaction_date`, `currency`, KPI fields.
- **Important tests:** `transaction_date` not null; `currency` not null.

### mrt_rp__customer_account_summary
- **Purpose:** Reporting view combining customer-account entities with transaction activity.
- **Grain:** One row per customer-account-transaction combination (left join preserves customer-account rows).
- **Source models:** `int_customer_accounts`, `int_transactions_enriched`.
- **Materialization:** `view`.
- **Key columns:** `customer_id`, `account_id`, `transaction_id`, `transaction_date`, `amount`.
- **Important tests:** Covered by upstream `int_*` entity integrity and join behavior checks.
