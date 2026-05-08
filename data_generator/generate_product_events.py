import random
from datetime import datetime, timedelta, timezone

PRODUCT_EVENT_NAMES = [
    "app_opened",
    "signup_started",
    "signup_completed",
    "kyc_started",
    "kyc_submitted",
    "kyc_status_viewed",
    "account_created",
    "deposit_started",
    "deposit_completed",
    "transfer_started",
    "transfer_completed",
    "investment_tab_viewed",
    "crypto_buy_clicked",
    "card_screen_viewed",
]
EVENT_WEIGHTS = [18, 5, 4, 6, 5, 7, 4, 7, 6, 8, 7, 8, 4, 11]
_ACCOUNT_OPTIONAL_EVENTS = {
    "signup_started",
    "signup_completed",
    "kyc_started",
    "kyc_submitted",
    "kyc_status_viewed",
    "app_opened",
}
SCREEN_BY_EVENT = {
    "app_opened": "home",
    "signup_started": "signup",
    "signup_completed": "signup",
    "kyc_started": "kyc",
    "kyc_submitted": "kyc",
    "kyc_status_viewed": "kyc",
    "account_created": "accounts",
    "deposit_started": "payments",
    "deposit_completed": "payments",
    "transfer_started": "payments",
    "transfer_completed": "payments",
    "investment_tab_viewed": "investments",
    "crypto_buy_clicked": "investments",
    "card_screen_viewed": "cards",
}
FEATURE_BY_EVENT = {
    "app_opened": "app_usage",
    "signup_started": "onboarding",
    "signup_completed": "onboarding",
    "kyc_started": "kyc",
    "kyc_submitted": "kyc",
    "kyc_status_viewed": "kyc",
    "account_created": "onboarding",
    "deposit_started": "deposit",
    "deposit_completed": "deposit",
    "transfer_started": "transfer",
    "transfer_completed": "transfer",
    "investment_tab_viewed": "investment",
    "crypto_buy_clicked": "investment",
    "card_screen_viewed": "cards",
}


def random_time_between(start: datetime, end: datetime) -> datetime:
    if end <= start:
        return start
    total_seconds = int((end - start).total_seconds())
    return start + timedelta(seconds=random.randint(0, total_seconds))


def generate_product_events(
    customers: list[dict],
    accounts: list[dict],
    dt: str,
    batch_id: str,
    generator_run_id: str,
    event_count: int | None = None,
    batch_start: datetime | None = None,
    batch_end: datetime | None = None,
) -> list[dict]:
    if not customers:
        return []

    accounts_by_customer: dict[str, list[dict]] = {}
    for account in accounts:
        accounts_by_customer.setdefault(account["customer_id"], []).append(account)

    if batch_start is None:
        batch_start = datetime.fromisoformat(f"{dt}T00:00:00+00:00")
    if batch_end is None:
        batch_end = batch_start + timedelta(minutes=20) - timedelta(seconds=1)

    if event_count is None:
        event_count = sum(random.randint(4, 10) for _ in customers)

    rows: list[dict] = []
    session_customers = random.choices(customers, k=max(1, min(len(customers), event_count // 4)))
    sessions = [
        {
            "customer": customer,
            "session_id": f"sess_{batch_id}_{generator_run_id}_{customer['customer_id']}_{idx:04d}",
            "platform": random.choice(["ios", "android", "web"]),
            "device_type": random.choice(["mobile", "tablet", "desktop"]),
            "app_version": random.choice(["2.3.1", "2.3.2", "2.4.0", "2.4.1"]),
        }
        for idx, customer in enumerate(session_customers, start=1)
    ]

    for event_seq in range(1, event_count + 1):
        session = random.choice(sessions)
        customer = session["customer"]
        customer_accounts = accounts_by_customer.get(customer["customer_id"], [])
        event_name = random.choices(PRODUCT_EVENT_NAMES, weights=EVENT_WEIGHTS, k=1)[0]
        use_account = bool(customer_accounts) and (
            event_name not in _ACCOUNT_OPTIONAL_EVENTS or random.random() < 0.30
        )
        account = random.choice(customer_accounts) if use_account else None
        event_time = random_time_between(batch_start, batch_end)

        rows.append(
            {
                "event_id": f"pe_{batch_id}_{generator_run_id}_{event_seq:06d}",
                "customer_id": customer["customer_id"],
                "account_id": account["account_id"] if account else None,
                "session_id": session["session_id"],
                "event_name": event_name,
                "event_timestamp": event_time.astimezone(timezone.utc).isoformat(),
                "platform": session["platform"],
                "device_type": session["device_type"],
                "app_version": session["app_version"],
                "screen_name": SCREEN_BY_EVENT[event_name],
                "feature_name": FEATURE_BY_EVENT[event_name],
                "event_properties": {
                    "network": random.choice(["wifi", "4g", "5g"]),
                    "experiment_bucket": random.choice(["A", "B", "control"]),
                    "is_new_customer": customer.get("is_new_customer", False),
                    "funnel_step": event_name.split("_")[-1],
                },
                "dt": dt,
                "batch_id": batch_id,
            }
        )

    return rows
