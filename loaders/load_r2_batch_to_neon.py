import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

from object_storage.s3_client import get_bucket_name, get_s3_client

import pg8000.dbapi
from dotenv import load_dotenv


TABLE_CONFIG = [
    ("customers", "raw", "raw_customers", "customers.jsonl", "customer_id"),
    ("accounts", "raw", "raw_accounts", "accounts.jsonl", "account_id"),
    ("transactions", "raw", "raw_transactions", "transactions.jsonl", "transaction_id"),
    ("product_events", "raw", "raw_product_events", "product_events.jsonl", "event_id"),
    ("kyc_applications", "raw", "raw_kyc_applications", "kyc_applications.jsonl", "kyc_application_id"),
]

DELETE_ORDER = [
    ("raw", "raw_product_events"),
    ("raw", "raw_kyc_applications"),
    ("raw", "raw_transactions"),
    ("raw", "raw_accounts"),
    ("raw", "raw_customers"),
]

LOAD_ORDER = [
    ("customers", "raw", "raw_customers", "customers.jsonl", "customer_id"),
    ("accounts", "raw", "raw_accounts", "accounts.jsonl", "account_id"),
    ("transactions", "raw", "raw_transactions", "transactions.jsonl", "transaction_id"),
    ("product_events", "raw", "raw_product_events", "product_events.jsonl", "event_id"),
    ("kyc_applications", "raw", "raw_kyc_applications", "kyc_applications.jsonl", "kyc_application_id"),
]

RAW_ID_SPECS = {
    "raw_customer_id": ("customers", "customer_id", "raw_cust_"),
    "raw_account_id": ("accounts", "account_id", "raw_acct_"),
    "raw_transaction_id": ("transactions", "transaction_id", "raw_txn_"),
    "raw_product_event_id": ("product_events", "event_id", "raw_pe_"),
    "raw_kyc_application_id": ("kyc_applications", "kyc_application_id", "raw_kyc_"),
}

TEXT_TYPES = {
    "text",
    "character varying",
    "character",
    "varchar",
    "bpchar",
}

INTEGER_TYPES = {
    "integer",
    "bigint",
    "smallint",
    "int2",
    "int4",
    "int8",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load one exact dt+batch_id FinSight raw batch from Cloudflare R2 into Neon Postgres."
    )

    parser.add_argument(
        "--dt",
        required=True,
        help="Partition date, example: 2026-05-02",
    )

    parser.add_argument(
        "--batch-id",
        required=True,
        help="Batch ID, example: 20260502_1436",
    )

    parser.add_argument(
        "--bucket", default=None, help="Optional bucket override")

    return parser.parse_args()


def load_project_env() -> None:
    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env", override=True)
    load_dotenv(override=False)


def get_neon_connection():
    database_url = os.getenv("DATABASE_URL") or os.getenv("NEON_DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "Missing required environment variable: DATABASE_URL or NEON_DATABASE_URL"
        )

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


def resolve_file_path(
    base_dir: Path,
    entity: str,
    dt: str,
    batch_id: str,
    file_name: str,
) -> Path:
    return base_dir / entity / f"dt={dt}" / f"batch_id={batch_id}" / file_name


def normalize_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def read_jsonl_records(file_path: Path, id_field: str) -> list[dict]:
    if not file_path.exists():
        raise FileNotFoundError(f"Required file is missing: {file_path}")

    if file_path.stat().st_size == 0:
        raise ValueError(f"Required file is empty: {file_path}")

    records = []

    with file_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()

            if not stripped:
                continue

            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON in {file_path} line {line_number}: {exc}"
                ) from exc

            if id_field not in record or record.get(id_field) is None:
                raise ValueError(
                    f"Missing required field '{id_field}' in {file_path} line {line_number}"
                )

            record[id_field] = str(record[id_field])
            records.append(record)

    if not records:
        raise ValueError(f"Required file has no JSON rows: {file_path}")

    return records


def calculate_raw_record_hash(record: dict) -> str:
    canonical_json = json.dumps(
        record,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def build_raw_ingestion_id(
    entity: str,
    batch_id: str,
    business_id: str,
    prefix: str,
) -> str:
    seed = f"{entity}|{batch_id}|{business_id}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]
    return f"{prefix}{digest}"


def parse_timestamp(value, fallback: datetime):
    if value is None or value == "":
        return fallback

    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    if isinstance(value, str):
        cleaned = value.strip()

        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"

        try:
            parsed = datetime.fromisoformat(cleaned)
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
        where table_schema = %s
          and table_name = %s
        order by ordinal_position;
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
            "name": row[0],
            "is_nullable": row[1] == "YES",
            "has_default": row[2] is not None,
            "data_type": row[3],
            "udt_name": row[4],
            "column_default": row[2],
        }
        for row in rows
    ]


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def metadata_value(column_name: str, ctx: dict):
    record = ctx["record"]
    now_utc = ctx["now_utc"]
    source_file_path = ctx["source_file_path"]

    values = {
        "batch_id": ctx["batch_id"],
        "dt": ctx["dt"],
        "source_bucket": ctx["source_bucket"],
        "source_object_key": source_file_path,
        "source_file_path": source_file_path,
        "raw_file_path": source_file_path,
        "source_system": "cloudflare_r2",
        "payload": json.dumps(
            record,
            sort_keys=True,
            default=str,
            separators=(",", ":"),
        ),
        "raw_record_hash": calculate_raw_record_hash(record),
        "loaded_at": now_utc,
        "ingested_at": now_utc,
        "created_at": parse_timestamp(record.get("created_at"), now_utc),
        "updated_at": parse_timestamp(record.get("updated_at"), now_utc),
    }

    return values.get(column_name)


def should_skip_column(col: dict) -> bool:
    name = col["name"]

    if name == "id":
        return True

    if name in RAW_ID_SPECS:
        is_integer_type = (
            col["udt_name"] in INTEGER_TYPES
            or col["data_type"] in INTEGER_TYPES
        )

        if is_integer_type and col["has_default"]:
            return True

        if is_integer_type and not col["has_default"]:
            raise ValueError(
                f"Required raw ID column '{name}' is numeric and has no default. "
                "Change the DDL so it is generated by default, or make it text."
            )

    return False


def build_insert_rows(
    columns: list[dict],
    records: list[dict],
    ctx_base: dict,
) -> tuple[list[str], list[tuple]]:
    insert_columns = [
        col for col in columns
        if not should_skip_column(col)
    ]

    column_names = [col["name"] for col in insert_columns]
    rows = []

    for row_number, record in enumerate(records, start=1):
        ctx = {
            **ctx_base,
            "record": record,
        }

        row_values = []

        for col in insert_columns:
            name = col["name"]
            value = None

            # Generate raw technical IDs first.
            # This must happen before checking `name in record`, because older
            # JSON rows may contain raw_customer_id/raw_account_id/raw_transaction_id as null.
            if name in RAW_ID_SPECS:
                entity, business_id_field, prefix = RAW_ID_SPECS[name]

                business_id = record.get(business_id_field)

                if business_id is None:
                    raise ValueError(
                        f"Cannot load row {row_number}: missing business ID field "
                        f"'{business_id_field}' needed to build '{name}'"
                    )

                column_type = col["udt_name"] or col["data_type"]

                if column_type in TEXT_TYPES or col["data_type"] in TEXT_TYPES:
                    value = build_raw_ingestion_id(
                        entity=entity,
                        batch_id=ctx["batch_id"],
                        business_id=str(business_id),
                        prefix=prefix,
                    )
                else:
                    value = None

            elif name in record and record.get(name) is not None:
                value = record[name]

            else:
                value = metadata_value(name, ctx)

            if value is None and (not col["is_nullable"]) and (not col["has_default"]):
                raise ValueError(
                    f"Cannot load row {row_number}: required column '{name}' "
                    "has no value and no database default"
                )

            row_values.append(value)

        rows.append(tuple(row_values))

    return column_names, rows


def delete_existing_batch(conn, batch_id: str) -> None:
    cur = conn.cursor()

    try:
        for schema, table in DELETE_ORDER:
            cur.execute(
                f"""
                delete from {quote_identifier(schema)}.{quote_identifier(table)}
                where batch_id = %s;
                """,
                (batch_id,),
            )
    finally:
        cur.close()


def insert_rows(
    conn,
    schema: str,
    table: str,
    column_names: list[str],
    rows: list[tuple],
    chunk_size: int = 500,
) -> int:
    if not rows:
        return 0

    quoted_columns = ", ".join(
        quote_identifier(column_name)
        for column_name in column_names
    )

    row_placeholders = []
    for column_name in column_names:
        if column_name == "payload":
            row_placeholders.append("%s::jsonb")
        else:
            row_placeholders.append("%s")

    single_row_placeholder = "(" + ", ".join(row_placeholders) + ")"

    cur = conn.cursor()
    inserted = 0

    try:
        for start_index in range(0, len(rows), chunk_size):
            chunk = rows[start_index:start_index + chunk_size]

            values_sql = ", ".join(
                [single_row_placeholder] * len(chunk)
            )

            flat_params = []
            for row in chunk:
                flat_params.extend(row)

            sql = (
                f"insert into {quote_identifier(schema)}.{quote_identifier(table)} "
                f"({quoted_columns}) values {values_sql};"
            )

            cur.execute(sql, tuple(flat_params))

            inserted += len(chunk)
            print(f"{schema}.{table}: inserted {inserted} of {len(rows)} rows")

    finally:
        cur.close()

    return len(rows)
    if not rows:
        return 0

    quoted_columns = ", ".join(
        quote_identifier(column_name)
        for column_name in column_names
    )

    placeholders = ", ".join(
        "%s::jsonb" if column_name == "payload" else "%s"
        for column_name in column_names
    )

    sql = (
        f"insert into {quote_identifier(schema)}.{quote_identifier(table)} "
        f"({quoted_columns}) values ({placeholders});"
    )

    cur = conn.cursor()

    try:
        cur.executemany(sql, rows)
    finally:
        cur.close()

    return len(rows)

def run_batch_validations(conn, batch_id: str) -> dict:
    checks = {
        "raw.raw_customers": """
            select count(*)
            from raw.raw_customers
            where batch_id = %s;
        """,
        "raw.raw_accounts": """
            select count(*)
            from raw.raw_accounts
            where batch_id = %s;
        """,
        "raw.raw_transactions": """
            select count(*)
            from raw.raw_transactions
            where batch_id = %s;
        """,
        "raw.raw_product_events": """
            select count(*)
            from raw.raw_product_events
            where batch_id = %s;
        """,
        "raw.raw_kyc_applications": """
            select count(*)
            from raw.raw_kyc_applications
            where batch_id = %s;
        """,
        "accounts_without_customer": """
            select count(*)
            from raw.raw_accounts a
            left join raw.raw_customers c
                on c.batch_id = a.batch_id
               and c.payload->>'customer_id' = a.payload->>'customer_id'
            where a.batch_id = %s
              and c.payload is null;
        """,
        "transactions_without_account": """
            select count(*)
            from raw.raw_transactions t
            left join raw.raw_accounts a
                on a.batch_id = t.batch_id
               and a.payload->>'account_id' = t.payload->>'account_id'
            where t.batch_id = %s
              and a.payload is null;
        """,
        "transaction_customer_mismatch": """
            select count(*)
            from raw.raw_transactions t
            join raw.raw_accounts a
                on a.batch_id = t.batch_id
               and a.payload->>'account_id' = t.payload->>'account_id'
            where t.batch_id = %s
              and t.payload->>'customer_id' <> a.payload->>'customer_id';
        """,
        "product_events_without_customer": """
            select count(*)
            from raw.raw_product_events pe
            left join raw.raw_customers c
                on c.batch_id = pe.batch_id
               and c.payload->>'customer_id' = pe.payload->>'customer_id'
            where pe.batch_id = %s
              and c.payload is null;
        """,
        "product_events_without_account": """
            select count(*)
            from raw.raw_product_events pe
            left join raw.raw_accounts a
                on a.batch_id = pe.batch_id
               and a.payload->>'account_id' = pe.payload->>'account_id'
            where pe.batch_id = %s
              and nullif(pe.payload->>'account_id', '') is not null
              and a.payload is null;
        """,
        "product_event_customer_account_mismatch": """
            select count(*)
            from raw.raw_product_events pe
            join raw.raw_accounts a
                on a.batch_id = pe.batch_id
               and a.payload->>'account_id' = pe.payload->>'account_id'
            where pe.batch_id = %s
              and nullif(pe.payload->>'account_id', '') is not null
              and pe.payload->>'customer_id' <> a.payload->>'customer_id';
        """,
        "kyc_applications_without_customer": """
            select count(*)
            from raw.raw_kyc_applications ka
            left join raw.raw_customers c
                on c.payload->>'customer_id' = ka.payload->>'customer_id'
            where ka.batch_id = %s
              and c.payload is null;
        """,
        "customers_without_kyc": """
            select count(*)
            from raw.raw_customers c
            left join raw.raw_kyc_applications ka
                on ka.payload->>'customer_id' = c.payload->>'customer_id'
               and ka.batch_id = %s
            where c.batch_id = %s
              and ka.payload is null;
        """,
    }

    cur = conn.cursor()

    try:
        output = {}

        for label, sql in checks.items():
            params = (batch_id, batch_id) if label == "customers_without_kyc" else (batch_id,)
            cur.execute(sql, params)
            output[label] = cur.fetchone()[0]

        return output

    finally:
        cur.close()



def r2_object_key(entity: str, dt: str, batch_id: str, file_name: str) -> str:
    return f"{entity}/dt={dt}/batch_id={batch_id}/{file_name}"


def read_jsonl_records_from_r2(s3_client, bucket: str, object_key: str, id_field: str) -> list[dict]:
    try:
        obj = s3_client.get_object(Bucket=bucket, Key=object_key)
    except Exception as exc:
        raise FileNotFoundError(f"Missing required R2 object: s3://{bucket}/{object_key}") from exc
    rows = []
    body = obj["Body"].read().decode("utf-8")
    for i, line in enumerate(body.splitlines(), start=1):
        if not line.strip():
            continue
        record = json.loads(line)
        if id_field not in record or record.get(id_field) is None:
            raise ValueError(f"Missing required field '{id_field}' in {object_key} line {i}")
        record[id_field] = str(record[id_field])
        rows.append(record)
    if not rows:
        raise ValueError(f"Required object has no JSON rows: s3://{bucket}/{object_key}")
    return rows

def read_all_r2_records(s3_client, bucket: str, dt: str, batch_id: str) -> tuple[dict, dict]:
    records_by_table = {}
    file_paths = {}

    for entity, schema, table, file_name, id_field in TABLE_CONFIG:
        key = r2_object_key(entity, dt, batch_id, file_name)

        table_name = f"{schema}.{table}"

        file_paths[table_name] = key
        records_by_table[table_name] = read_jsonl_records_from_r2(
            s3_client=s3_client,
            bucket=bucket,
            object_key=key,
            id_field=id_field,
        )

    return records_by_table, file_paths


def main() -> None:
    args = parse_args()
    load_project_env()

        now_utc = datetime.now(timezone.utc)

    s3_client = get_s3_client()
    bucket = args.bucket or get_bucket_name()
    records_by_table, file_paths = read_all_r2_records(
        s3_client=s3_client,
        bucket=bucket,
        dt=args.dt,
        batch_id=args.batch_id,
    )
    print(f"BATCH_DT={args.dt}")
    print(f"BATCH_ID={args.batch_id}")

    conn = get_neon_connection()

    try:
        delete_existing_batch(conn, args.batch_id)

        loaded_counts = {}

        for entity, schema, table, file_name, id_field in LOAD_ORDER:
            full_table_name = f"{schema}.{table}"
            columns = get_table_columns(conn, schema, table)

            ctx_base = {
                "batch_id": args.batch_id,
                "dt": args.dt,
                "source_file_path": file_paths[full_table_name],
                "source_bucket": bucket,
                "now_utc": now_utc,
            }

            column_names, rows = build_insert_rows(
                columns=columns,
                records=records_by_table[full_table_name],
                ctx_base=ctx_base,
            )

            loaded_counts[full_table_name] = insert_rows(
                conn=conn,
                schema=schema,
                table=table,
                column_names=column_names,
                rows=rows,
            )

        validations = run_batch_validations(conn, args.batch_id)

        conn.commit()

        print("\nRows loaded")
        print("-----------")
        for table_name in [
            "raw.raw_customers",
            "raw.raw_accounts",
            "raw.raw_transactions",
            "raw.raw_product_events",
            "raw.raw_kyc_applications",
        ]:
            print(f"{table_name}: {loaded_counts[table_name]}")

        print("\nValidation checks")
        print("-----------------")
        for key in [
            "raw.raw_customers",
            "raw.raw_accounts",
            "raw.raw_transactions",
            "raw.raw_product_events",
            "raw.raw_kyc_applications",
            "accounts_without_customer",
            "transactions_without_account",
            "transaction_customer_mismatch",
            "product_events_without_customer",
            "product_events_without_account",
            "product_event_customer_account_mismatch",
            "kyc_applications_without_customer",
            "customers_without_kyc",
        ]:
            print(f"{key}: {validations[key]}")

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()
