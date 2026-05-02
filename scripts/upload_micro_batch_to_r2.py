import json
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

    raise RuntimeError(
        "Missing required environment variable. Tried: " + ", ".join(names)
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


def upload_file(s3_client, bucket_name: str, local_path: str, object_key: str) -> None:
    path = Path(local_path)

    if not path.exists():
        raise FileNotFoundError(f"Missing local file: {path}")

    s3_client.upload_file(
        Filename=str(path),
        Bucket=bucket_name,
        Key=object_key,
    )

    print(f"Uploaded {path} -> s3://{bucket_name}/{object_key}")


def main() -> None:
    load_project_env()

    project_root = Path(__file__).resolve().parents[1]
    manifest_path = project_root / "data" / "raw" / "latest_micro_batch.json"

    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Missing manifest: {manifest_path}. Run generate_micro_batch.py first."
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    bucket_name = get_env_value("S3_BUCKET_NAME", "R2_BUCKET_NAME")
    s3_client = get_r2_client()

    upload_file(
        s3_client=s3_client,
        bucket_name=bucket_name,
        local_path=manifest["customers_path"],
        object_key=manifest["customers_key"],
    )

    upload_file(
        s3_client=s3_client,
        bucket_name=bucket_name,
        local_path=manifest["accounts_path"],
        object_key=manifest["accounts_key"],
    )

    upload_file(
        s3_client=s3_client,
        bucket_name=bucket_name,
        local_path=manifest["transactions_path"],
        object_key=manifest["transactions_key"],
    )

    print("Micro-batch upload completed.")


if __name__ == "__main__":
    main()