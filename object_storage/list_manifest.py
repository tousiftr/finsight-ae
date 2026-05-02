from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from object_storage.s3_client import get_bucket_name, get_s3_client


def list_objects(prefix: str = "") -> list[dict]:
    s3_client = get_s3_client()
    bucket_name = get_bucket_name()

    response = s3_client.list_objects_v2(
        Bucket=bucket_name,
        Prefix=prefix,
    )

    objects = response.get("Contents", [])

    return [
        {
            "key": item["Key"],
            "size_bytes": item["Size"],
            "last_modified": item["LastModified"].isoformat(),
        }
        for item in objects
    ]


if __name__ == "__main__":
    files = list_objects("customers/")

    if not files:
        print("No customer files found in S3 yet.")
    else:
        for file in files:
            print(file)