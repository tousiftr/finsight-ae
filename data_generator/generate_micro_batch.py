import argparse
import json
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path

from faker import Faker
fake = Faker()
BDT = timezone(timedelta(hours=6))

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def make_batch_id(now: datetime) -> str:
    return now.strftime("%Y%m%d_%H%M")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, default=str) + "\n")


def choose_customer_count() -> int:
    return random.choices([0, 1, 2], weights=[25, 55, 20], k=1)[0]


def choose_transaction_count(now: datetime) -> int:
    hour = now.astimezone(BDT).hour
    if 1 <= hour < 7:
        return random.randint(0, 4)
    if 7 <= hour < 11:
        return random.randint(3, 10)
    if 11 <= hour < 22:
        return random.randint(8, 25)
    return random.randint(2, 8)


def parse_iso_date(date_text: str) -> datetime:
    return datetime.fromisoformat(f"{date_text}T00:00:00+00:00")


def random_time_between(start: datetime, end: datetime) -> datetime:
    if end <= start:
        return start
    total_seconds = int((end - start).total_seconds())
    return start + timedelta(seconds=random.randint(0, total_seconds))


def generate_customers(customer_count: int, batch_id: str, generated_at: datetime) -> list[dict]:
    signup_channels = ["organic", "paid_search", "referral", "social", "partner"]
    signup_weights = [40, 25, 15, 15, 5]
    rows = []
    for i in range(1, customer_count + 1):
        rows.append({
            "customer_id": f"C{i:05d}",
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": fake.unique.email(),
            "phone_number": fake.phone_number(),
            "country": random.choices(["BD", "US", "GB", "SG", "AE"], weights=[55, 20, 10, 10, 5], k=1)[0],
            "customer_status": random.choices(["active", "pending", "blocked"], weights=[88, 10, 2], k=1)[0],
            "signup_channel": random.choices(signup_channels, weights=signup_weights, k=1)[0],
            "kyc_status": None,
            "created_at": generated_at.isoformat(),
            "batch_id": batch_id,
        })
    return rows


def generate_customers_with_history(customer_count: int, batch_id: str, history_start: datetime, batch_end: datetime) -> list[dict]:
    rows = generate_customers(customer_count, batch_id, batch_end)
    for row in rows:
        row["created_at"] = random_time_between(history_start, batch_end).isoformat()
    return rows


def generate_accounts(customers: list[dict], batch_id: str, generated_at: datetime) -> list[dict]:
    rows = []
    next_account = 900001
    for customer in customers:
        account_count = random.choices([1, 2], weights=[85, 15], k=1)[0]
        for _ in range(account_count):
            account_type = random.choice(["savings", "plus", "investment", "super", "salary"])
            investment_sub_type = random.choice(["crypto", "etf", "cfd", "fx"]) if account_type == "investment" else None
            rows.append({
                "account_id": f"A{next_account:06d}",
                "customer_id": customer["customer_id"],
                "account_type": account_type,
                "investment_sub_type": investment_sub_type,
                "currency": random.choices(["BDT", "USD", "GBP", "EUR"], weights=[65, 25, 5, 5], k=1)[0],
                "account_status": random.choices(["active", "pending", "closed"], weights=[90, 8, 2], k=1)[0],
                "opened_at": generated_at.isoformat(),
                "batch_id": batch_id,
            })
            next_account += 1
    return rows


def generate_accounts_with_history(customers: list[dict], batch_id: str, batch_end: datetime) -> list[dict]:
    rows = []
    next_account = 900001
    for customer in customers:
        created_at = datetime.fromisoformat(customer["created_at"])
        account_count = random.choices([1, 2, 3, 4], weights=[45, 35, 15, 5], k=1)[0]
        for _ in range(account_count):
            account_type = random.choice(["savings", "plus", "investment", "super", "salary"])
            investment_sub_type = random.choice(["crypto", "etf", "cfd", "fx"]) if account_type == "investment" else None
            opened_at = random_time_between(created_at, batch_end)
            rows.append({
                "account_id": f"A{next_account:06d}",
                "customer_id": customer["customer_id"],
                "account_type": account_type,
                "investment_sub_type": investment_sub_type,
                "currency": random.choices(["BDT", "USD", "GBP", "EUR"], weights=[65, 25, 5, 5], k=1)[0],
                "account_status": random.choices(["active", "pending", "closed"], weights=[90, 8, 2], k=1)[0],
                "opened_at": opened_at.isoformat(),
                "batch_id": batch_id,
            })
            next_account += 1
    return rows


def generate_transactions(accounts: list[dict], transaction_count: int, batch_id: str, generated_at: datetime) -> list[dict]:
    rows = []
    for i in range(1, transaction_count + 1):
        if not accounts:
            break
        account = random.choice(accounts)
        rows.append({
            "transaction_id": f"txn_{i:06d}",
            "account_id": account["account_id"],
            "customer_id": account["customer_id"],
            "transaction_type": random.choices(["card_payment", "bank_transfer", "withdrawal", "deposit"], weights=[50, 20, 15, 15], k=1)[0],
            "amount": round(random.uniform(3, 900), 2),
            "currency": account.get("currency") or "USD",
            "status": random.choices(["completed", "pending", "failed", "declined"], weights=[86, 7, 4, 3], k=1)[0],
            "merchant_category": random.choice(["groceries", "food", "transport", "utilities", "ecommerce", "subscriptions", "travel", "cash_withdrawal"]),
            "transaction_timestamp": generated_at.isoformat(),
            "batch_id": batch_id,
        })
    return rows


def generate_transactions_with_history(accounts: list[dict], transaction_count: int, batch_id: str, batch_end: datetime) -> list[dict]:
    rows = []
    if not accounts:
        return rows
    for i in range(1, transaction_count + 1):
        account = random.choice(accounts)
        opened_at = datetime.fromisoformat(account["opened_at"])
        transaction_time = random_time_between(opened_at, batch_end)
        rows.append({
            "transaction_id": f"txn_{i:06d}",
            "account_id": account["account_id"],
            "customer_id": account["customer_id"],
            "transaction_type": random.choices(["card_payment", "bank_transfer", "withdrawal", "deposit"], weights=[50, 20, 15, 15], k=1)[0],
            "amount": round(random.uniform(3, 900), 2),
            "currency": account.get("currency") or "USD",
            "status": random.choices(["completed", "pending", "failed", "declined"], weights=[86, 7, 4, 3], k=1)[0],
            "merchant_category": random.choice(["groceries", "food", "transport", "utilities", "ecommerce", "subscriptions", "travel", "cash_withdrawal"]),
            "transaction_timestamp": transaction_time.isoformat(),
            "batch_id": batch_id,
        })
    return rows


def generate_product_events_with_history(customers: list[dict], accounts: list[dict], dt: str, batch_id: str, event_count: int, batch_end: datetime) -> list[dict]:
    account_by_customer: dict[str, list[dict]] = {}
    customer_by_id = {c["customer_id"]: c for c in customers}
    for account in accounts:
        account_by_customer.setdefault(account["customer_id"], []).append(account)

    names = [
        "app_opened", "signup_started", "signup_completed", "kyc_started", "kyc_submitted", "kyc_status_viewed",
        "account_created", "deposit_started", "deposit_completed", "transfer_started", "transfer_completed",
        "investment_tab_viewed", "crypto_buy_clicked", "card_screen_viewed",
    ]
    rows = []
    for i in range(1, event_count + 1):
        customer = random.choice(customers)
        customer_created = datetime.fromisoformat(customer_by_id[customer["customer_id"]]["created_at"])
        customer_accounts = account_by_customer.get(customer["customer_id"], [])
        account = random.choice(customer_accounts) if customer_accounts and random.random() < 0.6 else None
        event_time = random_time_between(customer_created, batch_end)
        rows.append({
            "event_id": f"pe_{i:06d}",
            "customer_id": customer["customer_id"],
            "account_id": account["account_id"] if account else None,
            "session_id": f"sess_{customer['customer_id']}_{random.randint(1, 99):02d}",
            "event_name": random.choice(names),
            "event_timestamp": event_time.isoformat(),
            "platform": random.choice(["ios", "android", "web"]),
            "device_type": random.choice(["mobile", "tablet", "desktop"]),
            "app_version": random.choice(["2.3.1", "2.3.2", "2.4.0"]),
            "screen_name": random.choice(["home", "signup", "kyc", "accounts", "payments", "cards", "investments"]),
            "feature_name": random.choice(["onboarding", "transfer", "deposit", "crypto", "cards", "profile"]),
            "event_properties": {"network": random.choice(["wifi", "4g", "5g"]), "experiment_bucket": random.choice(["A", "B"])},
            "dt": dt,
            "batch_id": batch_id,
        })
    return rows


def generate_kyc_with_history(customers: list[dict], dt: str, batch_id: str, batch_end: datetime) -> list[dict]:
    rows = []
    statuses = ["approved", "manual_review", "pending", "rejected", "expired"]
    weights = [75, 10, 8, 5, 2]
    reasons = ["document_mismatch", "blurry_document", "sanctions_hit", "insufficient_information"]
    for i, customer in enumerate(customers, start=1):
        created_at = datetime.fromisoformat(customer["created_at"])
        status = random.choices(statuses, weights=weights, k=1)[0]
        submitted_at = random_time_between(created_at, batch_end)
        reviewed_at = None
        rejection_reason = None
        if status in {"approved", "rejected", "manual_review"}:
            reviewed_at = random_time_between(submitted_at, batch_end)
        if status == "rejected":
            rejection_reason = random.choice(reasons)
        rows.append({
            "kyc_application_id": f"kyc_{i:06d}",
            "customer_id": customer["customer_id"],
            "submitted_at": submitted_at.isoformat(),
            "reviewed_at": reviewed_at.isoformat() if reviewed_at else None,
            "kyc_status": status,
            "kyc_level": random.choice(["basic", "standard", "enhanced"]),
            "document_type": random.choice(["passport", "national_id", "driving_license", "residence_permit"]),
            "country": random.choice(["BD", "US", "GB", "SG", "AE"]),
            "risk_score": round(random.uniform(0, 100), 2),
            "rejection_reason": rejection_reason,
            "review_channel": random.choice(["automated", "manual", "hybrid"]),
            "reviewer_type": random.choice(["system", "internal_reviewer", "vendor_reviewer"]),
            "dt": dt,
            "batch_id": batch_id,
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a small realistic FinSight micro-batch.")
    parser.add_argument("--dt", type=str, default=None)
    parser.add_argument("--batch-id", type=str, default=None)
    parser.add_argument("--customer-count", type=int, default=100)
    parser.add_argument("--transaction-count", type=int, default=1200)
    parser.add_argument("--history-start-date", type=str, default=None)
    parser.add_argument("--product-event-count", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    now = utc_now()
    batch_dt = args.dt or now.strftime("%Y-%m-%d")
    batch_id = args.batch_id or make_batch_id(now)
    if args.seed is not None:
        random.seed(args.seed)
        Faker.seed(args.seed)
    history_start_date = args.history_start_date or batch_dt
    history_start = parse_iso_date(history_start_date)
    batch_end = datetime.fromisoformat(f"{batch_dt}T23:59:59+00:00")
    product_event_count = args.product_event_count if args.product_event_count is not None else args.customer_count * 10

    customers = generate_customers_with_history(args.customer_count, batch_id, history_start, batch_end)
    accounts = generate_accounts_with_history(customers, batch_id, batch_end)
    transactions = generate_transactions_with_history(accounts, args.transaction_count, batch_id, batch_end)
    product_events = generate_product_events_with_history(customers, accounts, batch_dt, batch_id, product_event_count, batch_end)
    kyc_applications = generate_kyc_with_history(customers, batch_dt, batch_id, batch_end)
    latest_kyc_by_customer = {}
    for app in sorted(kyc_applications, key=lambda row: row["submitted_at"]):
        latest_kyc_by_customer[app["customer_id"]] = app["kyc_status"]
    for customer in customers:
        customer["kyc_status"] = latest_kyc_by_customer.get(customer["customer_id"])

    base = Path(__file__).resolve().parents[1] / "data" / "raw"
    write_jsonl(base / "customers" / f"dt={batch_dt}" / f"batch_id={batch_id}" / "customers.jsonl", customers)
    write_jsonl(base / "accounts" / f"dt={batch_dt}" / f"batch_id={batch_id}" / "accounts.jsonl", accounts)
    write_jsonl(base / "transactions" / f"dt={batch_dt}" / f"batch_id={batch_id}" / "transactions.jsonl", transactions)
    write_jsonl(base / "product_events" / f"dt={batch_dt}" / f"batch_id={batch_id}" / "product_events.jsonl", product_events)
    write_jsonl(base / "kyc_applications" / f"dt={batch_dt}" / f"batch_id={batch_id}" / "kyc_applications.jsonl", kyc_applications)

    print(f"BATCH_DT={batch_dt}")
    print(f"BATCH_ID={batch_id}")
    print(f"Generated customers rows: {len(customers)}")
    print(f"Generated accounts rows: {len(accounts)}")
    print(f"Generated transactions rows: {len(transactions)}")
    print(f"Generated product_events rows: {len(product_events)}")
    print(f"Generated kyc_applications rows: {len(kyc_applications)}")


if __name__ == "__main__":
    main()
