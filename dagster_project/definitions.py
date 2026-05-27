from pathlib import Path
import os
import subprocess

from dagster import Definitions, ScheduleDefinition, job, op
from dagster_dbt import DbtCliResource, dbt_assets

PROJECT_ROOT = Path("/opt/finsight-dagster")
DBT_DIR = PROJECT_ROOT / "dbt_fintech"
DBT_PROFILES_DIR = Path("/home/rad/.dbt")
DBT_MANIFEST = DBT_DIR / "target" / "manifest.json"
DBT_EXECUTABLE = PROJECT_ROOT / ".venv" / "bin" / "dbt"

INTERMEDIATE_SELECTOR = os.getenv(
    "DBT_INTERMEDIATE_SELECTOR",
    "path:models/intermediate",
)

MART_SELECTOR = os.getenv(
    "DBT_MART_SELECTOR",
    "fqn:*mrt*",
)


@dbt_assets(manifest=DBT_MANIFEST)
def finsight_dbt_lineage_assets(context, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()


def run_cmd(cmd: list[str]) -> None:
    subprocess.run(
        cmd,
        cwd=DBT_DIR,
        check=True,
        env=os.environ.copy(),
    )


@op
def run_source_freshness():
    run_cmd([str(DBT_EXECUTABLE), "source", "freshness"])


@op
def run_snapshots():
    run_cmd([str(DBT_EXECUTABLE), "snapshot"])


@op
def run_intermediate_models():
    run_cmd([str(DBT_EXECUTABLE), "run", "--select", INTERMEDIATE_SELECTOR])


@op
def run_mart_models():
    run_cmd([str(DBT_EXECUTABLE), "run", "--select", MART_SELECTOR])


@op
def run_model_tests():
    run_cmd([
        str(DBT_EXECUTABLE),
        "test",
        "--select",
        INTERMEDIATE_SELECTOR,
        MART_SELECTOR,
    ])


@job
def dbt_source_freshness_job():
    run_source_freshness()


@job
def dbt_snapshot_job():
    run_snapshots()


@job
def dbt_intermediate_daily_job():
    run_intermediate_models()


@job
def dbt_mart_daily_job():
    run_mart_models()


@job
def dbt_tests_daily_job():
    run_model_tests()


source_freshness_schedule = ScheduleDefinition(
    job=dbt_source_freshness_job,
    cron_schedule="*/30 * * * *",
    execution_timezone="Asia/Dhaka",
)

snapshot_daily_schedule = ScheduleDefinition(
    job=dbt_snapshot_job,
    cron_schedule="25 12 * * *",
    execution_timezone="Asia/Dhaka",
)

intermediate_daily_schedule = ScheduleDefinition(
    job=dbt_intermediate_daily_job,
    cron_schedule="30 12 * * *",
    execution_timezone="Asia/Dhaka",
)

mart_daily_schedule = ScheduleDefinition(
    job=dbt_mart_daily_job,
    cron_schedule="50 12 * * *",
    execution_timezone="Asia/Dhaka",
)

tests_daily_schedule = ScheduleDefinition(
    job=dbt_tests_daily_job,
    cron_schedule="10 13 * * *",
    execution_timezone="Asia/Dhaka",
)

defs = Definitions(
    assets=[finsight_dbt_lineage_assets],
    resources={
        "dbt": DbtCliResource(
            project_dir=str(DBT_DIR),
            profiles_dir=str(DBT_PROFILES_DIR),
            dbt_executable=str(DBT_EXECUTABLE),
        )
    },
    jobs=[
        dbt_source_freshness_job,
        dbt_snapshot_job,
        dbt_intermediate_daily_job,
        dbt_mart_daily_job,
        dbt_tests_daily_job,
    ],
    schedules=[
        source_freshness_schedule,
        snapshot_daily_schedule,
        intermediate_daily_schedule,
        mart_daily_schedule,
        tests_daily_schedule,
    ],
)
