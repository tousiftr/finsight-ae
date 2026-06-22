import argparse
import hashlib
import json
import os
import re
import ssl
from pathlib import Path
from urllib.parse import unquote, urlparse

import boto3
import pg8000.dbapi
from dotenv import load_dotenv


ENTITY_NAME = "accounts"
RAW_TABLE = "raw.raw_accounts"
RAW_TABLE_SCHEMA = "raw"
RAW_TABLE_NAME = "raw_accounts"
OBJECT_PREFIX = "accounts/"
FILE_NAME = "accounts.jsonl"

KEY_PATTERN = re.compile(
    r"^accounts/dt=(?P<dt>\d{4}-\d{2}-\d{2})/batch_id=(?P<batch_id>[^/]+)/accounts\.jsonl$"
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=f"Load {ENTITY_NAME} JSONL from Cloudflare R2 into Neon {RAW_TABLE}."
    )

    parser.add_argument(
        "--latest",
        action="store_true",
        help=f"Load the latest {FILE_NAME} object from R2.",
    )

    parser.add_argument(
        "--key",
        type=str,
        default=None,
        help=f"Specific R2 object key to load. Example: {OBJECT_PREFIX}dt=2026-05-02/batch_id=20260502_0200/{FILE_NAME}",
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="Number of rows to insert per database batch.",
    )

    return parser.parse_args()


def load_project_env() -> None:
    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env", override=True)
    load_dotenv(override=False)


def get_env_value(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value

    raise RuntimeError(
        "Missing required environment variable. Tried: " + ", ".join(names)
    )


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=get_env_value("S3_ENDPOINT_URL", "R2_ENDPOINT_URL"),
        aws_access_key_id=get_env_value("S3_ACCESS_KEY_ID", "R2_ACCESS_KEY_ID"),
        aws_secret_access_key=get_env_value("S3_SECRET_ACCESS_KEY", "R2_SECRET_ACCESS_KEY"),
        region_name=os.getenv("S3_REGION", "auto"),
    )


def get_neon_connection():
    database_url = os.getenv("DATABASE_URL") or os.getenv("NEON_DATABASE_URL")

    if database_url:
        parsed = urlparse(database_url)

        return pg8000.dbapi.connect(
            user=unquote(parsed.username or ""),
            password=unquote(parsed.password or ""),
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


def ensure_raw_table(conn) -> None:
    cursor = conn.cursor()

    try:
        cursor.execute("create schema if not exists raw;")

        cursor.execute(
            f"""
            create table if not exists {RAW_TABLE} (
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
            f"""
            create unique index if not exists ux_{RAW_TABLE_NAME}_source_object_key_raw_record_hash
            on {RAW_TABLE} (source_object_key, raw_record_hash);
            """
        )

        cursor.execute(
            f"""
            create index if not exists ix_{RAW_TABLE_NAME}_dt_batch_id
            on {RAW_TABLE} (dt, batch_id);
            """
        )

        conn.commit()

    finally:
        cursor.close()


def find_latest_key(s3_client, bucket_name: str) -> str:
    paginator = s3_client.get_paginator("list_objects_v2")
    latest_object = None

    for page in paginator.paginate(Bucket=bucket_name, Prefix=OBJECT_PREFIX):
        for obj in page.get("Contents", []):
            key = obj["Key"]

            if not key.endswith("/" + FILE_NAME):
                continue

            if not KEY_PATTERN.match(key):
                continue

            if latest_object is None or obj["LastModified"] > latest_object["LastModified"]:
                latest_object = obj

    if latest_object is None:
        raise RuntimeError(
            f"No {FILE_NAME} object found in R2 under prefix {OBJECT_PREFIX}."
        )

    return latest_object["Key"]


def parse_partition_from_key(object_key: str) -> tuple[str, str]:
    match = KEY_PATTERN.match(object_key)

    if not match:
        raise ValueError(
            "Object key does not match expected format: "
            f"{OBJECT_PREFIX}dt=YYYY-MM-DD/batch_id=YYYYMMDD_HHMM/{FILE_NAME}"
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
            raise ValueError(
                f"Invalid JSON on line {line_number} in s3://{bucket_name}/{object_key}: {exc}"
            ) from exc

    return records


def calculate_raw_record_hash(record: dict) -> str:
    canonical_json = json.dumps(record, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def get_table_columns(conn) -> set[str]:
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            select column_name
            from information_schema.columns
            where table_schema = %s
              and table_name = %s;
            """,
            (RAW_TABLE_SCHEMA, RAW_TABLE_NAME),
        )

        return {row[0] for row in cursor.fetchall()}

    finally:
        cursor.close()


def quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def get_table_count(conn) -> int:
    cursor = conn.cursor()

    try:
        cursor.execute(f"select count(*) from {RAW_TABLE};")
        return cursor.fetchone()[0]

    finally:
        cursor.close()


def get_batch_count(conn, batch_id: str) -> int:
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"""
            select count(*)
            from {RAW_TABLE}
            where batch_id = %s;
            """,
            (batch_id,),
        )

        return cursor.fetchone()[0]

    finally:
        cursor.close()


def load_records_to_neon(
    conn,
    records: list[dict],
    dt: str,
    batch_id: str,
    source_bucket: str,
    source_object_key: str,
    chunk_size: int = 1000,
) -> None:
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
            f"{RAW_TABLE} is missing required columns for this loader: "
            + ", ".join(sorted(missing_required))
        )

    all_rows = []

    for record in records:
        values_by_column = {
            "source_system": "cloudflare_r2",
            "source_bucket": source_bucket,
            "source_object_key": source_object_key,
            "source_file_path": source_file_path,
            "payload": json.dumps(record, sort_keys=True, default=str),
            "dt": dt,
            "batch_id": batch_id,
            "raw_record_hash": calculate_raw_record_hash(record),
        }

        all_rows.append(tuple(values_by_column[column] for column in insert_columns))

    if not all_rows:
        print("No rows to load.")
        return

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

    try:
        for start_index in range(0, len(all_rows), chunk_size):
            chunk = all_rows[start_index : start_index + chunk_size]

            values_sql = ", ".join([single_row_placeholder] * len(chunk))

            flat_params = []

            for row in chunk:
                flat_params.extend(row)

            insert_sql = f"""
                insert into {RAW_TABLE} (
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

    finally:
        cursor.close()

    print("Finished insert chunks.")


def main():
    load_project_env()
    args = parse_args()

    if not args.latest and not args.key:
        raise RuntimeError("Use either --latest or --key <object_key>.")

    bucket_name = get_env_value("S3_BUCKET_NAME", "R2_BUCKET_NAME")
    s3_client = get_s3_client()

    if args.key:
        object_key = args.key
    else:
        object_key = find_latest_key(s3_client, bucket_name)

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
        ensure_raw_table(conn)

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
        print(f"Target table:       {RAW_TABLE}")
        print(f"Source object key:  {object_key}")
        print(f"Table rows before: {before_count}")
        print(f"Table rows after:  {after_count}")
        print(f"Rows inserted:     {after_count - before_count}")
        print(f"Batch rows before: {before_batch_count}")
        print(f"Batch rows after:  {after_batch_count}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
