from faker import Faker
from datetime import datetime, timezone
from pathlib import Path
import json
import random
import uuid

fake = Faker()

CUSTOMER_STATUSES = ["active", "inactive", "suspended", "closed"]
KYC_STATUSES = ["approved", "pending", "rejected"]
COUNTRIES = ["Bangladesh", "United States", "United Kingdom", "Germany", "Singapore"]
ACQUISITION_CHANNELS = ["organic", "paid_search", "social", "referral", "affiliate"]


def generate_customers(batch_id: str, number_of_customers: int = 100) -> list[dict]:
    customers = []

    for _ in range(number_of_customers):
        created_at = fake.date_time_between(
            start_date="-2y",
            end_date="now",
            tzinfo=timezone.utc
        )

        customer = {
            "customer_id": str(uuid.uuid4()),
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": fake.unique.email(),
            "phone_number": fake.phone_number(),
            "date_of_birth": fake.date_of_birth(minimum_age=18, maximum_age=75).isoformat(),
            "country": random.choice(COUNTRIES),
            "customer_status": random.choices(
                CUSTOMER_STATUSES,
                weights=[80, 10, 5, 5],
                k=1
            )[0],
            "kyc_status": random.choices(
                KYC_STATUSES,
                weights=[75, 15, 10],
                k=1
            )[0],
            "acquisition_channel": random.choice(ACQUISITION_CHANNELS),
            "created_at": created_at.isoformat(),
            "batch_id": batch_id
        }

        customers.append(customer)

    return customers


def write_jsonl(records: list[dict], output_path: str) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record) + "\n")


if __name__ == "__main__":
    now = datetime.now(timezone.utc)
    dt = now.strftime("%Y-%m-%d")
    batch_id = now.strftime("%Y%m%d_%H%M")

    customers = generate_customers(
        batch_id=batch_id,
        number_of_customers=100
    )

    output_path = f"data/raw/customers/dt={dt}/batch_id={batch_id}/customers.jsonl"

    write_jsonl(customers, output_path)

    print(f"Generated {len(customers)} customers")
    print(f"Wrote customers to: {output_path}")