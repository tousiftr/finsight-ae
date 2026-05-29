$ErrorActionPreference = "Stop"

Write-Host "Running dbt current analytics slice..."

docker run --rm `
  --env-file .env.dbt `
  -v "${PWD}/dbt_fintech:/usr/app" `
  finsight-dbt:local build --profiles-dir . --select path:models/staging path:models/intermediate path:models/mart/report

Write-Host "dbt build completed successfully."