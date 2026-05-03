import argparse
import json
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path

from faker import Faker
from generate_kyc import generate_kyc_applications
from generate_product_events import generate_product_events


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


def generate_customers(customer_count: int, batch_id: str, generated_at: datetime) -> list[dict]:
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
            "created_at": generated_at.isoformat(),
            "batch_id": batch_id,
        })
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a small realistic FinSight micro-batch.")
    parser.add_argument("--dt", type=str, default=None)
    parser.add_argument("--batch-id", type=str, default=None)
    args = parser.parse_args()

    now = utc_now()
    batch_dt = args.dt or now.strftime("%Y-%m-%d")
    batch_id = args.batch_id or make_batch_id(now)

    customers = generate_customers(choose_customer_count(), batch_id, now)
    accounts = generate_accounts(customers, batch_id, now)
    transactions = generate_transactions(accounts, choose_transaction_count(now), batch_id, now)
    product_events = generate_product_events(customers, accounts, batch_dt, batch_id)
    kyc_applications = generate_kyc_applications(customers, batch_dt, batch_id)

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
