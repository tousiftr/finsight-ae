import os

import boto3
from botocore.client import Config
from dotenv import load_dotenv


def _env(*names: str, default: str | None = None) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    if default is not None:
        return default
    raise ValueError(f"Missing one of required environment variables: {', '.join(names)}")


def get_s3_client():
    load_dotenv()

    endpoint_url = _env("R2_ENDPOINT_URL", "R2_ENDPOINT", "S3_ENDPOINT_URL")
    access_key_id = _env("R2_ACCESS_KEY_ID", "S3_ACCESS_KEY_ID")
    secret_access_key = _env("R2_SECRET_ACCESS_KEY", "S3_SECRET_ACCESS_KEY")
    region_name = _env("R2_REGION", "S3_REGION", default="auto")

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region_name,
        config=Config(signature_version="s3v4"),
    )


def get_bucket_name() -> str:
    load_dotenv()
    return _env("R2_BUCKET_NAME", "R2_BUCKET", "S3_BUCKET_NAME")
