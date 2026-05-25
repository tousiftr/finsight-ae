from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from airflow.decorators import dag, task


PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", "/opt/finsight-ae"))
DBT_PROJECT_DIR = PROJECT_ROOT / "dbt_fintech"


def run_command(command: list[str], cwd: Path | None = None) -> str:
    """Run a read-only healthcheck command and return combined output."""
    result = subprocess.run(
        command,
        cwd=str(cwd or PROJECT_ROOT),
        text=True,
        capture_output=True,
        check=False,
        env=os.environ.copy(),
    )

    output = (result.stdout or "") + "\n" + (result.stderr or "")

    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}\n"
            f"Command: {' '.join(command)}\n\n"
            f"{output}"
        )

    return output


@dag(
    dag_id="finsight_airflow_healthcheck",
    description="Manual safe healthcheck for the FinSight Airflow sidecar. No writes, no ingestion, no dbt build.",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "rad",
        "retries": 0,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["finsight", "healthcheck", "manual-safe"],
    is_paused_upon_creation=True,
)
def finsight_airflow_healthcheck():
    @task
    def check_project_mount() -> str:
        if not PROJECT_ROOT.exists():
            raise FileNotFoundError(f"PROJECT_ROOT does not exist: {PROJECT_ROOT}")
        if not DBT_PROJECT_DIR.exists():
            raise FileNotFoundError(f"dbt project directory does not exist: {DBT_PROJECT_DIR}")
        return f"Project mounted successfully at {PROJECT_ROOT}"

    @task
    def check_python_version() -> str:
        return run_command(["python", "--version"])

    @task
    def check_dbt_version() -> str:
        return run_command(["dbt", "--version"], cwd=DBT_PROJECT_DIR)

    @task
    def check_dbt_debug() -> str:
        return run_command(["dbt", "debug", "--target", "prod"], cwd=DBT_PROJECT_DIR)

    @task
    def check_dbt_parse() -> str:
        return run_command(["dbt", "parse", "--target", "prod"], cwd=DBT_PROJECT_DIR)

    @task
    def check_dbt_ls() -> str:
        return run_command(["dbt", "ls", "--target", "prod"], cwd=DBT_PROJECT_DIR)

    mounted = check_project_mount()
    python_ok = check_python_version()
    dbt_version_ok = check_dbt_version()
    dbt_debug_ok = check_dbt_debug()
    dbt_parse_ok = check_dbt_parse()
    dbt_ls_ok = check_dbt_ls()

    mounted >> python_ok >> dbt_version_ok >> dbt_debug_ok >> dbt_parse_ok >> dbt_ls_ok


finsight_airflow_healthcheck()
