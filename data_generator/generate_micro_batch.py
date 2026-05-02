import argparse
import json
import os
import random
import ssl
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import unquote, urlparse
from uuid import uuid4

import pg8000.dbapi
from dotenv import load_dotenv
from faker import Faker


fake = Faker()


BDT = timezone(timedelta(hours=6))


def load_project_env() -> None:
    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env", override=True)


def get_neon_connection():
    database_url = os.getenv("DATABASE_URL") or os.getenv("NEON_DATABASE_URL")

    if not database_url:
        raise RuntimeError("Missing DATABASE_URL or NEON_DATABASE_URL in .env")

    parsed = urlparse(database_url)

    return pg8000.dbapi.connect(
        user=unquote(parsed.username or ""),
        password=unquote(parsed.password or ""),
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=unquote(parsed.path.lstrip("/")),
        ssl_context=ssl.create_default_context(),
    )


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
    """
    Realistic small fintech behavior:
    - some 10-minute windows have no signup
    - most active windows have 1 signup
    - some have 2 signups
    """
    return random.choices(
        population=[0, 1, 2],
        weights=[25, 55, 20],
        k=1,
    )[0]


def choose_transaction_count(now: datetime) -> int:
    """
    Transaction volume varies by Bangladesh local time.
    More activity during daytime/evening, less overnight.
    """
    bdt_now = now.astimezone(BDT)
    hour = bdt_now.hour

    if 1 <= hour < 7:
        return random.randint(0, 4)

    if 7 <= hour < 11:
        return random.randint(3, 10)

    if 11 <= hour < 22:
        return random.randint(8, 25)

    return random.randint(2, 8)


def fetch_existing_accounts(conn, limit: int = 100) -> list[dict]:
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"""
            select
                payload ->> 'account_id' as account_id,
                payload ->> 'customer_id' as customer_id,
                coalesce(payload ->> 'currency', 'USD') as currency
            from raw.raw_accounts
            where payload ->> 'account_id' is not null
              and payload ->> 'customer_id' is not null
            order by random()
            limit {int(limit)};
            """
        )

        rows = cursor.fetchall()

        return [
            {
                "account_id": row[0],
                "customer_id": row[1],
                "currency": row[2] or "USD",
            }
            for row in rows
        ]

    finally:
        cursor.close()


def generate_customers(customer_count: int, batch_id: str, generated_at: datetime) -> list[dict]:
    customers = []

    for _ in range(customer_count):
        customer_id = f"cus_{uuid4().hex[:12]}"

        customers.append(
            {
                "customer_id": customer_id,
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "email": fake.unique.email(),
                "phone_number": fake.phone_number(),
                "country": random.choices(
                    ["BD", "US", "GB", "SG", "AE"],
                    weights=[55, 20, 10, 10, 5],
                    k=1,
                )[0],
                "customer_status": random.choices(
                    ["active", "pending", "blocked"],
                    weights=[88, 10, 2],
                    k=1,
                )[0],
                "created_at": generated_at.isoformat(),
                "batch_id": batch_id,
            }
        )

    return customers


def generate_accounts(customers: list[dict], batch_id: str, generated_at: datetime) -> list[dict]:
    accounts = []

    for customer in customers:
        account_count = random.choices(
            [1, 2],
            weights=[85, 15],
            k=1,
        )[0]

        for _ in range(account_count):
            accounts.append(
                {
                    "account_id": f"acct_{uuid4().hex[:12]}",
                    "customer_id": customer["customer_id"],
                    "account_type": random.choices(
                        ["wallet", "checking", "savings"],
                        weights=[60, 30, 10],
                        k=1,
                    )[0],
                    "currency": random.choices(
                        ["BDT", "USD", "GBP", "EUR"],
                        weights=[65, 25, 5, 5],
                        k=1,
                    )[0],
                    "account_status": random.choices(
                        ["active", "pending", "closed"],
                        weights=[90, 8, 2],
                        k=1,
                    )[0],
                    "opened_at": generated_at.isoformat(),
                    "batch_id": batch_id,
                }
            )

    return accounts


def generate_transactions(
    accounts: list[dict],
    transaction_count: int,
    batch_id: str,
    generated_at: datetime,
) -> list[dict]:
    transactions = []

    if not accounts:
        return transactions

    for _ in range(transaction_count):
        account = random.choice(accounts)

        transaction_type = random.choices(
            ["card_payment", "bank_transfer", "wallet_topup", "withdrawal"],
            weights=[55, 20, 15, 10],
            k=1,
        )[0]

        status = random.choices(
            ["completed", "failed", "declined"],
            weights=[91, 5, 4],
            k=1,
        )[0]

        amount = round(random.uniform(3, 900), 2)

        transactions.append(
            {
                "transaction_id": f"txn_{uuid4().hex[:14]}",
                "account_id": account["account_id"],
                "customer_id": account["customer_id"],
                "transaction_type": transaction_type,
                "amount": amount,
                "currency": account.get("currency") or "USD",
                "status": status,
                "merchant_category": random.choices(
                    [
                        "groceries",
                        "food",
                        "transport",
                        "utilities",
                        "ecommerce",
                        "subscriptions",
                        "travel",
                        "cash_withdrawal",
                    ],
                    weights=[20, 18, 15, 12, 15, 8, 5, 7],
                    k=1,
                )[0],
                "transaction_timestamp": generated_at.isoformat(),
                "batch_id": batch_id,
            }
        )

    return transactions


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a small realistic FinSight micro-batch."
    )

    parser.add_argument(
        "--output-dir",
        default="data/raw",
        help="Base local output directory.",
    )

    parser.add_argument(
        "--existing-account-sample-size",
        type=int,
        default=100,
    )

    args = parser.parse_args()

    load_project_env()

    generated_at = utc_now()
    dt = generated_at.strftime("%Y-%m-%d")
    batch_id = make_batch_id(generated_at)

    conn = get_neon_connection()

    try:
        existing_accounts = fetch_existing_accounts(
            conn=conn,
            limit=args.existing_account_sample_size,
        )
    finally:
        conn.close()

    customer_count = choose_customer_count()
    transaction_count = choose_transaction_count(generated_at)

    customers = generate_customers(
        customer_count=customer_count,
        batch_id=batch_id,
        generated_at=generated_at,
    )

    new_accounts = generate_accounts(
        customers=customers,
        batch_id=batch_id,
        generated_at=generated_at,
    )

    transaction_accounts = existing_accounts + new_accounts

    transactions = generate_transactions(
        accounts=transaction_accounts,
        transaction_count=transaction_count,
        batch_id=batch_id,
        generated_at=generated_at,
    )

    output_base = Path(args.output_dir)

    customers_path = output_base / "customers" / f"dt={dt}" / f"batch_id={batch_id}" / "customers.jsonl"
    accounts_path = output_base / "accounts" / f"dt={dt}" / f"batch_id={batch_id}" / "accounts.jsonl"
    transactions_path = output_base / "transactions" / f"dt={dt}" / f"batch_id={batch_id}" / "transactions.jsonl"

    write_jsonl(customers_path, customers)
    write_jsonl(accounts_path, new_accounts)
    write_jsonl(transactions_path, transactions)

    manifest = {
        "dt": dt,
        "batch_id": batch_id,
        "customers_key": f"customers/dt={dt}/batch_id={batch_id}/customers.jsonl",
        "accounts_key": f"accounts/dt={dt}/batch_id={batch_id}/accounts.jsonl",
        "transactions_key": f"transactions/dt={dt}/batch_id={batch_id}/transactions.jsonl",
        "customers_path": str(customers_path),
        "accounts_path": str(accounts_path),
        "transactions_path": str(transactions_path),
    }

    manifest_path = output_base / "latest_micro_batch.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"Generated micro-batch batch_id={batch_id}")
    print(f"Customers: {len(customers)} -> {customers_path}")
    print(f"Accounts: {len(new_accounts)} -> {accounts_path}")
    print(f"Transactions: {len(transactions)} -> {transactions_path}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()