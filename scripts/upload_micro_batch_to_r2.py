import argparse
from pathlib import Path
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from object_storage.s3_client import get_bucket_name, get_s3_client

 

DATASETS = ["customers", "accounts", "transactions", "product_events", "kyc_applications"]


def local_file(root: Path, dataset: str, dt: str, batch_id: str) -> Path:
    return root / "data" / "raw" / dataset / f"dt={dt}" / f"batch_id={batch_id}" / f"{dataset}.jsonl"


def object_key(dataset: str, dt: str, batch_id: str) -> str:
    return f"{dataset}/dt={dt}/batch_id={batch_id}/{dataset}.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload an exact dt+batch_id raw batch to Cloudflare R2")
    parser.add_argument("--dt", required=True)
    parser.add_argument("--batch-id", required=True)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    client = get_s3_client()
    bucket = get_bucket_name()

    print(f"BATCH_DT={args.dt}")
    print(f"BATCH_ID={args.batch_id}")

    for dataset in DATASETS:
        src = local_file(project_root, dataset, args.dt, args.batch_id)
        if not src.exists():
            raise FileNotFoundError(f"Missing required local file: {src}")
        key = object_key(dataset, args.dt, args.batch_id)
        client.upload_file(Filename=str(src), Bucket=bucket, Key=key)
        print(f"Uploaded: {key}")


if __name__ == "__main__":
    main()
