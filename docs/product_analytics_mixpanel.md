# Product Analytics to Mixpanel (Manual First)

## Architecture
Neon Postgres  
→ dbt product/KYC models  
→ `dbt_fs.mixpanel_events_export`  
→ `product_analytics/sync_neon_to_mixpanel.py`  
→ Mixpanel Import API  
→ (Later) Airflow hourly DAG

## Why Python Import API (not Warehouse Connector)
This implementation is intentionally based on Mixpanel Import API so it works with the free Mixpanel plan and allows strict event-volume control via batch limits.

## Free-plan-safe event volume strategy
- Export model emits only core product/KYC milestones.
- Sync script reads only `MIXPANEL_BATCH_SIZE` rows per run (default `20`).
- Manual run first; scale frequency only after validation in Mixpanel Live View.

## dbt export model (`mixpanel_events_export`) columns
- `source_event_id`
- `event_name`
- `distinct_id` (customer_id as text)
- `event_time` (real source timestamp)
- `insert_id` (deterministic hash)
- `event_source`
- `event_properties` (JSONB, non-PII)

## PII exclusions
Excluded from payload:
- full name
- email
- phone
- address
- document numbers
- other raw identity fields

## Environment variables
- `NEON_DATABASE_URL`
- `MIXPANEL_PROJECT_ID=1d824830977ff0a48a92d961828f7e93`
- `MIXPANEL_SERVICE_ACCOUNT_USER`
- `MIXPANEL_SERVICE_ACCOUNT_SECRET`
- `MIXPANEL_REGION=api`
- `MIXPANEL_BATCH_SIZE=20`
- `MIXPANEL_EXPORT_TABLE=dbt_fs.mixpanel_events_export`

## Manual validation commands
```bash
cd /opt/finsight-ae/airflow

docker compose exec airflow-webserver bash -lc '
cd /opt/finsight-ae/dbt_fintech
dbt ls --select tag:product_analytics_hourly
'

docker compose exec airflow-webserver bash -lc '
cd /opt/finsight-ae/dbt_fintech
dbt build --select tag:product_analytics_hourly
'

docker compose exec airflow-webserver bash -lc '
python - <<PY
import os
import pg8000.dbapi
from urllib.parse import urlparse, unquote

url = os.environ["NEON_DATABASE_URL"]
p = urlparse(url)

conn = pg8000.dbapi.connect(
    user=unquote(p.username or ""),
    password=unquote(p.password or ""),
    host=p.hostname,
    port=p.port or 5432,
    database=unquote(p.path.lstrip("/")),
    ssl_context=True,
)

cur = conn.cursor()
cur.execute("""
select
    event_name,
    count(*) as event_count,
    min(event_time) as first_event_time,
    max(event_time) as last_event_time
from dbt_fs.mixpanel_events_export
group by event_name
order by event_count desc;
""")

for row in cur.fetchall():
    print(row)

cur.close()
conn.close()
PY
'
```

Manual sync:
```bash
cd /opt/finsight-ae/airflow

docker compose exec airflow-webserver bash -lc '
cd /opt/finsight-ae
set -a
source /opt/finsight-ae/.env.mixpanel
set +a
python product_analytics/sync_neon_to_mixpanel.py
'
```

## Later Airflow integration plan (after manual success)
Hourly DAG steps:
1. `dbt build --select tag:product_analytics_hourly`
2. `python product_analytics/sync_neon_to_mixpanel.py`

## Example Mixpanel funnels
- `User Registered -> KYC Submitted -> KYC Approved -> Account Activated`
- `Account Activated -> Feature Used -> Transaction Completed`
