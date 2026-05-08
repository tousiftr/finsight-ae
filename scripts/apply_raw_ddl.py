"""Apply raw schema DDL for FinSight ingestion-owned Neon tables."""

from __future__ import annotations

from pathlib import Path

from raw_db import PROJECT_ROOT, connect_to_neon

DDL_PATH = PROJECT_ROOT / "loaders" / "create_raw_tables.sql"


def main() -> None:
    if not DDL_PATH.exists():
        raise FileNotFoundError(f"Raw DDL file not found: {DDL_PATH}")

    ddl = DDL_PATH.read_text(encoding="utf-8")
    conn = connect_to_neon()
    try:
        cursor = conn.cursor()
        try:
            cursor.execute(ddl)
        finally:
            cursor.close()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print(f"Successfully applied raw DDL from {DDL_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
