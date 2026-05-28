import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from dagster import (
    DefaultSensorStatus,
    Definitions,
    Failure,
    MetadataValue,
    ScheduleDefinition,
    job,
    make_email_on_run_failure_sensor,
    op,
)


# ---------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------

def get_env(name: str, default: Optional[str] = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_optional_env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    return value if value not in (None, "") else default


def dbt_project_dir() -> Path:
    return Path(get_env("DBT_PROJECT_DIR", "/opt/finsight-ae/dbt_fintech")).resolve()


def dbt_profiles_dir() -> Path:
    return Path(get_env("DBT_PROFILES_DIR", "/opt/finsight-ae/dbt_fintech")).resolve()


def dbt_target() -> Optional[str]:
    return get_optional_env("DBT_TARGET", "prod")


# ---------------------------------------------------------------------
# Shared dbt runner
# ---------------------------------------------------------------------

def run_dbt_command(
    context,
    command_label: str,
    dbt_args: list[str],
    selector_env: Optional[str] = None,
    default_selector: Optional[str] = None,
) -> None:
    project_dir = dbt_project_dir()
    profiles_dir = dbt_profiles_dir()

    cmd = [
        "dbt",
        *dbt_args,
        "--project-dir",
        str(project_dir),
        "--profiles-dir",
        str(profiles_dir),
    ]

    target = dbt_target()
    if target:
        cmd.extend(["--target", target])

    selector = None
    if selector_env:
        selector = get_optional_env(selector_env, default_selector)
    elif default_selector:
        selector = default_selector

    if selector:
        cmd.extend(["--select", selector])

    context.log.info("Running %s command: %s", command_label, " ".join(cmd))

    result = subprocess.run(
        cmd,
        cwd=str(project_dir),
        text=True,
        capture_output=True,
        check=False,
    )

    if result.stdout:
        context.log.info("dbt stdout:\n%s", result.stdout)

    if result.stderr:
        context.log.warning("dbt stderr:\n%s", result.stderr)

    if result.returncode != 0:
        raise Failure(
            description=f"{command_label} failed.",
            metadata={
                "return_code": MetadataValue.int(result.returncode),
                "command": MetadataValue.text(" ".join(cmd)),
                "stdout_tail": MetadataValue.text(result.stdout[-4000:]),
                "stderr_tail": MetadataValue.text(result.stderr[-4000:]),
                "checked_at_utc": MetadataValue.text(datetime.utcnow().isoformat()),
            },
        )

    context.log.info("%s passed successfully.", command_label)


# ---------------------------------------------------------------------
# Healthcheck op
# ---------------------------------------------------------------------

@op
def dagster_dbt_healthcheck(context) -> dict:
    project_dir = dbt_project_dir()
    profiles_dir = dbt_profiles_dir()

    checks = {
        "dbt_project_dir": str(project_dir),
        "dbt_project_dir_exists": project_dir.exists(),
        "dbt_project_yml_exists": (project_dir / "dbt_project.yml").exists(),
        "dbt_profiles_dir": str(profiles_dir),
        "profiles_yml_exists": (profiles_dir / "profiles.yml").exists(),
    }

    context.log.info("Dagster dbt healthcheck: %s", checks)

    failed = [
        key
        for key, value in checks.items()
        if key.endswith("_exists") and value is False
    ]

    if failed:
        raise Failure(
            description=f"Dagster dbt healthcheck failed: {failed}",
            metadata={
                "dbt_project_dir": MetadataValue.path(str(project_dir)),
                "dbt_profiles_dir": MetadataValue.path(str(profiles_dir)),
                "checks": MetadataValue.json(checks),
            },
        )

    return checks


# ---------------------------------------------------------------------
# dbt ops
# ---------------------------------------------------------------------

@op
def run_dbt_source_freshness(context, checks: dict) -> None:
    run_dbt_command(
        context=context,
        command_label="dbt source freshness",
        dbt_args=["source", "freshness"],
        selector_env="DBT_SOURCE_FRESHNESS_SELECTOR",
        default_selector=None,
    )


@op
def run_dbt_intermediate_models(context, checks: dict) -> None:
    run_dbt_command(
        context=context,
        command_label="dbt intermediate daily build",
        dbt_args=["build"],
        selector_env="DBT_INTERMEDIATE_SELECTOR",
        default_selector="path:models/intermediate",
    )


@op
def run_dbt_mart_models(context, checks: dict) -> None:
    run_dbt_command(
        context=context,
        command_label="dbt mart daily build",
        dbt_args=["build"],
        selector_env="DBT_MART_SELECTOR",
        default_selector="path:models/marts",
    )


@op
def run_dbt_snapshots(context, checks: dict) -> None:
    run_dbt_command(
        context=context,
        command_label="dbt snapshot job",
        dbt_args=["snapshot"],
        selector_env="DBT_SNAPSHOT_SELECTOR",
        default_selector=None,
    )


@op
def run_dbt_tests(context, checks: dict) -> None:
    run_dbt_command(
        context=context,
        command_label="dbt tests daily job",
        dbt_args=["test"],
        selector_env="DBT_TEST_SELECTOR",
        default_selector=None,
    )


# ---------------------------------------------------------------------
# Dagster jobs
# ---------------------------------------------------------------------

@job(name="dbt_source_freshness_job")
def dbt_source_freshness_job():
    checks = dagster_dbt_healthcheck()
    run_dbt_source_freshness(checks)


@job(name="dbt_intermediate_daily_job")
def dbt_intermediate_daily_job():
    checks = dagster_dbt_healthcheck()
    run_dbt_intermediate_models(checks)


@job(name="dbt_mart_daily_job")
def dbt_mart_daily_job():
    checks = dagster_dbt_healthcheck()
    run_dbt_mart_models(checks)


@job(name="dbt_snapshot_job")
def dbt_snapshot_job():
    checks = dagster_dbt_healthcheck()
    run_dbt_snapshots(checks)


@job(name="dbt_tests_daily_job")
def dbt_tests_daily_job():
    checks = dagster_dbt_healthcheck()
    run_dbt_tests(checks)


# ---------------------------------------------------------------------
# Schedules
# UTC schedule.
# 20:30, 02:30, 08:30, 14:30 UTC = 02:30, 08:30, 14:30, 20:30 BDT
# ---------------------------------------------------------------------

dbt_source_freshness_schedule = ScheduleDefinition(
    job=dbt_source_freshness_job,
    cron_schedule="30 20,2,8,14 * * *",
    execution_timezone="UTC",
)

dbt_intermediate_daily_schedule = ScheduleDefinition(
    job=dbt_intermediate_daily_job,
    cron_schedule="0 21 * * *",
    execution_timezone="UTC",
)

dbt_mart_daily_schedule = ScheduleDefinition(
    job=dbt_mart_daily_job,
    cron_schedule="15 21 * * *",
    execution_timezone="UTC",
)

dbt_snapshot_daily_schedule = ScheduleDefinition(
    job=dbt_snapshot_job,
    cron_schedule="30 21 * * *",
    execution_timezone="UTC",
)

dbt_tests_daily_schedule = ScheduleDefinition(
    job=dbt_tests_daily_job,
    cron_schedule="45 21 * * *",
    execution_timezone="UTC",
)


# ---------------------------------------------------------------------
# Email alert sensor
# Main target: dbt_source_freshness_job
# ---------------------------------------------------------------------

def dagster_email_subject(context) -> str:
    return f"[FinSight Dagster Alert] Job failed: {context.dagster_run.job_name}"


def dagster_email_body(context) -> str:
    run = context.dagster_run

    failure_message = (
        context.failure_event.message
        if context.failure_event
        else "No failure event message available."
    )

    base_url = get_optional_env(
        "DAGSTER_WEBSERVER_BASE_URL",
        "https://dagster.iamrad.info",
    )

    run_url = (
        f"{base_url.rstrip('/')}/runs/{run.run_id}"
        if base_url
        else "Not configured"
    )

    return f"""
FinSight Dagster job failed.

Job:
{run.job_name}

Run ID:
{run.run_id}

Status:
{run.status}

Failure message:
{failure_message}

Dagster run URL:
{run_url}

Recommended checks:
1. Open the failed Dagster run.
2. Check the failed op logs.
3. If this is dbt_source_freshness_job, check whether raw source data is stale.
4. Verify DBT_PROJECT_DIR and DBT_PROFILES_DIR.
5. Run dbt source freshness manually on the VM.

Manual command:
cd /opt/finsight-dagster
source .venv/bin/activate
set -a
source .env
set +a
dbt source freshness --project-dir /opt/finsight-ae/dbt_fintech --profiles-dir /opt/finsight-ae/dbt_fintech --target prod
""".strip()


dagster_failure_email_sensor = make_email_on_run_failure_sensor(
    name="dagster_failure_email_sensor",
    email_from=get_env("DAGSTER_ALERT_EMAIL_FROM"),
    email_password=get_env("DAGSTER_ALERT_EMAIL_PASSWORD"),
    email_to=[get_env("DAGSTER_ALERT_EMAIL_TO")],
    email_subject_fn=dagster_email_subject,
    email_body_fn=dagster_email_body,
    smtp_host=get_optional_env("DAGSTER_SMTP_HOST", "smtp.gmail.com"),
    smtp_type=get_optional_env("DAGSTER_SMTP_TYPE", "STARTTLS"),
    smtp_port=int(get_optional_env("DAGSTER_SMTP_PORT", "587")),
    smtp_user=get_optional_env("DAGSTER_ALERT_EMAIL_FROM"),
    webserver_base_url=get_optional_env("DAGSTER_WEBSERVER_BASE_URL"),
    monitored_jobs=[
        dbt_source_freshness_job,
    ],
    default_status=DefaultSensorStatus.RUNNING,
)


# ---------------------------------------------------------------------
# Definitions
# ---------------------------------------------------------------------

defs = Definitions(
    jobs=[
        dbt_source_freshness_job,
        dbt_intermediate_daily_job,
        dbt_mart_daily_job,
        dbt_snapshot_job,
        dbt_tests_daily_job,
    ],
    schedules=[
        dbt_source_freshness_schedule,
        dbt_intermediate_daily_schedule,
        dbt_mart_daily_schedule,
        dbt_snapshot_daily_schedule,
        dbt_tests_daily_schedule,
    ],
    sensors=[
        dagster_failure_email_sensor,
    ],
)
