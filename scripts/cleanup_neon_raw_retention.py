"""Delete expired raw rows from Neon according to free-tier retention windows.

This script deletes only rows from Neon raw.raw_* tables. It never deletes or mutates
Cloudflare R2 objects, so R2 remains the immutable raw-file history.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from raw_db import connect_to_neon


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
        description="Delete expired rows from Neon raw tables using pg8000; R2 is never touched."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only count rows that would be deleted; do not delete or vacuum.",
    )
    parser.add_argument(
        "--skip-vacuum-analyze",
        action="store_true",
        help="Skip VACUUM ANALYZE after deletes.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Maximum expired rows to delete per committed transaction.",
    )
    return parser.parse_args()


def count_expired(conn, rule: RawRetentionRule) -> int:
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


def delete_expired_batch(conn, rule: RawRetentionRule, batch_size: int) -> int:
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"""
            with expired as (
                select ctid
                from {rule.table_name}
                where loaded_at < now() - (%s * interval '1 day')
                limit %s
            )
            delete from {rule.table_name} target
            using expired
            where target.ctid = expired.ctid;
            """,
            (rule.retention_days, batch_size),
        )
        return max(int(cursor.rowcount or 0), 0)
    finally:
        cursor.close()


def delete_expired(conn, rule: RawRetentionRule, batch_size: int) -> int:
    if batch_size < 1:
        raise ValueError("--batch-size must be at least 1")

    deleted_total = 0

    while True:
        deleted = delete_expired_batch(conn, rule, batch_size)
        conn.commit()
        deleted_total += deleted

        if deleted < batch_size:
            return deleted_total


def vacuum_analyze(conn) -> None:
    previous_autocommit = conn.autocommit
    conn.autocommit = True
    cursor = conn.cursor()
    try:
        for rule in RETENTION_RULES:
            print(f"vacuum analyze {rule.table_name}")
            cursor.execute(f"vacuum analyze {rule.table_name};")
    finally:
        cursor.close()
        conn.autocommit = previous_autocommit


def main() -> None:
    args = parse_args()
    mode = "DRY RUN" if args.dry_run else "EXECUTE"
    print(f"Neon raw retention cleanup mode: {mode}")
    print("R2 safety: this script deletes Neon raw rows only and never touches R2 objects.")

    conn = connect_to_neon()
    total_deleted = 0
    try:
        for rule in RETENTION_RULES:
            expired = count_expired(conn, rule)
            if args.dry_run:
                print(
                    f"{rule.table_name}: retention_days={rule.retention_days}, "
                    f"rows_to_delete={expired}"
                )
                continue

            deleted = delete_expired(conn, rule, args.batch_size)
            total_deleted += deleted
            print(
                f"{rule.table_name}: retention_days={rule.retention_days}, "
                f"rows_deleted={deleted}"
            )

        if args.dry_run:
            conn.rollback()
            print("Dry run complete; no rows deleted and no vacuum run.")
            return

        print(f"Committed Neon raw retention cleanup; total rows deleted={total_deleted}")

        if total_deleted and not args.skip_vacuum_analyze:
            vacuum_analyze(conn)
        elif not total_deleted:
            print("No rows deleted; skipping vacuum analyze.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
