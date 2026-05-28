from __future__ import annotations

import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from airflow.decorators import dag, task


DBT_PROJECT_DIR = Path(os.environ.get("DBT_PROJECT_DIR", "/opt/finsight-ae/dbt_fintech"))
DBT_PRODUCT_ANALYTICS_SELECTOR = os.environ.get(
    "DBT_PRODUCT_ANALYTICS_SELECTOR",
    "tag:product_analytics_hourly",
)
MIXPANEL_SYNC_SCRIPT = Path(
    os.environ.get(
        "MIXPANEL_SYNC_SCRIPT",
        "/opt/finsight-ae/product_analytics/sync_neon_to_mixpanel.py",
    )
)


def run_command(command: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
        env=os.environ.copy(),
    )

    output = (result.stdout or "") + "\n" + (result.stderr or "")

    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}\n"
            f"Command: {' '.join(command)}\n\n{output}"
        )

    return output


@dag(
    dag_id="finsight_mixpanel_hourly_sync",
    description="Hourly FinSight product analytics export refresh and Mixpanel sync.",
    start_date=datetime(2026, 5, 8),
    schedule="0 * * * *",
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "rad",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["finsight", "mixpanel", "product-analytics", "hourly"],
)
def finsight_mixpanel_hourly_sync():
    @task
    def rebuild_mixpanel_export() -> str:
        return run_command(
            ["dbt", "build", "--select", DBT_PRODUCT_ANALYTICS_SELECTOR, "--target", "prod"],
            cwd=DBT_PROJECT_DIR,
        )

    @task
    def sync_mixpanel_batch() -> str:
        if not MIXPANEL_SYNC_SCRIPT.exists():
            return f"Skipping Mixpanel sync. Script not found at {MIXPANEL_SYNC_SCRIPT}"

        return run_command(["python", str(MIXPANEL_SYNC_SCRIPT)])

    rebuild_mixpanel_export() >> sync_mixpanel_batch()


finsight_mixpanel_hourly_sync()
