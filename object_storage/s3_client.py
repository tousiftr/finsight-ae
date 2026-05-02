import os
import boto3
from botocore.client import Config
from dotenv import load_dotenv


def get_s3_client():
    load_dotenv()

    endpoint_url = os.getenv("S3_ENDPOINT_URL")
    access_key_id = os.getenv("S3_ACCESS_KEY_ID")
    secret_access_key = os.getenv("S3_SECRET_ACCESS_KEY")
    region_name = os.getenv("S3_REGION", "auto")

    if not endpoint_url:
        raise ValueError("Missing S3_ENDPOINT_URL")
    if not access_key_id:
        raise ValueError("Missing S3_ACCESS_KEY_ID")
    if not secret_access_key:
        raise ValueError("Missing S3_SECRET_ACCESS_KEY")

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

    bucket_name = os.getenv("S3_BUCKET_NAME")

    if not bucket_name:
        raise ValueError("Missing S3_BUCKET_NAME")

    return bucket_name