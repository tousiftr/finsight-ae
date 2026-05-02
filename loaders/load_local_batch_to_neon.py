import argparse
import hashlib
import json
import os
import ssl
from pathlib import Path
from urllib.parse import unquote, urlparse

import pg8000.dbapi
from dotenv import load_dotenv


TABLE_CONFIG = [
    ("customers", "raw.raw_customers", "customers.jsonl", "customer_id"),
    ("accounts", "raw.raw_accounts", "accounts.jsonl", "account_id"),
    ("transactions", "raw.raw_transactions", "transactions.jsonl", "transaction_id"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load one local partitioned FinSight raw batch into Neon Postgres."
    )
    parser.add_argument("--dt", required=True, help="Partition date (YYYY-MM-DD)")
    parser.add_argument("--batch-id", required=True, help="Batch ID (e.g., 20260502_1436)")
    return parser.parse_args()


def load_project_env() -> None:
    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env", override=True)
    load_dotenv(override=False)


def get_neon_connection():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("Missing required environment variable: DATABASE_URL")

    parsed = urlparse(database_url)
    return pg8000.dbapi.connect(
        user=unquote(parsed.username or ""),
        password=unquote(parsed.password or ""),
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=unquote(parsed.path.lstrip("/")),
        ssl_context=ssl.create_default_context(),
    )


def resolve_file_path(entity: str, dt: str, batch_id: str, file_name: str) -> Path:
    return Path("data/raw") / entity / f"dt={dt}" / f"batch_id={batch_id}" / file_name


def read_jsonl_records(file_path: Path, id_field: str) -> list[dict]:
    if not file_path.exists():
        raise FileNotFoundError(f"Required file is missing: {file_path}")

    records: list[dict] = []
    with file_path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {file_path} line {line_number}: {exc}") from exc

            if id_field not in record:
                raise ValueError(f"Missing required field '{id_field}' in {file_path} line {line_number}")

            record[id_field] = str(record[id_field])
            records.append(record)

    if not records:
        raise ValueError(f"Required file is empty (or only blank lines): {file_path}")

    return records


def calculate_raw_record_hash(record: dict) -> str:
    canonical_json = json.dumps(record, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def upsert_records(conn, table_name: str, records: list[dict], dt: str, batch_id: str) -> int:
    sql = f"""
        insert into {table_name} (
            payload,
            dt,
            batch_id,
            raw_record_hash
        )
        values (%s, %s, %s, %s)
        on conflict (raw_record_hash) do update
        set payload = excluded.payload,
            dt = excluded.dt,
            batch_id = excluded.batch_id
    """

    count = 0
    cursor = conn.cursor()
    try:
        for record in records:
            cursor.execute(sql, (json.dumps(record), dt, batch_id, calculate_raw_record_hash(record)))
            count += 1
    finally:
        cursor.close()
    return count


def main() -> None:
    args = parse_args()
    load_project_env()

    records_by_table: dict[str, list[dict]] = {}
    for entity, table_name, file_name, id_field in TABLE_CONFIG:
        path = resolve_file_path(entity, args.dt, args.batch_id, file_name)
        records_by_table[table_name] = read_jsonl_records(path, id_field)

    conn = get_neon_connection()
    try:
        for _, table_name, _, _ in TABLE_CONFIG:
            count = upsert_records(conn, table_name, records_by_table[table_name], args.dt, args.batch_id)
            print(f"{table_name}: {count} rows inserted/upserted")
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
