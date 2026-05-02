# Metric Definitions

Source metric model: `int_daily_finance_metrics`.
Reporting exposure model: `mrt_rp__daily_kpis`.

## transaction_count
- **Business definition:** Total number of transactions for a day and currency.
- **SQL logic / formula:** `count(*)`
- **Source model:** `int_daily_finance_metrics` (derived from `int_transactions_enriched`).
- **Reporting model:** `mrt_rp__daily_kpis`.

## approved_transaction_count
- **Business definition:** Number of transactions in approved/success-equivalent statuses.
- **SQL logic / formula:** `sum(case when lower(transaction_status) in ('approved', 'completed', 'success', 'succeeded') then 1 else 0 end)`
- **Source model:** `int_daily_finance_metrics`.
- **Reporting model:** `mrt_rp__daily_kpis`.

## declined_transaction_count
- **Business definition:** Number of declined transactions.
- **SQL logic / formula:** `sum(case when lower(transaction_status) = 'declined' then 1 else 0 end)`
- **Source model:** `int_daily_finance_metrics`.
- **Reporting model:** `mrt_rp__daily_kpis`.

## failed_transaction_count
- **Business definition:** Number of failed/error transactions.
- **SQL logic / formula:** `sum(case when lower(transaction_status) in ('failed', 'error') then 1 else 0 end)`
- **Source model:** `int_daily_finance_metrics`.
- **Reporting model:** `mrt_rp__daily_kpis`.

## approved_transaction_amount
- **Business definition:** Total approved/success-equivalent transaction amount.
- **SQL logic / formula:** `sum(case when lower(transaction_status) in ('approved', 'completed', 'success', 'succeeded') then amount else 0 end)`
- **Source model:** `int_daily_finance_metrics`.
- **Reporting model:** `mrt_rp__daily_kpis`.

## average_approved_transaction_amount
- **Business definition:** Average amount of approved/success-equivalent transactions.
- **SQL logic / formula:** `avg(case when lower(transaction_status) in ('approved', 'completed', 'success', 'succeeded') then amount end)`
- **Source model:** `int_daily_finance_metrics`.
- **Reporting model:** `mrt_rp__daily_kpis`.

## transaction_success_rate
- **Business definition:** Share of total transactions that are approved/success-equivalent.
- **SQL logic / formula:** `sum(approved_flag)::numeric / nullif(count(*), 0)::numeric` where `approved_flag` follows approved/success-equivalent status rules.
- **Source model:** `int_daily_finance_metrics`.
- **Reporting model:** `mrt_rp__daily_kpis`.
