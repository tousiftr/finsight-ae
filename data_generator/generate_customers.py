import random
from datetime import datetime, timezone

from faker import Faker


fake = Faker()

SIGNUP_CHANNELS = ["organic", "paid_search", "referral", "social", "partner"]
SIGNUP_CHANNEL_WEIGHTS = [40, 25, 15, 15, 5]
KYC_STATUSES = ["approved", "manual_review", "pending", "rejected", "expired"]
KYC_STATUS_WEIGHTS = [68, 12, 12, 6, 2]
CUSTOMER_SEGMENTS = ["mass_market", "emerging_affluent", "affluent", "student", "smb_owner"]
EMPLOYMENT_STATUSES = ["employed", "self_employed", "student", "unemployed", "retired"]
INCOME_BANDS = ["0_25k", "25k_50k", "50k_100k", "100k_250k", "250k_plus"]
RISK_SEGMENTS = ["low", "medium", "high"]
COUNTRY_CITIES = {
    "BD": ["Dhaka", "Chittagong", "Sylhet", "Khulna"],
    "US": ["New York", "Austin", "Seattle", "San Francisco"],
    "GB": ["London", "Manchester", "Birmingham", "Leeds"],
    "SG": ["Singapore"],
    "AE": ["Dubai", "Abu Dhabi", "Sharjah"],
}
COUNTRY_WEIGHTS = [35, 30, 15, 10, 10]


def make_customer_id(index: int) -> str:
    return f"C{index:05d}"


def generate_customers(row_count: int, start_number: int = 1) -> list[dict]:
    now_iso = datetime.now(timezone.utc).isoformat()
    customers = []

    for customer_number in range(start_number, start_number + row_count):
        country = random.choices(list(COUNTRY_CITIES), weights=COUNTRY_WEIGHTS, k=1)[0]
        created_at = fake.date_time_between(
            start_date="-30d",
            end_date="now",
            tzinfo=timezone.utc,
        ).isoformat()
        phone = fake.phone_number()
        customers.append(
            {
                "customer_id": make_customer_id(customer_number),
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "email": fake.unique.email(),
                "phone": phone,
                "phone_number": phone,
                "date_of_birth": fake.date_of_birth(minimum_age=18, maximum_age=80).isoformat(),
                "country": country,
                "city": random.choice(COUNTRY_CITIES[country]),
                "signup_channel": random.choices(
                    SIGNUP_CHANNELS,
                    weights=SIGNUP_CHANNEL_WEIGHTS,
                    k=1,
                )[0],
                "customer_segment": random.choices(CUSTOMER_SEGMENTS, weights=[45, 20, 12, 15, 8], k=1)[0],
                "employment_status": random.choices(EMPLOYMENT_STATUSES, weights=[58, 18, 12, 7, 5], k=1)[0],
                "income_band": random.choices(INCOME_BANDS, weights=[22, 33, 28, 14, 3], k=1)[0],
                "risk_segment": random.choices(RISK_SEGMENTS, weights=[72, 23, 5], k=1)[0],
                "kyc_status": random.choices(
                    KYC_STATUSES,
                    weights=KYC_STATUS_WEIGHTS,
                    k=1,
                )[0],
                "created_at": created_at,
                "updated_at": now_iso,
            }
        )

    return customers


def generate_customer_updates(
    existing_customers: list[dict],
    batch_start: datetime,
    batch_end: datetime,
    max_updates: int = 5,
) -> list[dict]:
    """Create append-only newer versions for a few existing customers."""
    candidates = [customer for customer in existing_customers if customer.get("customer_id")]
    if not candidates or max_updates <= 0:
        return []

    update_count = random.randint(0, min(max_updates, len(candidates)))
    if update_count == 0:
        return []

    updates: list[dict] = []
    for customer in random.sample(candidates, k=update_count):
        updated_customer = dict(customer)
        current_kyc = str(updated_customer.get("kyc_status") or "").lower()
        next_kyc_choices = [status for status in KYC_STATUSES if status != current_kyc] or KYC_STATUSES
        current_segment = updated_customer.get("customer_segment")
        next_segment_choices = [segment for segment in CUSTOMER_SEGMENTS if segment != current_segment] or CUSTOMER_SEGMENTS
        current_risk = updated_customer.get("risk_segment")
        next_risk_choices = [risk for risk in RISK_SEGMENTS if risk != current_risk] or RISK_SEGMENTS

        updated_at = batch_start + (batch_end - batch_start) * random.random()
        updated_customer["kyc_status"] = random.choices(next_kyc_choices, weights=None, k=1)[0]
        updated_customer["risk_segment"] = random.choice(next_risk_choices)
        updated_customer["customer_segment"] = random.choice(next_segment_choices)
        updated_customer["updated_at"] = updated_at.isoformat()
        updates.append(updated_customer)

    return updates
