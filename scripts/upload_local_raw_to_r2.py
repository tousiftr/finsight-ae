"""Upload local data/raw JSONL files to Cloudflare R2 using matching relative keys."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from object_storage.upload_raw_files import upload_file_to_s3

DOMAINS = {
    "customers",
    "accounts",
    "merchants",
    "transactions",
    "product_events",
    "kyc_applications",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload local FinSight raw JSONL files to R2.")
    parser.add_argument("--raw-root", default="data/raw", help="Root folder for local raw partitions.")
    parser.add_argument("--domain", choices=sorted(DOMAINS), help="Optional single domain to upload.")
    return parser.parse_args()


def load_env() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(PROJECT_ROOT / ".env.dbt", override=False)


def require_r2_env() -> None:
    endpoint = os.getenv("R2_ENDPOINT_URL") or os.getenv("R2_ENDPOINT") or os.getenv("S3_ENDPOINT_URL")
    access_key = os.getenv("R2_ACCESS_KEY_ID") or os.getenv("S3_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY") or os.getenv("S3_SECRET_ACCESS_KEY")
    bucket = os.getenv("R2_BUCKET_NAME") or os.getenv("R2_BUCKET") or os.getenv("S3_BUCKET_NAME")
    missing = []
    if not endpoint:
        missing.append("R2_ENDPOINT_URL/R2_ENDPOINT/S3_ENDPOINT_URL")
    if not access_key:
        missing.append("R2_ACCESS_KEY_ID/S3_ACCESS_KEY_ID")
    if not secret_key:
        missing.append("R2_SECRET_ACCESS_KEY/S3_SECRET_ACCESS_KEY")
    if not bucket:
        missing.append("R2_BUCKET_NAME/R2_BUCKET/S3_BUCKET_NAME")
    if missing:
        raise RuntimeError("Missing R2 environment variables: " + ", ".join(missing))


def discover_files(raw_root: Path, domain: str | None) -> list[Path]:
    if domain:
        return sorted((raw_root / domain).glob(f"dt=*/batch_id=*/{domain}.jsonl"))
    return sorted(raw_root.glob("*/dt=*/batch_id=*/*.jsonl"))


def main() -> None:
    args = parse_args()
    load_env()
    require_r2_env()

    raw_root = Path(args.raw_root).resolve()
    if not raw_root.exists():
        raise FileNotFoundError(f"Raw root does not exist: {raw_root}")

    files = discover_files(raw_root, args.domain)
    if not files:
        print(f"No JSONL files found under {raw_root}")
        return

    for path in files:
        key = path.relative_to(raw_root).as_posix()
        uri = upload_file_to_s3(str(path), key)
        print(f"uploaded: {path} -> {uri}")

    print(f"Uploaded {len(files)} local raw files to R2.")


if __name__ == "__main__":
    main()
