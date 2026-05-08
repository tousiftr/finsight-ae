import argparse
import json
from pathlib import Path

from generate_accounts import generate_accounts
from generate_customers import generate_customers
from generate_merchants import current_hourly_batch_window, generate_merchants
from generate_transactions import generate_transactions


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

    batch_start, batch_end, dt, batch_id = current_hourly_batch_window()

    customers = generate_customers(args.customer_count)
    accounts = generate_accounts(customers)
    merchants = generate_merchants(args.merchant_count, batch_id, batch_start, batch_end)
    transactions = generate_transactions(accounts, merchants=merchants, batch_start=batch_start, batch_end=batch_end, batch_id=batch_id)

    base = Path(args.output_dir)
    write_jsonl(base / "customers" / f"dt={dt}" / f"batch_id={batch_id}" / "customers.jsonl", customers)
    write_jsonl(base / "accounts" / f"dt={dt}" / f"batch_id={batch_id}" / "accounts.jsonl", accounts)
    write_jsonl(base / "merchants" / f"dt={dt}" / f"batch_id={batch_id}" / "merchants.jsonl", merchants)
    write_jsonl(base / "transactions" / f"dt={dt}" / f"batch_id={batch_id}" / "transactions.jsonl", transactions)

    print(f"Generated batch_id={batch_id}")
    print(f"Customers={len(customers)} Accounts={len(accounts)} Merchants={len(merchants)} Transactions={len(transactions)}")


if __name__ == "__main__":
    main()
