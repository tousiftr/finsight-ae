"""Delete expired raw rows from Neon according to live raw retention windows.

This script connects to Neon with pg8000 and deletes only rows from raw.raw_* tables.
It never lists, deletes, rewrites, or mutates Cloudflare R2 objects, so R2 remains the
full immutable raw-file history while Neon keeps only recent live raw rows.

By default the script is a dry run. Pass --execute to perform deletes.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

import pg8000.dbapi
from dotenv import load_dotenv


@dataclass(frozen=True)
class RawRetentionRule:
    table_name: str
    retention_days: int


RETENTION_RULES: tuple[RawRetentionRule, ...] = (
    RawRetentionRule("raw.raw_transactions", 7),
    RawRetentionRule("raw.raw_product_events", 7),
    RawRetentionRule("raw.raw_kyc_applications", 14),
    RawRetentionRule("raw.raw_customers", 30),
    RawRetentionRule("raw.raw_accounts", 30),
    RawRetentionRule("raw.raw_merchants", 30),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Delete expired rows from Neon raw tables using pg8000. "
            "Cloudflare R2 raw files are never touched."
        )
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete expired Neon rows. Omit for a dry run.",
    )
    parser.add_argument(
        "--vacuum",
        action="store_true",
        help="Run VACUUM on raw tables after --execute deletes to return reusable space to Postgres.",
    )
    return parser.parse_args()


def get_neon_connection():
    database_url = os.getenv("DATABASE_URL") or os.getenv("NEON_DATABASE_URL")

    if not database_url:
        raise RuntimeError("Missing DATABASE_URL or NEON_DATABASE_URL.")

    parsed = urlparse(database_url)

    return pg8000.dbapi.connect(
        user=unquote(parsed.username or ""),
        password=unquote(parsed.password or ""),
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=unquote(parsed.path.lstrip("/")),
        ssl_context=True,
    )


def print_database_size(conn, label: str) -> None:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "select pg_size_pretty(pg_database_size(current_database())) as database_size;"
        )
        print(f"{label} database_size={cursor.fetchone()[0]}")
    finally:
        cursor.close()


def print_table_sizes(conn) -> None:
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            select
                n.nspname || '.' || c.relname as table_name,
                pg_size_pretty(pg_total_relation_size(c.oid)) as total_size,
                pg_size_pretty(pg_relation_size(c.oid)) as table_size,
                pg_size_pretty(pg_indexes_size(c.oid)) as index_size
            from pg_class c
            join pg_namespace n on n.oid = c.relnamespace
            where n.nspname = 'raw'
              and c.relname in (
                  'raw_customers',
                  'raw_accounts',
                  'raw_merchants',
                  'raw_transactions',
                  'raw_product_events',
                  'raw_kyc_applications'
              )
              and c.relkind in ('r', 'p')
            order by pg_total_relation_size(c.oid) desc;
            """
        )
        print("\nRaw table sizes")
        print("---------------")
        for table_name, total_size, table_size, index_size in cursor.fetchall():
            print(
                f"{table_name}: total={total_size} table={table_size} indexes={index_size}"
            )
    finally:
        cursor.close()


def expired_count(conn, rule: RawRetentionRule) -> int:
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"""
            select count(*)
            from {rule.table_name}
            where loaded_at < now() - (%s * interval '1 day');
            """,
            (rule.retention_days,),
        )
        return int(cursor.fetchone()[0])
    finally:
        cursor.close()


def delete_expired_rows(conn, rule: RawRetentionRule) -> int:
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"""
            delete from {rule.table_name}
            where loaded_at < now() - (%s * interval '1 day');
            """,
            (rule.retention_days,),
        )
        return max(int(cursor.rowcount or 0), 0)
    finally:
        cursor.close()


def vacuum_tables(conn) -> None:
    previous_autocommit = conn.autocommit
    conn.autocommit = True
    cursor = conn.cursor()
    try:
        for rule in RETENTION_RULES:
            print(f"VACUUM {rule.table_name}")
            cursor.execute(f"vacuum {rule.table_name};")
    finally:
        cursor.close()
        conn.autocommit = previous_autocommit


def main() -> None:
    args = parse_args()
    load_dotenv()

    mode = "EXECUTE" if args.execute else "DRY RUN"
    print(f"Neon raw retention cleanup mode: {mode}")
    print("R2 safety: this script deletes Neon rows only and never touches R2 objects.")

    conn = get_neon_connection()
    try:
        print_database_size(conn, "Before")
        print_table_sizes(conn)

        print("\nRetention plan")
        print("--------------")
        total_deleted = 0
        for rule in RETENTION_RULES:
            count = expired_count(conn, rule)
            print(
                f"{rule.table_name}: retention={rule.retention_days} days, "
                f"expired_rows={count}"
            )

            if args.execute and count:
                deleted = delete_expired_rows(conn, rule)
                total_deleted += deleted
                print(f"{rule.table_name}: deleted_rows={deleted}")

        if args.execute:
            conn.commit()
            print(f"\nCommitted Neon raw cleanup. Total deleted rows: {total_deleted}")
            if args.vacuum and total_deleted:
                vacuum_tables(conn)
            print_database_size(conn, "After")
            print_table_sizes(conn)
        else:
            conn.rollback()
            print("\nDry run complete. Pass --execute to delete expired Neon raw rows.")

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
