import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from generate_accounts import generate_accounts
from generate_customers import generate_customers
from generate_kyc import generate_kyc_applications
from generate_merchants import generate_merchants
from generate_product_events import generate_product_events
from generate_transactions import generate_transactions


def current_quarter_hour_batch_window(now: datetime | None = None) -> tuple[datetime, datetime, str, str]:
    """Return the prior UTC 15-minute batch window and partition values."""
    now_utc = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    current_quarter_minute = (now_utc.minute // 15) * 15
    current_quarter = now_utc.replace(minute=current_quarter_minute, second=0, microsecond=0)
    batch_start = current_quarter - timedelta(minutes=15)
    batch_end = current_quarter - timedelta(seconds=1)
    dt = batch_start.strftime("%Y-%m-%d")
    batch_id = batch_start.strftime("%Y%m%d_%H%M")
    return batch_start, batch_end, dt, batch_id


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate FinSight raw customer/account/transaction data.")
    parser.add_argument("--customer-count", type=int, default=100)
    parser.add_argument("--merchant-count", type=int, default=250)
    parser.add_argument("--output-dir", default="data/raw")
    args = parser.parse_args()

    batch_start, batch_end, dt, batch_id = current_quarter_hour_batch_window()

    customers = generate_customers(args.customer_count)
    accounts = generate_accounts(customers)
    merchants = generate_merchants(args.merchant_count, batch_id, batch_start, batch_end)
    transactions = generate_transactions(accounts, merchants=merchants, batch_start=batch_start, batch_end=batch_end, batch_id=batch_id)
    product_events = generate_product_events(customers, accounts, dt, batch_id)
    kyc_applications = generate_kyc_applications(customers, dt, batch_id)

    base = Path(args.output_dir)
    write_jsonl(base / "customers" / f"dt={dt}" / f"batch_id={batch_id}" / "customers.jsonl", customers)
    write_jsonl(base / "accounts" / f"dt={dt}" / f"batch_id={batch_id}" / "accounts.jsonl", accounts)
    write_jsonl(base / "merchants" / f"dt={dt}" / f"batch_id={batch_id}" / "merchants.jsonl", merchants)
    write_jsonl(base / "transactions" / f"dt={dt}" / f"batch_id={batch_id}" / "transactions.jsonl", transactions)
    write_jsonl(base / "product_events" / f"dt={dt}" / f"batch_id={batch_id}" / "product_events.jsonl", product_events)
    write_jsonl(base / "kyc_applications" / f"dt={dt}" / f"batch_id={batch_id}" / "kyc_applications.jsonl", kyc_applications)

    print(f"Generated batch_id={batch_id}")
    print(
        f"Customers={len(customers)} Accounts={len(accounts)} Merchants={len(merchants)} "
        f"Transactions={len(transactions)} ProductEvents={len(product_events)} "
        f"KycApplications={len(kyc_applications)}"
    )


if __name__ == "__main__":
    main()
