import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import boto3
import pg8000.dbapi
from botocore.config import Config
from dotenv import load_dotenv


CUSTOMERS_KEY_PATTERN = re.compile(
    r"^customers/dt=(?P<dt>\d{4}-\d{2}-\d{2})/batch_id=(?P<batch_id>[^/]+)/customers\.jsonl$"
)


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def connect_to_neon():
    database_url = get_required_env("NEON_DATABASE_URL")
    parsed = urlparse(database_url)

    return pg8000.dbapi.connect(
        user=unquote(parsed.username or ""),
        password=unquote(parsed.password or ""),
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=unquote(parsed.path.lstrip("/")),
        ssl_context=True,
    )


def get_env_value(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value

    raise ValueError(
        f"Missing required environment variable. Tried: {', '.join(names)}"
    )


def get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=get_env_value("S3_ENDPOINT_URL", "R2_ENDPOINT_URL"),
        aws_access_key_id=get_env_value("S3_ACCESS_KEY_ID", "R2_ACCESS_KEY_ID"),
        aws_secret_access_key=get_env_value("S3_SECRET_ACCESS_KEY", "R2_SECRET_ACCESS_KEY"),
        region_name=os.getenv("S3_REGION", "auto"),
        config=Config(signature_version="s3v4"),
    )


def parse_key_partitions(object_key: str) -> tuple[str | None, str | None]:
    match = CUSTOMERS_KEY_PATTERN.match(object_key)
    if not match:
        return None, None

    return match.group("dt"), match.group("batch_id")


def find_latest_customers_key(s3_client, bucket_name: str) -> str:
    paginator = s3_client.get_paginator("list_objects_v2")
    candidates: list[dict[str, Any]] = []

    for page in paginator.paginate(Bucket=bucket_name, Prefix="customers/"):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith("/customers.jsonl"):
                candidates.append(obj)

    if not candidates:
        raise FileNotFoundError(
            f"No customers.jsonl files found in bucket {bucket_name} under customers/"
        )

    latest = max(candidates, key=lambda obj: obj["LastModified"])
    return latest["Key"]


def read_jsonl_from_r2(s3_client, bucket_name: str, object_key: str) -> list[dict[str, Any]]:
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


def stable_record_hash(record: dict[str, Any]) -> str:
    serialized = json.dumps(record, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def extract_customer_id(record: dict[str, Any]) -> str | None:
    for key in ["customer_id", "id", "customer_uuid"]:
        value = record.get(key)
        if value is not None:
            return str(value)

    return None


def ensure_raw_tables_exist(conn) -> None:
    sql_path = Path(__file__).resolve().parent / "create_raw_customers.sql"

    with open(sql_path, "r", encoding="utf-8") as file:
        ddl = file.read()

    cur = conn.cursor()

    try:
        for statement in ddl.split(";"):
            statement = statement.strip()

            if statement:
                cur.execute(statement)

        conn.commit()

    finally:
        cur.close()


def insert_customers(
    conn,
    bucket_name: str,
    object_key: str,
    records: list[dict[str, Any]],
) -> tuple[int, int]:
    dt_value, batch_id = parse_key_partitions(object_key)
    source_file_path = f"s3://{bucket_name}/{object_key}"

    inserted = 0
    skipped = 0

    insert_sql = """
        insert into raw.raw_customers (
            customer_id,
            payload,
            source_bucket,
            source_object_key,
            source_file_path,
            dt,
            batch_id,
            raw_record_hash
        )
        values (
            %s,
            %s::jsonb,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )
        on conflict (source_object_key, raw_record_hash)
        do nothing
        returning raw_customer_id
    """

    cur = conn.cursor()

    try:
        for record in records:
            cur.execute(
                insert_sql,
                (
                    extract_customer_id(record),
                    json.dumps(record, sort_keys=True, default=str),
                    bucket_name,
                    object_key,
                    source_file_path,
                    dt_value,
                    batch_id,
                    stable_record_hash(record),
                ),
            )

            returned_row = cur.fetchone()

            if returned_row:
                inserted += 1
            else:
                skipped += 1

    finally:
        cur.close()

    return inserted, skipped


def write_ingestion_log(
    conn,
    bucket_name: str,
    object_key: str,
    rows_read: int,
    rows_inserted: int,
    rows_skipped: int,
    status: str,
    started_at: datetime,
    error_message: str | None = None,
) -> None:
    dt_value, batch_id = parse_key_partitions(object_key)

    cur = conn.cursor()

    try:
        cur.execute(
            """
            insert into raw.raw_ingestion_log (
                source_system,
                source_bucket,
                source_object_key,
                target_table,
                dt,
                batch_id,
                rows_read,
                rows_inserted,
                rows_skipped,
                status,
                error_message,
                started_at
            )
            values (
                'cloudflare_r2',
                %s,
                %s,
                'raw.raw_customers',
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                bucket_name,
                object_key,
                dt_value,
                batch_id,
                rows_read,
                rows_inserted,
                rows_skipped,
                status,
                error_message,
                started_at,
            ),
        )

    finally:
        cur.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load customers JSONL from Cloudflare R2 into Neon raw.raw_customers."
    )

    parser.add_argument(
        "--key",
        help="R2 object key. Example: customers/dt=2026-05-02/batch_id=20260502_0200/customers.jsonl",
    )

    parser.add_argument(
        "--latest",
        action="store_true",
        help="Load the latest customers.jsonl found under customers/",
    )

    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env", override=True)

    bucket_name = get_env_value("S3_BUCKET_NAME", "R2_BUCKET_NAME")
    s3_client = get_r2_client()

    if args.key:
        object_key = args.key
    elif args.latest:
        object_key = find_latest_customers_key(s3_client, bucket_name)
    else:
        raise ValueError("Provide either --key or --latest")

    started_at = datetime.now(timezone.utc)

    print(f"Loading from: s3://{bucket_name}/{object_key}")

    records = read_jsonl_from_r2(
        s3_client=s3_client,
        bucket_name=bucket_name,
        object_key=object_key,
    )

    print(f"Rows read from JSONL: {len(records)}")

    conn = connect_to_neon()

    try:
        ensure_raw_tables_exist(conn)

        inserted, skipped = insert_customers(
            conn=conn,
            bucket_name=bucket_name,
            object_key=object_key,
            records=records,
        )

        write_ingestion_log(
            conn=conn,
            bucket_name=bucket_name,
            object_key=object_key,
            rows_read=len(records),
            rows_inserted=inserted,
            rows_skipped=skipped,
            status="success",
            started_at=started_at,
        )

        conn.commit()

        print("Load completed successfully.")
        print(f"Rows inserted: {inserted}")
        print(f"Rows skipped as duplicates: {skipped}")

    except Exception as exc:
        conn.rollback()

        try:
            write_ingestion_log(
                conn=conn,
                bucket_name=bucket_name,
                object_key=object_key,
                rows_read=len(records),
                rows_inserted=0,
                rows_skipped=0,
                status="failed",
                started_at=started_at,
                error_message=str(exc),
            )
            conn.commit()
        except Exception:
            conn.rollback()

        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()