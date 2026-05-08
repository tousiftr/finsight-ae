import argparse
import hashlib
import json
import os
import re
import ssl
from urllib.parse import unquote, urlparse

import boto3
import pg8000.dbapi
from dotenv import load_dotenv


CUSTOMERS_KEY_PATTERN = re.compile(
    r"^customers/dt=(?P<dt>\d{4}-\d{2}-\d{2})/batch_id=(?P<batch_id>[^/]+)/customers\.jsonl$"
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Load customer JSONL from Cloudflare R2 into Neon raw.raw_customers."
    )

    parser.add_argument(
        "--latest",
        action="store_true",
        help="Load the latest customers JSONL object from R2.",
    )

    parser.add_argument(
        "--key",
        type=str,
        default=None,
        help="Specific R2 object key to load.",
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=50,
        help="Number of rows to insert per database batch.",
    )

    return parser.parse_args()


def get_s3_client():
    required_env_vars = [
        "S3_ENDPOINT_URL",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
        "S3_BUCKET_NAME",
    ]

    missing = [name for name in required_env_vars if not os.getenv(name)]

    if missing:
        raise RuntimeError(
            f"Missing required S3 environment variables: {', '.join(missing)}"
        )

    return boto3.client(
        "s3",
        endpoint_url=os.getenv("S3_ENDPOINT_URL"),
        aws_access_key_id=os.getenv("S3_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY"),
        region_name=os.getenv("S3_REGION", "auto"),
    )


def get_neon_connection():
    database_url = os.getenv("DATABASE_URL") or os.getenv("NEON_DATABASE_URL")

    if database_url:
        parsed = urlparse(database_url)

        return pg8000.dbapi.connect(
            user=unquote(parsed.username),
            password=unquote(parsed.password),
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=unquote(parsed.path.lstrip("/")),
            ssl_context=ssl.create_default_context(),
        )

    return pg8000.dbapi.connect(
        user=os.getenv("PGUSER") or os.getenv("POSTGRES_USER"),
        password=os.getenv("PGPASSWORD") or os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("PGHOST") or os.getenv("POSTGRES_HOST"),
        port=int(os.getenv("PGPORT") or 5432),
        database=os.getenv("PGDATABASE") or os.getenv("POSTGRES_DB"),
        ssl_context=ssl.create_default_context(),
    )


def find_latest_customers_key(s3_client, bucket_name: str) -> str:
    paginator = s3_client.get_paginator("list_objects_v2")
    latest_object = None

    for page in paginator.paginate(Bucket=bucket_name, Prefix="customers/"):
        for obj in page.get("Contents", []):
            key = obj["Key"]

            if not key.endswith("/customers.jsonl"):
                continue

            if not CUSTOMERS_KEY_PATTERN.match(key):
                continue

            if latest_object is None or obj["LastModified"] > latest_object["LastModified"]:
                latest_object = obj

    if latest_object is None:
        raise RuntimeError("No customers JSONL object found in R2.")

    return latest_object["Key"]


def parse_partition_from_key(object_key: str) -> tuple[str, str]:
    match = CUSTOMERS_KEY_PATTERN.match(object_key)

    if not match:
        raise ValueError(
            "Object key does not match expected format: "
            "customers/dt=YYYY-MM-DD/batch_id=YYYYMMDD_HHMM/customers.jsonl"
        )

    return match.group("dt"), match.group("batch_id")


def read_jsonl_from_s3(s3_client, bucket_name: str, object_key: str) -> list[dict]:
    response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
    body = response["Body"].read().decode("utf-8")

    records = []

    for line_number, line in enumerate(body.splitlines(), start=1):
        line = line.strip()

        if not line:
            continue

        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc

    return records


def calculate_raw_record_hash(record: dict) -> str:
    canonical_json = json.dumps(record, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def ensure_raw_customers_table(conn):
    cursor = conn.cursor()

    cursor.execute("create schema if not exists raw;")

    cursor.execute(
        """
        create table if not exists raw.raw_customers (
            id bigserial primary key,
            source_system text not null default 'cloudflare_r2',
            source_bucket text not null,
            source_object_key text not null,
            source_file_path text not null,
            payload jsonb not null,
            dt date not null,
            batch_id text not null,
            raw_record_hash text not null,
            loaded_at timestamptz not null default now()
        );
        """
    )

    cursor.execute(
        """
        create unique index if not exists ux_raw_customers_source_object_key_raw_record_hash
        on raw.raw_customers (source_object_key, raw_record_hash);
        """
    )

    conn.commit()


def get_table_columns(conn) -> set[str]:
    cursor = conn.cursor()

    cursor.execute(
        """
        select column_name
        from information_schema.columns
        where table_schema = 'raw'
          and table_name = 'raw_customers';
        """
    )

    return {row[0] for row in cursor.fetchall()}


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def get_table_count(conn) -> int:
    cursor = conn.cursor()
    cursor.execute("select count(*) from raw.raw_customers;")
    return cursor.fetchone()[0]


def get_batch_count(conn, batch_id: str) -> int:
    cursor = conn.cursor()

    cursor.execute(
        """
        select count(*)
        from raw.raw_customers
        where batch_id = %s;
        """,
        (batch_id,),
    )

    return cursor.fetchone()[0]


def load_records_to_neon(
    conn,
    records: list[dict],
    dt: str,
    batch_id: str,
    source_bucket: str,
    source_object_key: str,
    chunk_size: int = 50,
):
    source_file_path = f"s3://{source_bucket}/{source_object_key}"

    table_columns = get_table_columns(conn)

    possible_insert_columns = [
        "source_system",
        "source_bucket",
        "source_object_key",
        "source_file_path",
        "payload",
        "dt",
        "batch_id",
        "raw_record_hash",
    ]

    insert_columns = [
        column for column in possible_insert_columns if column in table_columns
    ]

    required_for_loader = {
        "payload",
        "dt",
        "batch_id",
        "source_object_key",
        "raw_record_hash",
    }

    missing_required = required_for_loader - set(insert_columns)

    if missing_required:
        raise RuntimeError(
            "raw.raw_customers is missing required columns for this loader: "
            + ", ".join(sorted(missing_required))
        )

    all_rows = []

    for record in records:
        values_by_column = {
            "source_system": "cloudflare_r2",
            "source_bucket": source_bucket,
            "source_object_key": source_object_key,
            "source_file_path": source_file_path,
            "payload": json.dumps(record, sort_keys=True),
            "dt": dt,
            "batch_id": batch_id,
            "raw_record_hash": calculate_raw_record_hash(record),
        }

        all_rows.append(tuple(values_by_column[column] for column in insert_columns))

    quoted_columns = ", ".join(quote_identifier(column) for column in insert_columns)

    row_placeholder_parts = []

    for column in insert_columns:
        if column == "payload":
            row_placeholder_parts.append("%s::jsonb")
        else:
            row_placeholder_parts.append("%s")

    single_row_placeholder = "(" + ", ".join(row_placeholder_parts) + ")"

    cursor = conn.cursor()
    total_checked = 0

    for start_index in range(0, len(all_rows), chunk_size):
        chunk = all_rows[start_index : start_index + chunk_size]

        values_sql = ", ".join([single_row_placeholder] * len(chunk))

        flat_params = []

        for row in chunk:
            flat_params.extend(row)

        insert_sql = f"""
            insert into raw.raw_customers (
                {quoted_columns}
            )
            values
                {values_sql}
            on conflict (source_object_key, raw_record_hash) do nothing;
        """

        cursor.execute(insert_sql, tuple(flat_params))
        conn.commit()

        total_checked += len(chunk)
        print(f"Inserted/checked {total_checked} of {len(all_rows)} rows...")

    print("Finished insert chunks.")


def main():
    load_dotenv()

    args = parse_args()

    if not args.latest and not args.key:
        raise RuntimeError("Use either --latest or --key <object_key>.")

    bucket_name = os.getenv("S3_BUCKET_NAME")

    if not bucket_name:
        raise RuntimeError("Missing required environment variable: S3_BUCKET_NAME")

    s3_client = get_s3_client()

    if args.key:
        object_key = args.key
    else:
        object_key = find_latest_customers_key(s3_client, bucket_name)

    dt, batch_id = parse_partition_from_key(object_key)

    print(f"Loading from: s3://{bucket_name}/{object_key}")

    records = read_jsonl_from_s3(
        s3_client=s3_client,
        bucket_name=bucket_name,
        object_key=object_key,
    )

    print(f"Rows read from JSONL: {len(records)}")

    conn = get_neon_connection()

    try:
        ensure_raw_customers_table(conn)

        before_count = get_table_count(conn)
        before_batch_count = get_batch_count(conn, batch_id)

        load_records_to_neon(
            conn=conn,
            records=records,
            dt=dt,
            batch_id=batch_id,
            source_bucket=bucket_name,
            source_object_key=object_key,
            chunk_size=args.chunk_size,
        )

        after_count = get_table_count(conn)
        after_batch_count = get_batch_count(conn, batch_id)

        print("\nLoad summary")
        print("------------")
        print(f"Table rows before: {before_count}")
        print(f"Table rows after:  {after_count}")
        print(f"Rows inserted:     {after_count - before_count}")
        print(f"Batch rows before: {before_batch_count}")
        print(f"Batch rows after:  {after_batch_count}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()