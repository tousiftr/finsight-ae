import random
from datetime import datetime, timezone

from faker import Faker


fake = Faker()

SIGNUP_CHANNELS = ["organic", "paid_search", "referral", "partner", "social"]
KYC_STATUSES = ["pending", "approved", "rejected", "manual_review"]


def make_customer_id(index: int) -> str:
    return f"C{index:05d}"


def generate_customers(row_count: int) -> list[dict]:
    now_iso = datetime.now(timezone.utc).isoformat()
    customers = []

    for idx in range(1, row_count + 1):
        customers.append(
            {
                "customer_id": make_customer_id(idx),
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "email": fake.unique.email(),
                "phone_number": fake.phone_number(),
                "country": fake.country_code(),
                "signup_channel": random.choice(SIGNUP_CHANNELS),
                "kyc_status": random.choice(KYC_STATUSES),
                "created_at": fake.date_time_between(
                    start_date="-2y",
                    end_date="now",
                    tzinfo=timezone.utc,
                ).isoformat(),
                "updated_at": now_iso,
            }
        )

    return customers
