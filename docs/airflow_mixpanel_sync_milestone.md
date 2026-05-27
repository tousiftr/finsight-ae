# Airflow + Mixpanel Sync Milestone

## Purpose
This milestone operationalizes **automated product analytics export** from FinSight's warehouse to Mixpanel on an hourly schedule. The goal is to keep Mixpanel populated with fresh, analysis-ready product events for funnels, activation, and behavior monitoring—without manual exports.

Business and engineering value:
- Automated product analytics export reduces manual operational work.
- Hourly orchestration improves freshness for product decision-making.
- Duplicate-safe sync protects event quality and trust in analytics.
- Airflow provides operational visibility and rerun controls.
- Mixpanel-ready event stream supports funnels and activation analysis.

## Architecture

```text
Airflow DAG (finsight_mixpanel_hourly_sync)
  -> dbt product analytics build
  -> dbt_fs.mixpanel_events_export
  -> product_analytics/sync_neon_to_mixpanel.py
  -> Mixpanel Import API
  -> metadata.mixpanel_sync_log
```

## Deployment and Access
- Public/admin Airflow URL: `https://airflow.iamrad.info`
- Airflow access is protected by **Caddy HTTPS + basic auth**.
- Airflow webserver is bound locally on `127.0.0.1:8082` and is **not directly exposed**.
- VM project path: `/opt/finsight-ae`
- Repo mount path inside Airflow container: `/opt/airflow/finsight`

## DAG Configuration
- DAG name: `finsight_mixpanel_hourly_sync`
- Schedule: **hourly**
- Tasks:
  - `dbt_product_analytics_build`
  - `mixpanel_import_sync`

Expected runtime behavior:
- `MIXPANEL_BATCH_SIZE=100` for hourly processing slices.
- `MIXPANEL_DRY_RUN=false` for real hourly sync.
- Sync sends only unsynced events (0 to batch size depending on backlog).

## Validation Evidence (Confirmed)
- Mixpanel service-account auth test: `STATUS 200`
- Mixpanel Import API response:
  - `code: 200`
  - `num_records_imported: 100`
  - `status: OK`
- Sync script logs include:
  - `Logged 100 event(s) with sync_status='success'`
  - `Successfully sent 100 events to Mixpanel.`

## Duplicate Protection Logic
Duplicate protection is enforced through `metadata.mixpanel_sync_log`:
- The sync process records successful event insert IDs (`insert_id` / `$insert_id`).
- Before sending, the script filters out records already logged as `sync_status='success'`.
- Result: retried or subsequent runs avoid re-importing already successful events.

## Operations Runbook

### Check Airflow logs
1. Open `https://airflow.iamrad.info`.
2. Navigate to DAG `finsight_mixpanel_hourly_sync`.
3. Open the latest DAG Run.
4. Review task logs for:
   - `dbt_product_analytics_build`
   - `mixpanel_import_sync`
5. Confirm row-selection, API response status, and sync log inserts.

### Check Mixpanel Events
1. Open Mixpanel project.
2. Go to Events / Live View (or equivalent event explorer).
3. Filter for events expected from `dbt_fs.mixpanel_events_export`.
4. Verify event timestamps and count growth after DAG runs.

### Check `metadata.mixpanel_sync_log`
Run a warehouse query to validate status and duplicates:

```sql
select
  sync_status,
  count(*) as rows
from metadata.mixpanel_sync_log
group by 1
order by 1;
```

Optional recent-success check:

```sql
select *
from metadata.mixpanel_sync_log
where sync_status = 'success'
order by synced_at desc
limit 100;
```

### Pause / unpause DAG safely
- In Airflow UI, use the DAG toggle for `finsight_mixpanel_hourly_sync`.
- Before pausing, confirm no critical run is currently processing.
- After unpausing, optionally trigger a single manual run to confirm health.
- Avoid overlapping manual runs with active scheduled runs.

## Troubleshooting Notes
- **401 from Mixpanel API**
  - Usually invalid Mixpanel service-account credentials.
  - Re-check `MIXPANEL_SERVICE_ACCOUNT_USER` and `MIXPANEL_SERVICE_ACCOUNT_SECRET`.

- **Permission denied on `.env.airflow`**
  - File ownership/permissions on VM are incorrect.
  - Reassign ownership to the Airflow runtime user and tighten mode (e.g., `chmod 600`).

- **DAG run stuck in queued**
  - DAG may be paused, or `max_active_runs`/concurrency is blocked by another run.
  - Check DAG toggle, active runs, and scheduler health.

- **`/opt/airflow/finsight` missing in container**
  - Repo mount is missing from Docker Compose bind mounts.
  - Verify compose volume mapping and restart services.
