FROM apache/airflow:2.10.5-python3.11

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

COPY requirements.txt /tmp/finsight-requirements.txt
COPY requirements-dbt.txt /tmp/requirements-dbt.txt

RUN pip install --no-cache-dir -r /tmp/finsight-requirements.txt \
    && pip install --no-cache-dir -r /tmp/requirements-dbt.txt psycopg2-binary==2.9.10 \
    && dbt --version \
    && python -c 'import dbt.version; version = dbt.version.__version__; print("Installed dbt version:", version); assert not version.startswith("2."), "dbt Core v2 / Fusion is not supported for this Postgres project yet"'
