import random
from datetime import datetime, timezone

from faker import Faker


fake = Faker()

SIGNUP_CHANNELS = ["organic", "paid_search", "referral", "social", "partner"]
SIGNUP_CHANNEL_WEIGHTS = [40, 25, 15, 15, 5]
KYC_STATUSES = ["approved", "manual_review", "pending", "rejected", "expired"]
KYC_STATUS_WEIGHTS = [75, 10, 8, 5, 2]


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
                "signup_channel": random.choices(
                    SIGNUP_CHANNELS,
                    weights=SIGNUP_CHANNEL_WEIGHTS,
                    k=1,
                )[0],
                "kyc_status": random.choices(
                    KYC_STATUSES,
                    weights=KYC_STATUS_WEIGHTS,
                    k=1,
                )[0],
                "created_at": fake.date_time_between(
                    start_date="-2y",
                    end_date="now",
                    tzinfo=timezone.utc,
                ).isoformat(),
                "updated_at": now_iso,
            }
        )

    return customers
