import random
from datetime import datetime, timezone

from faker import Faker


fake = Faker()

SIGNUP_CHANNELS = ["organic", "paid_search", "referral", "social", "partner"]
SIGNUP_CHANNEL_WEIGHTS = [40, 25, 15, 15, 5]
KYC_STATUSES = ["approved", "manual_review", "pending", "rejected", "expired"]
KYC_STATUS_WEIGHTS = [62, 12, 18, 6, 2]
CUSTOMER_SEGMENTS = ["standard", "premium", "mass_market", "emerging_affluent", "affluent", "student", "smb_owner"]
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
                "customer_segment": random.choices(CUSTOMER_SEGMENTS, weights=[38, 8, 20, 12, 8, 9, 5], k=1)[0],
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


def generate_customer_updates(existing_customers: list[dict], batch_end: datetime, max_updates: int = 5) -> list[dict]:
    """Append-only customer profile changes for existing customers.

    Raw ingestion keeps every version as a new row; staging chooses the latest
    customer record by updated_at/loaded_at for current-state models while dbt
    snapshots preserve history.
    """
    if not existing_customers or max_updates <= 0:
        return []

    updates: list[dict] = []
    update_count = random.randint(0, min(max_updates, len(existing_customers)))
    for offset, customer in enumerate(random.sample(existing_customers, k=update_count), start=1):
        updated = dict(customer)
        previous_kyc = (updated.get("kyc_status") or "pending").lower()
        previous_risk = (updated.get("risk_segment") or "low").lower()
        previous_segment = updated.get("customer_segment") or "standard"

        change_type = random.choices(
            ["kyc", "risk", "segment"],
            weights=[58, 24, 18],
            k=1,
        )[0]
        if change_type == "kyc":
            if previous_kyc == "pending":
                updated["kyc_status"] = random.choices(["approved", "manual_review", "rejected"], weights=[78, 16, 6], k=1)[0]
            elif previous_kyc == "manual_review":
                updated["kyc_status"] = random.choices(["approved", "rejected", "pending"], weights=[64, 24, 12], k=1)[0]
            else:
                updated["kyc_status"] = random.choices([previous_kyc, "manual_review", "approved"], weights=[65, 20, 15], k=1)[0]
        elif change_type == "risk":
            updated["risk_segment"] = {"low": "medium", "medium": random.choice(["low", "high"]), "high": "medium"}.get(previous_risk, "medium")
        else:
            updated["customer_segment"] = random.choices(
                [previous_segment, "premium", "emerging_affluent", "affluent"],
                weights=[45, 25, 20, 10],
                k=1,
            )[0]

        # Preserve required customer fields even for older raw payloads.
        updated.setdefault("first_name", fake.first_name())
        updated.setdefault("last_name", fake.last_name())
        updated.setdefault("email", fake.unique.email())
        phone = updated.get("phone") or updated.get("phone_number") or fake.phone_number()
        updated["phone"] = phone
        updated["phone_number"] = phone
        updated.setdefault("date_of_birth", fake.date_of_birth(minimum_age=18, maximum_age=80).isoformat())
        country = updated.get("country") or random.choices(list(COUNTRY_CITIES), weights=COUNTRY_WEIGHTS, k=1)[0]
        updated["country"] = country
        updated["city"] = updated.get("city") or random.choice(COUNTRY_CITIES[country])
        updated.setdefault("signup_channel", random.choices(SIGNUP_CHANNELS, weights=SIGNUP_CHANNEL_WEIGHTS, k=1)[0])
        updated.setdefault("employment_status", random.choice(EMPLOYMENT_STATUSES))
        updated.setdefault("income_band", random.choice(INCOME_BANDS))
        updated.setdefault("risk_segment", random.choices(RISK_SEGMENTS, weights=[72, 23, 5], k=1)[0])
        updated.setdefault("customer_segment", random.choice(CUSTOMER_SEGMENTS))
        updated.setdefault("created_at", (batch_end).isoformat())
        updated["updated_at"] = (batch_end.replace(microsecond=0)).isoformat()
        updates.append(updated)

    return updates
