import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from faker import Faker


fake = Faker()


def generate_customers(row_count: int, output_file_path: str) -> str:
    output_path = Path(output_file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now(UTC)

    with output_path.open("w", encoding="utf-8") as file:
        for _ in range(row_count):
            customer = {
                "customer_id": str(uuid.uuid4()),
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "email": fake.unique.email(),
                "phone_number": fake.phone_number(),
                "country": fake.country_code(),
                "signup_channel": fake.random_element(
                    elements=["organic", "paid_search", "referral", "partner", "social"]
                ),
                "kyc_status": fake.random_element(
                    elements=["pending", "approved", "rejected", "manual_review"]
                ),
                "created_at": fake.date_time_between(
                    start_date="-2y",
                    end_date="now",
                    tzinfo=UTC,
                ).isoformat(),
                "updated_at": now.isoformat(),
            }

            file.write(json.dumps(customer) + "\n")

    return str(output_path)