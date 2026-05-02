FROM python:3.11-slim

WORKDIR /usr/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        git \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install --no-cache-dir dbt-core dbt-postgres

ENTRYPOINT ["dbt"]