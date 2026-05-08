import random
from datetime import datetime, timedelta, timezone

from faker import Faker


fake = Faker()

MERCHANT_CATEGORIES = [
    "groceries",
    "food",
    "transport",
    "utilities",
    "ecommerce",
    "subscriptions",
    "travel",
    "healthcare",
    "entertainment",
]

CATEGORY_NAME_PATTERNS = {
    "groceries": ["{name} Market", "{name} Grocers", "Fresh {name}"],
    "food": ["{name} Cafe", "{name} Kitchen", "Bistro {name}"],
    "transport": ["{name} Rides", "{name} Transit", "Metro {name}"],
    "utilities": ["{name} Energy", "{name} Telecom", "Utility {name}"],
    "ecommerce": ["{name} Online", "{name} Shop", "Digital {name}"],
    "subscriptions": ["{name} Plus", "{name} Stream", "{name} Cloud"],
    "travel": ["{name} Travel", "{name} Airways", "Hotel {name}"],
    "healthcare": ["{name} Pharmacy", "{name} Clinic", "Health {name}"],
    "entertainment": ["{name} Cinema", "{name} Games", "Events {name}"],
}

COUNTRY_CITIES = {
    "BD": ["Dhaka", "Chittagong", "Sylhet", "Khulna"],
    "US": ["New York", "Austin", "Seattle", "San Francisco"],
    "GB": ["London", "Manchester", "Birmingham", "Leeds"],
    "SG": ["Singapore"],
    "AE": ["Dubai", "Abu Dhabi", "Sharjah"],
}

RISK_TIERS = ["low", "medium", "high"]
RISK_WEIGHTS = [70, 22, 8]


def current_hourly_batch_window(now: datetime | None = None) -> tuple[datetime, datetime, str, str]:
    """Return the prior UTC hourly batch window and its dt/batch_id partitions."""
    now_utc = now or datetime.now(timezone.utc)
    current_hour = now_utc.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    batch_start = current_hour - timedelta(hours=1)
    batch_end = current_hour - timedelta(seconds=1)
    dt = batch_start.strftime("%Y-%m-%d")
    batch_id = batch_start.strftime("%Y%m%d_%H00")
    return batch_start, batch_end, dt, batch_id


def batch_window_from_batch_id(batch_id: str) -> tuple[datetime, datetime]:
    batch_start = datetime.strptime(batch_id, "%Y%m%d_%H%M").replace(tzinfo=timezone.utc)
    batch_end = batch_start + timedelta(hours=1) - timedelta(seconds=1)
    return batch_start, batch_end


def random_time_between(start: datetime, end: datetime) -> datetime:
    if end <= start:
        return start
    total_seconds = int((end - start).total_seconds())
    return start + timedelta(seconds=random.randint(0, total_seconds))


def merchant_name_for_category(category: str) -> str:
    base_name = fake.company().split(",")[0]
    pattern = random.choice(CATEGORY_NAME_PATTERNS[category])
    return pattern.format(name=base_name)


def generate_merchants(
    merchant_count: int = 250,
    batch_id: str | None = None,
    batch_start: datetime | None = None,
    batch_end: datetime | None = None,
) -> list[dict]:
    if batch_start is None or batch_end is None:
        batch_start, batch_end, _, default_batch_id = current_hourly_batch_window()
        batch_id = batch_id or default_batch_id

    rows = []
    for index in range(1, merchant_count + 1):
        category = random.choice(MERCHANT_CATEGORIES)
        country = random.choices(["BD", "US", "GB", "SG", "AE"], weights=[45, 25, 12, 10, 8], k=1)[0]
        risk_tier = random.choices(RISK_TIERS, weights=RISK_WEIGHTS, k=1)[0]
        onboarded_at = random_time_between(batch_start - timedelta(days=730), batch_start)
        updated_at = random_time_between(batch_start, batch_end)

        rows.append(
            {
                "merchant_id": f"M{index:06d}",
                "merchant_name": merchant_name_for_category(category),
                "merchant_category": category,
                "merchant_country": country,
                "merchant_city": random.choice(COUNTRY_CITIES[country]),
                "risk_tier": risk_tier,
                "is_high_risk": risk_tier == "high",
                "onboarded_at": onboarded_at.isoformat(),
                "updated_at": updated_at.isoformat(),
                "batch_id": batch_id,
            }
        )

    return rows
