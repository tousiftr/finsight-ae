import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from faker import Faker


fake = Faker()


def utc_now():
    return datetime.now(timezone.utc)


def make_batch_id(now):
    return now.strftime("%Y%m%d_%H%M")


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, default=str) + "\n")


def generate_customers(customer_count, batch_id, generated_at):
    customers = []

    for _ in range(customer_count):
        customer_id = f"cus_{uuid4().hex[:12]}"

        customers.append({
            "customer_id": customer_id,
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": fake.unique.email(),
            "phone_number": fake.phone_number(),
            "country": random.choice(["BD", "US", "GB", "SG", "AE"]),
            "customer_status": random.choice(["active", "active", "active", "pending"]),
            "created_at": generated_at.isoformat(),
            "batch_id": batch_id,
        })

    return customers


def generate_accounts(customers, batch_id, generated_at):
    accounts = []

    for customer in customers:
        account_count = random.choice([1, 1, 1, 2])

        for _ in range(account_count):
            accounts.append({
                "account_id": f"acct_{uuid4().hex[:12]}",
                "customer_id": customer["customer_id"],
                "account_type": random.choice(["checking", "savings", "wallet"]),
                "currency": random.choice(["BDT", "USD", "GBP", "EUR"]),
                "account_status": random.choice(["active", "active", "active", "pending"]),
                "opened_at": generated_at.isoformat(),
                "batch_id": batch_id,
            })

    return accounts


def generate_transactions(accounts, batch_id, generated_at, min_transactions, max_transactions):
    transactions = []

    transaction_count = random.randint(min_transactions, max_transactions)

    for _ in range(transaction_count):
        account = random.choice(accounts)

        amount = round(random.uniform(5, 1500), 2)
        status = random.choice([
            "completed",
            "completed",
            "completed",
            "completed",
            "failed",
            "declined",
        ])

        transactions.append({
            "transaction_id": f"txn_{uuid4().hex[:14]}",
            "account_id": account["account_id"],
            "customer_id": account["customer_id"],
            "transaction_type": random.choice(["card_payment", "bank_transfer", "wallet_topup", "withdrawal"]),
            "amount": amount,
            "currency": account["currency"],
            "status": status,
            "merchant_category": random.choice(["groceries", "travel", "utilities", "food", "ecommerce", "subscriptions"]),
            "transaction_timestamp": generated_at.isoformat(),
            "batch_id": batch_id,
        })

    return transactions


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--min-customers", type=int, default=2)
    parser.add_argument("--max-customers", type=int, default=25)
    parser.add_argument("--min-transactions", type=int, default=200)
    parser.add_argument("--max-transactions", type=int, default=350)
    parser.add_argument("--output-dir", default="data/raw")

    args = parser.parse_args()

    generated_at = utc_now()
    dt = generated_at.strftime("%Y-%m-%d")
    batch_id = make_batch_id(generated_at)

    customer_count = random.randint(args.min_customers, args.max_customers)

    customers = generate_customers(customer_count, batch_id, generated_at)
    accounts = generate_accounts(customers, batch_id, generated_at)
    transactions = generate_transactions(
        accounts=accounts,
        batch_id=batch_id,
        generated_at=generated_at,
        min_transactions=args.min_transactions,
        max_transactions=args.max_transactions,
    )

    output_base = Path(args.output_dir)

    customers_path = output_base / "customers" / f"dt={dt}" / f"batch_id={batch_id}" / "customers.jsonl"
    accounts_path = output_base / "accounts" / f"dt={dt}" / f"batch_id={batch_id}" / "accounts.jsonl"
    transactions_path = output_base / "transactions" / f"dt={dt}" / f"batch_id={batch_id}" / "transactions.jsonl"

    write_jsonl(customers_path, customers)
    write_jsonl(accounts_path, accounts)
    write_jsonl(transactions_path, transactions)

    print(f"Generated batch_id={batch_id}")
    print(f"Customers: {len(customers)} -> {customers_path}")
    print(f"Accounts: {len(accounts)} -> {accounts_path}")
    print(f"Transactions: {len(transactions)} -> {transactions_path}")


if __name__ == "__main__":
    main()