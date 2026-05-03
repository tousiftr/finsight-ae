import argparse
import os
from pathlib import Path

import boto3
from botocore.config import Config
from dotenv import load_dotenv


def load_project_env() -> None:
    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env", override=True)


def get_env_value(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    raise RuntimeError("Missing required environment variable. Tried: " + ", ".join(names))


def get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=get_env_value("S3_ENDPOINT_URL", "R2_ENDPOINT_URL"),
        aws_access_key_id=get_env_value("S3_ACCESS_KEY_ID", "R2_ACCESS_KEY_ID"),
        aws_secret_access_key=get_env_value("S3_SECRET_ACCESS_KEY", "R2_SECRET_ACCESS_KEY"),
        region_name=os.getenv("S3_REGION", "auto"),
        config=Config(signature_version="s3v4"),
    )


def assert_file_ready(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing expected local file: {path}")
    if path.stat().st_size == 0:
        raise RuntimeError(f"Expected local file is empty: {path}")


def upload_file(s3_client, bucket_name: str, local_path: Path, object_key: str) -> None:
    assert_file_ready(local_path)
    s3_client.upload_file(Filename=str(local_path), Bucket=bucket_name, Key=object_key)
    print(f"Uploaded: {object_key}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload a dt+batch micro-batch to Cloudflare R2.")
    parser.add_argument("--dt", required=True, help="Batch date in YYYY-MM-DD")
    parser.add_argument("--batch-id", required=True, help="Batch id in YYYYMMDD_HHMM")
    args = parser.parse_args()

    load_project_env()
    project_root = Path(__file__).resolve().parents[1]

    dt = args.dt
    batch_id = args.batch_id

    customers_path = project_root / "data" / "raw" / "customers" / f"dt={dt}" / f"batch_id={batch_id}" / "customers.jsonl"
    accounts_path = project_root / "data" / "raw" / "accounts" / f"dt={dt}" / f"batch_id={batch_id}" / "accounts.jsonl"
    transactions_path = project_root / "data" / "raw" / "transactions" / f"dt={dt}" / f"batch_id={batch_id}" / "transactions.jsonl"

    customers_key = f"customers/dt={dt}/batch_id={batch_id}/customers.jsonl"
    accounts_key = f"accounts/dt={dt}/batch_id={batch_id}/accounts.jsonl"
    transactions_key = f"transactions/dt={dt}/batch_id={batch_id}/transactions.jsonl"

    bucket_name = get_env_value("S3_BUCKET_NAME", "R2_BUCKET_NAME")
    s3_client = get_r2_client()

    print(f"BATCH_DT={dt}")
    print(f"BATCH_ID={batch_id}")

    upload_file(s3_client, bucket_name, customers_path, customers_key)
    upload_file(s3_client, bucket_name, accounts_path, accounts_key)
    upload_file(s3_client, bucket_name, transactions_path, transactions_key)

    print("R2 keys uploaded:")
    print(customers_key)
    print(accounts_key)
    print(transactions_key)


if __name__ == "__main__":
    main()
