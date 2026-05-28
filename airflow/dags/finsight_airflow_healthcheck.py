from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.operators.python import PythonOperator


DEFAULT_ARGS = {
    "owner": "rad",
    "depends_on_past": False,
    "email": ["aefinsight@yahoo.com"],
    "email_on_failure": True,
    "email_on_retry": True,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def check_required_env_vars() -> None:
    required = [
        "DBT_PROJECT_DIR",
        "DBT_PROFILES_DIR",
        "MIXPANEL_EXPORT_TABLE",
        "MIXPANEL_BATCH_SIZE",
        "MIXPANEL_DRY_RUN",
        "DBT_PRODUCT_ANALYTICS_SELECTOR",
        "AIRFLOW__SMTP__SMTP_HOST",
        "AIRFLOW__SMTP__SMTP_USER",
        "AIRFLOW__SMTP__SMTP_MAIL_FROM",
        "AIRFLOW__SMTP__SMTP_PASSWORD",
    ]

    missing = [key for key in required if not os.getenv(key)]

    if missing:
        raise AirflowException(
            "Missing required env vars: " + ", ".join(missing)
        )

    print("Required Airflow environment variables are set.")


def check_runtime_paths() -> None:
    dbt_project_dir = Path(os.getenv("DBT_PROJECT_DIR", ""))
    dbt_profiles_dir = Path(os.getenv("DBT_PROFILES_DIR", ""))
    airflow_dags_dir = Path("/opt/airflow/dags")

    checks = {
        "DBT_PROJECT_DIR": dbt_project_dir,
        "DBT_PROFILES_DIR": dbt_profiles_dir,
        "AIRFLOW_DAGS_DIR": airflow_dags_dir,
    }

    missing_paths = [
        f"{name}={path}"
        for name, path in checks.items()
        if not path.exists()
    ]

    if missing_paths:
        raise AirflowException(
            "Missing required runtime paths: " + ", ".join(missing_paths)
        )

    print("Airflow runtime paths are valid.")
    print(f"DBT_PROJECT_DIR={dbt_project_dir}")
    print(f"DBT_PROFILES_DIR={dbt_profiles_dir}")
    print(f"AIRFLOW_DAGS_DIR={airflow_dags_dir}")


with DAG(
    dag_id="finsight_airflow_healthcheck",
    description="FinSight Airflow runtime, env, path, and alert healthcheck.",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2026, 5, 28),
    schedule="15 * * * *",
    catchup=False,
    max_active_runs=1,
    tags=["finsight", "healthcheck", "monitoring"],
) as dag:

    check_env = PythonOperator(
        task_id="check_required_env_vars",
        python_callable=check_required_env_vars,
    )

    check_paths = PythonOperator(
        task_id="check_runtime_paths",
        python_callable=check_runtime_paths,
    )

    check_env >> check_paths
