import argparse
import json
import os
import random
from datetime import datetime, timezone
from uuid import uuid4

import boto3
from dotenv import load_dotenv
from faker import Faker


fake = Faker()


KYC_STATUSES = ["not_started", "pending", "approved", "rejected"]
SIGNUP_CHANNELS = ["organic", "paid_search", "referral", "social", "email"]

ACCOUNT_TYPES = ["checking", "savings", "wallet"]
ACCOUNT_STATUSES = ["active", "suspended", "closed"]

TRANSACTION_TYPES = ["card_payment", "bank_transfer", "wallet_topup", "withdrawal"]
TRANSACTION_STATUSES = ["approved", "declined", "pending"]


def parse_args():
    parser = argparse.ArgumentParser(description="Generate FinSight batch data and upload JSONL files to R2.")

    parser.add_argument(
        "--customers",
        type=int,
        default=1000,
        help="Number of customers to generate.",
    )

    parser.add_argument(
        "--min-accounts-per-customer",
        type=int,
        default=1,
        help="Minimum accounts per customer.",
    )

    parser.add_argument(
        "--max-accounts-per-customer",
        type=int,
        default=2,
        help="Maximum accounts per customer.",
    )

    parser.add_argument(
        "--min-transactions-per-account",
        type=int,
        default=3,
        help="Minimum transactions per account.",
    )

    parser.add_argument(
        "--max-transactions-per-account",
        type=int,
        default=10,
        help="Maximum transactions per account.",
    )

    return parser.parse_args()


def get_batch_partition():
    now = datetime.now(timezone.utc)
    dt = now.strftime("%Y-%m-%d")
    batch_id = now.strftime("%Y%m%d_%H%M")
    return dt, batch_id


def generate_customers(count: int) -> list[dict]:
    customers = []
    seen_customer_ids = set()
    seen_emails = set()

    for i in range(count):
        customer_id = str(uuid4())

        while customer_id in seen_customer_ids:
            customer_id = str(uuid4())

        seen_customer_ids.add(customer_id)

        email = f"{fake.user_name()}.{i}.{customer_id[:8]}@example.com".lower()

        while email in seen_emails:
            email = f"{fake.user_name()}.{i}.{uuid4().hex[:8]}@example.com".lower()

        seen_emails.add(email)

        created_at = fake.date_time_between(
            start_date="-2y",
            end_date="now",
            tzinfo=timezone.utc,
        )

        customers.append(
            {
                "customer_id": customer_id,
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "email": email,
                "phone_number": fake.phone_number(),
                "country": fake.country_code(),
                "kyc_status": random.choice(KYC_STATUSES),
                "signup_channel": random.choice(SIGNUP_CHANNELS),
                "created_at": created_at.isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    return customers


def generate_accounts(
    customers: list[dict],
    min_accounts_per_customer: int,
    max_accounts_per_customer: int,
) -> list[dict]:
    accounts = []

    for customer in customers:
        account_count = random.randint(min_accounts_per_customer, max_accounts_per_customer)

        for _ in range(account_count):
            opened_at = fake.date_time_between(
                start_date="-2y",
                end_date="now",
                tzinfo=timezone.utc,
            )

            accounts.append(
                {
                    "account_id": str(uuid4()),
                    "customer_id": customer["customer_id"],
                    "account_type": random.choice(ACCOUNT_TYPES),
                    "account_status": random.choice(ACCOUNT_STATUSES),
                    "currency": "USD",
                    "opened_at": opened_at.isoformat(),
                    "created_at": opened_at.isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )

    return accounts


def generate_transactions(
    accounts: list[dict],
    min_transactions_per_account: int,
    max_transactions_per_account: int,
) -> list[dict]:
    transactions = []

    for account in accounts:
        transaction_count = random.randint(
            min_transactions_per_account,
            max_transactions_per_account,
        )

        for _ in range(transaction_count):
            amount = round(random.uniform(5, 500), 2)
            status = random.choice(TRANSACTION_STATUSES)

            transactions.append(
                {
                    "transaction_id": str(uuid4()),
                    "account_id": account["account_id"],
                    "customer_id": account["customer_id"],
                    "transaction_type": random.choice(TRANSACTION_TYPES),
                    "transaction_status": status,
                    "amount": amount,
                    "currency": account["currency"],
                    "transaction_at": fake.date_time_between(
                        start_date="-1y",
                        end_date="now",
                        tzinfo=timezone.utc,
                    ).isoformat(),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )

    return transactions


def records_to_jsonl_bytes(records: list[dict]) -> bytes:
    lines = [json.dumps(record, ensure_ascii=False, sort_keys=True) for record in records]
    return ("\n".join(lines) + "\n").encode("utf-8")


def get_s3_client():
    endpoint_url = os.getenv("S3_ENDPOINT_URL")
    access_key_id = os.getenv("S3_ACCESS_KEY_ID")
    secret_access_key = os.getenv("S3_SECRET_ACCESS_KEY")
    region = os.getenv("S3_REGION", "auto")

    missing = [
        name
        for name, value in {
            "S3_ENDPOINT_URL": endpoint_url,
            "S3_ACCESS_KEY_ID": access_key_id,
            "S3_SECRET_ACCESS_KEY": secret_access_key,
        }.items()
        if not value
    ]

    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region,
    )


def upload_jsonl(records: list[dict], dataset_name: str, dt: str, batch_id: str) -> str:
    bucket_name = os.getenv("S3_BUCKET_NAME")

    if not bucket_name:
        raise RuntimeError("Missing required environment variable: S3_BUCKET_NAME")

    object_key = f"{dataset_name}/dt={dt}/batch_id={batch_id}/{dataset_name}.jsonl"

    s3_client = get_s3_client()
    s3_client.put_object(
        Bucket=bucket_name,
        Key=object_key,
        Body=records_to_jsonl_bytes(records),
        ContentType="application/x-ndjson",
    )

    return object_key


def main():
    load_dotenv()

    args = parse_args()
    dt, batch_id = get_batch_partition()

    print("Generating FinSight batch")
    print("-------------------------")
    print(f"dt: {dt}")
    print(f"batch_id: {batch_id}")
    print(f"customers requested: {args.customers}")

    customers = generate_customers(count=args.customers)

    accounts = generate_accounts(
        customers=customers,
        min_accounts_per_customer=args.min_accounts_per_customer,
        max_accounts_per_customer=args.max_accounts_per_customer,
    )

    transactions = generate_transactions(
        accounts=accounts,
        min_transactions_per_account=args.min_transactions_per_account,
        max_transactions_per_account=args.max_transactions_per_account,
    )

    print("\nGenerated row counts:")
    print(f"customers: {len(customers)}")
    print(f"accounts: {len(accounts)}")
    print(f"transactions: {len(transactions)}")

    uploaded_customer_key = upload_jsonl(customers, "customers", dt, batch_id)
    uploaded_account_key = upload_jsonl(accounts, "accounts", dt, batch_id)
    uploaded_transaction_key = upload_jsonl(transactions, "transactions", dt, batch_id)

    bucket_name = os.getenv("S3_BUCKET_NAME")

    print("\nUploaded objects:")
    print(f"s3://{bucket_name}/{uploaded_customer_key}")
    print(f"s3://{bucket_name}/{uploaded_account_key}")
    print(f"s3://{bucket_name}/{uploaded_transaction_key}")

    print("\nBatch generation complete.")


if __name__ == "__main__":
    main()