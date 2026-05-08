"""Shared pg8000 helpers for FinSight raw Neon maintenance scripts."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import pg8000.dbapi
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_project_env() -> None:
    """Load local env files without requiring either file to exist."""
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(PROJECT_ROOT / ".env.dbt", override=False)


def _ssl_context_from_query(query: str):
    params = parse_qs(query)
    sslmode = (params.get("sslmode") or [""])[0].lower()
    if sslmode in {"disable", "allow", "prefer"}:
        return None
    return True


def connect_to_neon():
    """Connect to Neon/Postgres using DATABASE_URL-style or DBT_PG_* env vars."""
    load_project_env()
    database_url = os.getenv("DATABASE_URL") or os.getenv("NEON_DATABASE_URL")

    if database_url:
        parsed = urlparse(database_url)
        database = unquote(parsed.path.lstrip("/"))
        if not parsed.hostname or not database:
            raise RuntimeError("DATABASE_URL/NEON_DATABASE_URL is missing host or database.")

        return pg8000.dbapi.connect(
            user=unquote(parsed.username or ""),
            password=unquote(parsed.password or ""),
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=database,
            ssl_context=_ssl_context_from_query(parsed.query),
        )

    required = {
        "DBT_PG_HOST": os.getenv("DBT_PG_HOST"),
        "DBT_PG_DATABASE": os.getenv("DBT_PG_DATABASE"),
        "DBT_PG_USER": os.getenv("DBT_PG_USER"),
        "DBT_PG_PASSWORD": os.getenv("DBT_PG_PASSWORD"),
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(
            "Missing database configuration. Set DATABASE_URL/NEON_DATABASE_URL or "
            f"DBT_PG_* variables. Missing: {', '.join(missing)}"
        )

    return pg8000.dbapi.connect(
        user=required["DBT_PG_USER"],
        password=required["DBT_PG_PASSWORD"],
        host=required["DBT_PG_HOST"],
        port=int(os.getenv("DBT_PG_PORT", "5432")),
        database=required["DBT_PG_DATABASE"],
        ssl_context=True,
    )


def raw_bucket_name(default: str = "finsight-raw") -> str:
    load_project_env()
    return (
        os.getenv("R2_BUCKET_NAME")
        or os.getenv("R2_BUCKET")
        or os.getenv("S3_BUCKET_NAME")
        or default
    )
