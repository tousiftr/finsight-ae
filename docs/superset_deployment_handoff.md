# FinSight Superset Deployment Handoff

## Current project status

FinSight Analytics backend pipeline is working enough to move into dashboard publishing.

Current working pieces:

- Python live data generator is state-aware and generates realistic fintech data.
- Neon raw tables are loading data.
- dbt staging, intermediate, snapshots, and marts are implemented.
- dbt models are intended to live in one analytics schema: `dbt_fs`.
- Superset is connected locally to Neon successfully.
- Superset can see the `dbt_fs` schema and at least one mart dataset, including `mrt_transactions`.
- First dashboard focus is transaction analytics.

## Current local Superset status

Superset is running locally through Docker on the PC.

Local URL:

```text
http://localhost:8088
```

Database connection:

- Database: Neon Postgres
- Schema for dashboarding: `dbt_fs`
- Do not use raw tables for dashboards.
- Use dbt mart/view datasets such as `mrt_transactions` first.

First dataset selected successfully:

```text
mrt_transactions
```

Recommended first dashboard:

```text
FinSight Transactions Dashboard
```

Recommended first transaction charts:

- Total Transactions
- Gross Transaction Volume
- Fee Revenue
- Transaction Success Rate
- Daily Transaction Count
- Daily Transaction Volume
- Transaction Status Breakdown
- Transaction Type Breakdown
- Transaction Volume by Merchant Category
- Failed and Declined Transactions table

## Netlify note

Netlify can publish the portfolio page, screenshots, documentation, and dashboard exports.

Netlify cannot directly host Apache Superset because Superset is a Python/Docker web app, not a static site.

Best Netlify use now:

- Add Superset dashboard screenshots.
- Add architecture diagram.
- Add GitHub Actions screenshots.
- Add dbt lineage/docs screenshots.
- Add explanation of the pipeline.
- Link to GitHub repo.

Future public page:

```text
iamrad.info/projects/finsight-analytics
```

## Online Superset deployment goal

Desired online architecture:

```text
Oracle Cloud Always Free VPS
-> Docker + Apache Superset
-> Neon Postgres dbt_fs marts
-> dashboard.iamrad.info
-> Netlify portfolio page links to screenshots or protected dashboard
```

## Oracle Cloud attempt status

Oracle Cloud setup was attempted using:

- Region: Singapore West
- Image: Canonical Ubuntu 24.04
- Shape: VM.Standard.A1.Flex
- Size attempted: 2 OCPU / 12 GB RAM
- Smaller fallback attempted/planned: 1 OCPU / 6 GB RAM
- Public IPv4 must be set to Yes
- SSH key was generated through Oracle

Oracle returned this error:

```text
Out of capacity for shape VM.Standard.A1.Flex in availability domain AD-1.
Create the instance in a different availability domain or try again later.
```

Interpretation:

- Configuration was mostly correct.
- The failure is Oracle free capacity, not a FinSight or Superset error.
- Singapore West AD-1 currently has no available Always Free Ampere A1 capacity.

Recommended Oracle retry order:

1. VM.Standard.A1.Flex, 1 OCPU / 6 GB RAM, public IPv4 Yes, fault domain automatic.
2. Try another availability domain if available.
3. Retry later, especially morning/night.
4. Avoid E2 Micro for Superset if possible because it is too weak.

## Temporary publishing options

Option A, recommended now:

```text
Local Superset -> screenshots -> Netlify project page
```

Option B, temporary interactive demo from PC:

```powershell
cloudflared tunnel --url http://localhost:8088
```

This requires the PC and Docker Desktop to stay on.

Option C, permanent interactive dashboard later:

```text
Oracle Always Free VPS or cheap VPS -> Superset Docker -> Neon -> dashboard subdomain
```

## Next prompt should continue from here

Suggested next prompt:

```text
Continue from my FinSight Superset deployment handoff. Oracle A1 in Singapore West was out of capacity. Help me either retry Oracle later, create a Netlify portfolio page with Superset screenshots, or set up Cloudflare Tunnel for a temporary dashboard demo.
```
