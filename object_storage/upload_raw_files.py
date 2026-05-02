from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from object_storage.s3_client import get_bucket_name, get_s3_client


def upload_file_to_s3(local_file_path: str, s3_key: str) -> str:
    local_path = Path(local_file_path)

    if not local_path.exists():
        raise FileNotFoundError(f"Local file does not exist: {local_file_path}")

    s3_client = get_s3_client()
    bucket_name = get_bucket_name()

    print(f"Uploading local file: {local_path}")
    print(f"Target bucket: {bucket_name}")
    print(f"Target key: {s3_key}")

    s3_client.upload_file(
        Filename=str(local_path),
        Bucket=bucket_name,
        Key=s3_key,
    )

    s3_client.head_object(
        Bucket=bucket_name,
        Key=s3_key,
    )

    return f"s3://{bucket_name}/{s3_key}"


if __name__ == "__main__":
    print("upload_raw_files.py loaded successfully.")
    print("This is a helper file. Run this instead:")
    print("python scripts/run_customers_to_s3.py")