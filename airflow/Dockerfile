FROM apache/airflow:2.10.5-python3.11

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

COPY requirements.txt /tmp/finsight-requirements.txt

RUN pip install --no-cache-dir -r /tmp/finsight-requirements.txt \
    && pip install --no-cache-dir dbt-postgres==1.9.0 psycopg2-binary==2.9.10
