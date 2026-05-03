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

_ACCOUNT_OPTIONAL_EVENTS = {
    "signup_started",
    "signup_completed",
    "kyc_started",
    "kyc_submitted",
    "kyc_status_viewed",
    "app_opened",
}


def generate_product_events(customers: list[dict], accounts: list[dict], dt: str, batch_id: str) -> list[dict]:
    accounts_by_customer: dict[str, list[dict]] = {}
    for account in accounts:
        accounts_by_customer.setdefault(account["customer_id"], []).append(account)

    rows: list[dict] = []
    event_seq = 1
    day_start = datetime.fromisoformat(f"{dt}T00:00:00+00:00")

    for customer in customers:
        customer_accounts = accounts_by_customer.get(customer["customer_id"], [])
        for _ in range(random.randint(4, 10)):
            event_name = random.choice(PRODUCT_EVENT_NAMES)
            use_account = bool(customer_accounts) and (
                event_name not in _ACCOUNT_OPTIONAL_EVENTS or random.random() < 0.25
            )
            account = random.choice(customer_accounts) if use_account else None
            event_time = day_start + timedelta(seconds=random.randint(0, 86399))

            rows.append({
                "event_id": f"pe_{event_seq:06d}",
                "customer_id": customer["customer_id"],
                "account_id": account["account_id"] if account else None,
                "session_id": f"sess_{customer['customer_id']}_{random.randint(1, 99):02d}",
                "event_name": event_name,
                "event_timestamp": event_time.astimezone(timezone.utc).isoformat(),
                "platform": random.choice(["ios", "android", "web"]),
                "device_type": random.choice(["mobile", "tablet", "desktop"]),
                "app_version": random.choice(["2.3.1", "2.3.2", "2.4.0"]),
                "screen_name": random.choice(["home", "signup", "kyc", "accounts", "payments", "cards", "investments"]),
                "feature_name": random.choice(["onboarding", "transfer", "deposit", "crypto", "cards", "profile"]),
                "event_properties": {
                    "network": random.choice(["wifi", "4g", "5g"]),
                    "experiment_bucket": random.choice(["A", "B"]),
                },
                "dt": dt,
                "batch_id": batch_id,
            })
            event_seq += 1

    return rows
