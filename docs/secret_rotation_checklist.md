# Secret Rotation Checklist (Neon + Mixpanel)

Use this checklist whenever credentials are exposed, shared in logs/chats, or due for routine rotation.

## Scope
Rotate and validate:
- Neon database password
- Mixpanel service-account secret

---

## 1) Rotate Neon database password

### A. Rotate in Neon
1. Sign in to Neon console.
2. Open the FinSight project/database credentials area.
3. Rotate or reset the database user password used by FinSight.
4. Copy the updated connection string securely.

### B. Update local and remote environments
Update all locations that depend on Neon credentials:
- Local `.env.dbt`
- Local `.env.mixpanel`
- VM Airflow env: `/opt/finsight-ae/airflow/.env.airflow`
- GitHub Actions repository/environment secrets (if used)

Suggested fields to verify:
- `NEON_DATABASE_URL`
- `DATABASE_URL` (if still used anywhere)
- `DBT_PG_PASSWORD` (if profile uses discrete dbt env vars)

### C. Validate after update
1. Run dbt debug locally.
2. Run dbt debug inside the Airflow container.
3. Run Mixpanel sync in dry-run mode.
4. Run one real sync test.
5. Confirm Airflow task success and no auth/connection errors.

---

## 2) Rotate Mixpanel service-account credentials

### A. Create/rotate service account
1. In Mixpanel project settings, create a new service account, or rotate/recreate the current one.
2. Copy **username** and **secret** immediately (secret is often shown once).

### B. Update environments
Update credential locations:
- Local `.env.mixpanel`
- VM Airflow env: `/opt/finsight-ae/airflow/.env.airflow`
- GitHub Actions secrets (if Mixpanel sync is ever run there)

Required variables:
- `MIXPANEL_SERVICE_ACCOUNT_USER`
- `MIXPANEL_SERVICE_ACCOUNT_SECRET`

### C. Validate credentials directly
Run a quick auth check:

```python
import requests

resp = requests.get("https://mixpanel.com/api/app/me", auth=(user, secret))
print(resp.status_code)
```

Expected result: `STATUS 200`.

### D. Validate pipeline end-to-end
1. Run dry run.
2. Run one real sync.
3. Verify Mixpanel Import API response is successful.
4. Verify sync entries are logged with success in `metadata.mixpanel_sync_log`.

### E. Decommission old credentials
- Delete or disable old Mixpanel service account **only after** the new one is confirmed working.

---

## 3) Post-rotation hardening
- Confirm real secrets are not committed to git history.
- Ensure `.env*` runtime secret files remain git-ignored.
- Restrict file permissions on VM secret files (e.g., owner-only read/write).
- Record rotation date/time and operator in internal ops notes.
- Optionally schedule periodic rotation (e.g., quarterly).
