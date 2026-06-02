FROM python:3.11-slim

WORKDIR /usr/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-dbt.txt /tmp/requirements-dbt.txt

RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install --no-cache-dir -r /tmp/requirements-dbt.txt \
    && dbt --version \
    && python -c 'import dbt.version; version = dbt.version.__version__; print("Installed dbt version:", version); assert not version.startswith("2."), "dbt Core v2 / Fusion is not supported for this Postgres project yet"'

ENTRYPOINT ["dbt"]
