from pathlib import Path
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_generator.generate_customers import generate_customers
from object_storage.upload_raw_files import upload_file_to_s3


def main() -> None:
    run_time = datetime.now(ZoneInfo("Asia/Dhaka"))

    dt = run_time.strftime("%Y-%m-%d")
    batch_id = run_time.strftime("%Y%m%d_%H%M")

    local_file_path = f"data/raw/customers/dt={dt}/batch_id={batch_id}/customers.jsonl"
    s3_key = f"customers/dt={dt}/batch_id={batch_id}/customers.jsonl"

    generated_file = generate_customers(
        row_count=1000,
        output_file_path=local_file_path,
    )

    s3_uri = upload_file_to_s3(
        local_file_path=generated_file,
        s3_key=s3_key,
    )

    print(f"Generated local file: {generated_file}")
    print(f"Uploaded to: {s3_uri}")


if __name__ == "__main__":
    main()