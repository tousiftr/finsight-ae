"""Load local partitioned JSONL raw files into Neon raw tables idempotently."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from raw_db import connect_to_neon, raw_bucket_name


@dataclass(frozen=True)
class DomainConfig:
    domain: str
    table_name: str
    raw_id_column: str
    payload_id_field: str
    customer_id_column: str | None = None


DOMAIN_CONFIGS: dict[str, DomainConfig] = {
    "customers": DomainConfig(
        domain="customers",
        table_name="raw.raw_customers",
        raw_id_column="raw_customer_id",
        payload_id_field="customer_id",
        customer_id_column="customer_id",
    ),
    "accounts": DomainConfig(
        domain="accounts",
        table_name="raw.raw_accounts",
        raw_id_column="raw_account_id",
        payload_id_field="account_id",
    ),
    "merchants": DomainConfig(
        domain="merchants",
        table_name="raw.raw_merchants",
        raw_id_column="raw_merchant_id",
        payload_id_field="merchant_id",
        customer_id_column="merchant_id",
    ),
    "transactions": DomainConfig(
        domain="transactions",
        table_name="raw.raw_transactions",
        raw_id_column="raw_transaction_id",
        payload_id_field="transaction_id",
    ),
    "product_events": DomainConfig(
        domain="product_events",
        table_name="raw.raw_product_events",
        raw_id_column="raw_product_event_id",
        payload_id_field="event_id",
    ),
    "kyc_applications": DomainConfig(
        domain="kyc_applications",
        table_name="raw.raw_kyc_applications",
        raw_id_column="raw_kyc_application_id",
        payload_id_field="kyc_application_id",
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load FinSight local data/raw JSONL partitions into Neon raw tables."
    )
    parser.add_argument("--raw-root", default="data/raw", help="Root folder for raw JSONL partitions.")
    parser.add_argument(
        "--domain",
        choices=sorted(DOMAIN_CONFIGS),
        help="Optional single domain to load. Omit to load all supported domains.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=100,
        help="Rows to insert before committing. Smaller chunks reduce Neon transaction size.",
    )
    return parser.parse_args()


def canonical_hash(payload: dict) -> str:
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def partition_value(part: str, prefix: str) -> str:
    if not part.startswith(prefix):
        raise ValueError(f"Expected partition '{prefix}...' but found '{part}'")
    return part.split("=", 1)[1]


def discover_files(raw_root: Path, domain: str) -> list[Path]:
    domain_root = raw_root / domain
    if not domain_root.exists():
        print(f"No local raw directory for domain={domain}: {domain_root}; skipping")
        return []
    return sorted(domain_root.glob(f"dt=*/batch_id=*/{domain}.jsonl"))


def read_jsonl(path: Path, required_field: str) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            if payload.get(required_field) in (None, ""):
                raise ValueError(f"Missing {required_field} in {path} line {line_number}")
            rows.append(payload)
    return rows


def source_object_key(raw_root: Path, path: Path) -> str:
    return path.relative_to(raw_root).as_posix()


def insert_file(
    conn,
    config: DomainConfig,
    raw_root: Path,
    path: Path,
    bucket: str,
    chunk_size: int,
) -> tuple[int, int]:
    if chunk_size < 1:
        raise ValueError("--chunk-size must be at least 1")

    batch_id = partition_value(path.parent.name, "batch_id=")
    dt = partition_value(path.parent.parent.name, "dt=")
    object_key = source_object_key(raw_root, path)
    source_file_path = f"s3://{bucket}/{object_key}"
    payloads = read_jsonl(path, config.payload_id_field)

    columns = [
        config.raw_id_column,
        "payload",
        "source_bucket",
        "source_object_key",
        "source_file_path",
        "dt",
        "batch_id",
        "raw_record_hash",
    ]
    if config.customer_id_column:
        columns.insert(1, config.customer_id_column)

    placeholders = ["%s"] * len(columns)
    payload_index = columns.index("payload")
    placeholders[payload_index] = "%s::jsonb"
    quoted_columns = ", ".join(columns)
    placeholder_sql = ", ".join(placeholders)
    sql = f"""
        insert into {config.table_name} ({quoted_columns})
        values ({placeholder_sql})
        on conflict (source_object_key, raw_record_hash) do nothing;
    """

    inserted = 0
    cursor = conn.cursor()
    try:
        for start_index in range(0, len(payloads), chunk_size):
            chunk = payloads[start_index:start_index + chunk_size]

            for payload in chunk:
                business_id = str(payload[config.payload_id_field])
                values: list[str] = []
                for column in columns:
                    if column == config.raw_id_column:
                        values.append(business_id)
                    elif column == config.customer_id_column:
                        values.append(business_id)
                    elif column == "payload":
                        values.append(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
                    elif column == "source_bucket":
                        values.append(bucket)
                    elif column == "source_object_key":
                        values.append(object_key)
                    elif column == "source_file_path":
                        values.append(source_file_path)
                    elif column == "dt":
                        values.append(dt)
                    elif column == "batch_id":
                        values.append(batch_id)
                    elif column == "raw_record_hash":
                        values.append(canonical_hash(payload))
                    else:
                        raise ValueError(f"Unexpected insert column: {column}")
                cursor.execute(sql, tuple(values))
                inserted += max(int(cursor.rowcount or 0), 0)

            conn.commit()
            checked = min(start_index + len(chunk), len(payloads))
            print(
                f"{config.table_name}: committed chunk through row {checked} of {len(payloads)} "
                f"for {object_key}"
            )
    finally:
        cursor.close()

    print(
        f"file loaded: {path} | candidate rows={len(payloads)} | inserted rows={inserted} | "
        "duplicates skipped by on conflict"
    )
    return len(payloads), inserted


def main() -> None:
    args = parse_args()
    raw_root = Path(args.raw_root).resolve()
    if not raw_root.exists():
        raise FileNotFoundError(f"Raw root does not exist: {raw_root}")

    domains = [args.domain] if args.domain else list(DOMAIN_CONFIGS)
    bucket = raw_bucket_name()
    total_candidates = 0
    total_inserted = 0

    conn = connect_to_neon()
    try:
        for domain in domains:
            config = DOMAIN_CONFIGS[domain]
            files = discover_files(raw_root, domain)
            for path in files:
                candidates, inserted = insert_file(
                    conn=conn,
                    config=config,
                    raw_root=raw_root,
                    path=path,
                    bucket=bucket,
                    chunk_size=args.chunk_size,
                )
                total_candidates += candidates
                total_inserted += inserted
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print("duplicates skipped by on conflict")
    print(f"total processed rows={total_candidates}")
    print(f"total inserted rows={total_inserted}")


if __name__ == "__main__":
    main()
