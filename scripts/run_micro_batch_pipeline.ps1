$ErrorActionPreference = "Stop"

Write-Host "Generating realistic FinSight raw micro-batch..."
python data_generator/generate_micro_batch.py

Write-Host "Uploading micro-batch files to Cloudflare R2..."
python scripts/upload_micro_batch_to_r2.py

Write-Host "Loading latest customers from R2 to Neon raw..."
python loaders/load_customers_r2_to_neon.py --latest

Write-Host "Loading latest accounts from R2 to Neon raw..."
python loaders/load_accounts_r2_to_neon.py --latest

Write-Host "Loading latest transactions from R2 to Neon raw..."
python loaders/load_transactions_r2_to_neon.py --latest

Write-Host "Verifying raw customers..."
python loaders/verify_raw_customers_loaded.py

Write-Host "Verifying raw accounts and transactions..."
python loaders/verify_raw_accounts_transactions_loaded.py

Write-Host "Raw micro-ingestion completed successfully. No dbt was run."