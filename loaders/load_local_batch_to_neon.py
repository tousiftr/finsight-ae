import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

import pg8000.dbapi
from dotenv import load_dotenv


TABLE_CONFIG = [
    ("customers", "raw", "raw_customers", "customers.jsonl", "customer_id"),
    ("accounts", "raw", "raw_accounts", "accounts.jsonl", "account_id"),
    ("transactions", "raw", "raw_transactions", "transactions.jsonl", "transaction_id"),
]

DELETE_ORDER = [
    ("raw", "raw_transactions"),
    ("raw", "raw_accounts"),
    ("raw", "raw_customers"),
]


META_FILLERS = {
    "batch_id": lambda ctx: ctx["batch_id"],
    "dt": lambda ctx: ctx["dt"],
    "source_bucket": lambda _ctx: "local",
    "source_object_key": lambda ctx: ctx["source_file_path"],
    "source_file_path": lambda ctx: ctx["source_file_path"],
    "raw_file_path": lambda ctx: ctx["source_file_path"],
    "source_system": lambda _ctx: "local",
    "payload": lambda ctx: json.dumps(ctx["record"], sort_keys=True, separators=(",", ":")),
    "raw_record_hash": lambda ctx: calculate_raw_record_hash(ctx["record"]),
    "loaded_at": lambda ctx: ctx["now_utc"],
    "ingested_at": lambda ctx: ctx["now_utc"],
    "created_at": lambda ctx: parse_timestamp(ctx["record"].get("created_at"), ctx["now_utc"]),
    "updated_at": lambda ctx: parse_timestamp(ctx["record"].get("updated_at"), ctx["now_utc"]),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load one local partitioned FinSight raw batch into Neon Postgres.")
    parser.add_argument("--dt", required=True, help="Partition date (YYYY-MM-DD)")
    parser.add_argument("--batch-id", required=True, help="Batch ID (e.g., 20260502_1436)")
    parser.add_argument("--base-dir", default="data/raw", help="Root directory containing raw partitioned JSONL files")
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
    host = parsed.hostname or ""
    database = unquote(parsed.path.lstrip("/"))
    print(f"Connecting to Neon host={host} db={database}")

    return pg8000.dbapi.connect(
        user=unquote(parsed.username or ""),
        password=unquote(parsed.password or ""),
        host=host,
        port=parsed.port or 5432,
        database=database,
        ssl_context=True,
    )


def resolve_file_path(base_dir: Path, entity: str, dt: str, batch_id: str, file_name: str) -> Path:
    return base_dir / entity / f"dt={dt}" / f"batch_id={batch_id}" / file_name


def read_jsonl_records(file_path: Path, id_field: str) -> list[dict]:
    if not file_path.exists():
        raise FileNotFoundError(f"Required file is missing: {file_path}")
    records = []
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


def parse_timestamp(value, fallback: datetime):
    if not value:
        return fallback
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        val = value.strip()
        if val.endswith("Z"):
            val = val[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(val)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return fallback
    return fallback


def get_table_columns(conn, schema: str, table: str) -> list[dict]:
    sql = """
    select
        column_name,
        is_nullable,
        column_default,
        data_type,
        udt_name
    from information_schema.columns
    where table_schema = %s and table_name = %s
    order by ordinal_position
    """
    cur = conn.cursor()
    try:
        cur.execute(sql, (schema, table))
        rows = cur.fetchall()
    finally:
        cur.close()
    if not rows:
        raise RuntimeError(f"Table not found: {schema}.{table}")
    return [
        {
            "name": r[0],
            "is_nullable": r[1] == "YES",
            "has_default": r[2] is not None,
            "data_type": r[3],
            "udt_name": r[4],
        }
        for r in rows
    ]


def build_insert_rows(columns: list[dict], records: list[dict], ctx_base: dict) -> tuple[list[str], list[tuple]]:
    column_names = [c["name"] for c in columns if c["name"] != "id"]
    rows = []
    for idx, record in enumerate(records, start=1):
        ctx = {**ctx_base, "record": record}
        row_vals = []
        for col in columns:
            name = col["name"]
            if name == "id":
                continue
            if name in record:
                value = record[name]
            elif name in META_FILLERS:
                value = META_FILLERS[name](ctx)
            else:
                value = None
            if value is None and (not col["is_nullable"]) and (not col["has_default"]):
                raise ValueError(
                    f"Cannot load row {idx}: required column '{name}' has no value and no database default"
                )
            row_vals.append(value)
        rows.append(tuple(row_vals))
    return column_names, rows


def delete_existing_batch(conn, batch_id: str) -> None:
    cur = conn.cursor()
    try:
        for schema, table in DELETE_ORDER:
            cur.execute(f"delete from {schema}.{table} where batch_id = %s", (batch_id,))
    finally:
        cur.close()


def insert_rows(conn, schema: str, table: str, column_names: list[str], rows: list[tuple]) -> int:
    placeholders = ", ".join(["%s"] * len(column_names))
    sql = f"insert into {schema}.{table} ({', '.join(column_names)}) values ({placeholders})"
    cur = conn.cursor()
    try:
        cur.executemany(sql, rows)
    finally:
        cur.close()
    return len(rows)


def run_batch_validations(conn, batch_id: str) -> dict:
    checks = {
        "raw.raw_customers": "select count(*) from raw.raw_customers where batch_id = %s",
        "raw.raw_accounts": "select count(*) from raw.raw_accounts where batch_id = %s",
        "raw.raw_transactions": "select count(*) from raw.raw_transactions where batch_id = %s",
        "accounts_without_customer": """
            select count(*)
            from raw.raw_accounts a
            left join raw.raw_customers c
                on c.batch_id = a.batch_id
               and c.payload->>'customer_id' = a.payload->>'customer_id'
            where a.batch_id = %s
              and c.id is null
        """,
        "transactions_without_account": """
            select count(*)
            from raw.raw_transactions t
            left join raw.raw_accounts a
                on a.batch_id = t.batch_id
               and a.payload->>'account_id' = t.payload->>'account_id'
            where t.batch_id = %s
              and a.id is null
        """,
        "transaction_customer_mismatch": """
            select count(*)
            from raw.raw_transactions t
            join raw.raw_accounts a
              on a.batch_id = t.batch_id
             and a.payload->>'account_id' = t.payload->>'account_id'
            where t.batch_id = %s
              and a.payload->>'customer_id' <> t.payload->>'customer_id'
        """,
    }
    cur = conn.cursor()
    try:
        out = {}
        for label, sql in checks.items():
            cur.execute(sql, (batch_id,))
            out[label] = cur.fetchone()[0]
        return out
    finally:
        cur.close()


def main() -> None:
    args = parse_args()
    load_project_env()
    base_dir = Path(args.base_dir)
    now_utc = datetime.now(timezone.utc)

    records_by_table = {}
    file_paths = {}
    for entity, schema, table, file_name, id_field in TABLE_CONFIG:
        path = resolve_file_path(base_dir, entity, args.dt, args.batch_id, file_name)
        file_paths[f"{schema}.{table}"] = path
        records_by_table[f"{schema}.{table}"] = read_jsonl_records(path, id_field)

    conn = get_neon_connection()
    try:
        delete_existing_batch(conn, args.batch_id)

        loaded_counts = {}
        for entity, schema, table, _, _ in TABLE_CONFIG:
            fqtn = f"{schema}.{table}"
            columns = get_table_columns(conn, schema, table)
            ctx_base = {
                "batch_id": args.batch_id,
                "dt": args.dt,
                "source_file_path": str(file_paths[fqtn]).replace("\\", "/"),
                "now_utc": now_utc,
            }
            col_names, rows = build_insert_rows(columns, records_by_table[fqtn], ctx_base)
            loaded_counts[fqtn] = insert_rows(conn, schema, table, col_names, rows)

        validations = run_batch_validations(conn, args.batch_id)
        conn.commit()

        print("Rows loaded:")
        for table in ["raw.raw_customers", "raw.raw_accounts", "raw.raw_transactions"]:
            print(f"  {table}: {loaded_counts[table]}")

        print("Validation checks:")
        for key in [
            "raw.raw_customers",
            "raw.raw_accounts",
            "raw.raw_transactions",
            "accounts_without_customer",
            "transactions_without_account",
            "transaction_customer_mismatch",
        ]:
            print(f"  {key}: {validations[key]}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
