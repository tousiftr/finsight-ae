$ErrorActionPreference = "Stop"

Write-Host "Running dbt current analytics slice..."

docker run --rm `
  --env-file .env.dbt `
  -v "${PWD}/dbt_fintech:/usr/app" `
  finsight-dbt:local build --profiles-dir . --select staging int_transactions_enriched fct_transactions mrt_finance_daily_transactions mrt_finance_daily_kpis mrt_customer_account_summary

Write-Host "dbt build completed successfully."