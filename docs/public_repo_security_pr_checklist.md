# Public repository security PR checklist

Use this checklist before opening or merging public PRs. The goal is to keep the public portfolio repository useful without exposing private infrastructure, credentials, customer data, or operational secrets.

## Secrets and private configuration

- [ ] No `.env`, `profiles.yml`, `secrets.toml`, private keys, certificates, Caddy production config, or real credentials are committed.
- [ ] No Neon, Mixpanel, Cloudflare R2, SMTP, Airflow, Superset, or Caddy secrets are present in code, docs, logs, screenshots, workflow files, or examples.
- [ ] Example files such as `.env.example`, `.env.*.example`, `*.env.example`, and `dbt_fintech/profiles.yml.example` contain placeholders only.
- [ ] Any required local values are documented as placeholders and stored only in local `.env` files, GitHub Secrets, Airflow connections, or VM-only configuration.

## Data and screenshots

- [ ] No real customer data, transaction data, emails, phone numbers, IP addresses, access tokens, account IDs, or other personal or sensitive data are included.
- [ ] Screenshots are reviewed for visible credentials, connection strings, session cookies, Basic Auth headers, URLs with tokens, private hostnames, email addresses, and production data.
- [ ] Generated sample data is synthetic and safe for public display.

## GitHub Actions and automation

- [ ] Workflows do not echo secrets, run `printenv`, enable `set -x`, dump full environment variables, or send secrets to external URLs.
- [ ] Workflows use least-privilege `permissions` blocks and do not request write permissions unless the workflow genuinely requires them.
- [ ] PRs touching `.github/workflows/**` receive extra manual review for secret handling, third-party actions, permissions, and data exfiltration risk.
- [ ] Third-party actions are reviewed before use and pinned to a trusted release or version where practical.

## Required checks before merge

- [ ] Secret scanning passes before merge.
- [ ] `dbt parse`, `dbt build`, or `dbt test` passes where relevant to the change.
- [ ] Local and CI checks do not print secrets or write generated credentials back into the repository.
- [ ] The PR description calls out any security-sensitive files changed and any manual review performed.
