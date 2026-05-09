import argparse
import json
import os
import random
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.append(str(SCRIPTS_DIR))

from generate_accounts import generate_accounts
from generate_customers import generate_customer_updates, generate_customers
from generate_kyc import generate_kyc_applications
from generate_merchants import generate_merchants
from generate_product_events import generate_product_events
from generate_transactions import generate_transaction_status_updates, generate_transactions
from generator_state import GeneratorState, load_generator_state


def current_quarter_hour_batch_window(now: datetime | None = None) -> tuple[datetime, datetime, str, str]:
    """Return the prior UTC 20-minute batch window and partition values."""
    now_utc = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    current_slot_minute = (now_utc.minute // 20) * 20
    current_slot = now_utc.replace(minute=current_slot_minute, second=0, microsecond=0)
    batch_start = current_slot - timedelta(minutes=20)
    batch_end = current_slot - timedelta(seconds=1)
    dt = batch_start.strftime("%Y-%m-%d")
    batch_id = batch_start.strftime("%Y%m%d_%H%M")
    return batch_start, batch_end, dt, batch_id


def _safe_id_part(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_")


def generator_run_id() -> str:
    run_id = os.getenv("GITHUB_RUN_ID")
    run_attempt = os.getenv("GITHUB_RUN_ATTEMPT", "1")
    if run_id:
        return f"gh{_safe_id_part(run_id)}_{_safe_id_part(run_attempt)}"
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")


def assert_unique(rows: list[dict], key: str, label: str) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for row in rows:
        value = row.get(key)
        if value in seen:
            duplicates.add(value)
        else:
            seen.add(value)
    if duplicates:
        raise ValueError(f"Duplicate {label} IDs generated: {sorted(duplicates)[:10]}")


def validate_transaction_references(transactions: list[dict], reusable_accounts: list[dict]) -> None:
    """Ensure generated transactions only reference known account/customer pairs."""
    valid_accounts_by_id = {
        account["account_id"]: account
        for account in reusable_accounts
        if account.get("account_id") and account.get("customer_id")
    }

    for transaction in transactions:
        transaction_id = transaction.get("transaction_id")
        account_id = transaction.get("account_id")
        customer_id = transaction.get("customer_id")

        if account_id is None:
            raise ValueError(f"Transaction has null account_id; transaction_id={transaction_id}")
        if customer_id is None:
            raise ValueError(f"Transaction has null customer_id; transaction_id={transaction_id}")

        if account_id not in valid_accounts_by_id:
            raise ValueError(
                f"Transaction references missing account_id={account_id}; "
                f"transaction_id={transaction_id}"
            )

        expected_customer_id = valid_accounts_by_id[account_id]["customer_id"]
        if customer_id != expected_customer_id:
            raise ValueError(
                "Transaction customer/account mismatch: "
                f"transaction_id={transaction_id}, "
                f"account_id={account_id}, "
                f"customer_id={customer_id}, "
                f"expected_customer_id={expected_customer_id}"
            )


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row) + "\n")


def random_or_fixed(min_value: int, max_value: int, fixed_value: int | None, label: str) -> int:
    if fixed_value is not None:
        if fixed_value < 0:
            raise ValueError(f"--{label}-count must be non-negative")
        return fixed_value
    if min_value < 0 or max_value < 0:
        raise ValueError(f"--{label}-min and --{label}-max must be non-negative")
    if min_value > max_value:
        raise ValueError(f"--{label}-min must be less than or equal to --{label}-max")
    return random.randint(min_value, max_value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate realistic FinSight live fintech raw data.")
    parser.add_argument("--customer-count", type=int, default=None, help="Backward-compatible fixed customer count.")
    parser.add_argument("--merchant-count", type=int, default=None, help="Backward-compatible fixed merchant count.")
    parser.add_argument("--customer-min", type=int, default=1)
    parser.add_argument("--customer-max", type=int, default=8)
    parser.add_argument("--merchant-min", type=int, default=0)
    parser.add_argument("--merchant-max", type=int, default=2)
    parser.add_argument("--transaction-min", type=int, default=30)
    parser.add_argument("--transaction-max", type=int, default=120)
    parser.add_argument("--event-min", type=int, default=150)
    parser.add_argument("--event-max", type=int, default=700)
    parser.add_argument("--output-dir", default="data/raw")
    return parser.parse_args()


def choose_reusable_accounts(state: GeneratorState, new_accounts: list[dict]) -> list[dict]:
    """Mix existing and new accounts, preferring existing state when available."""
    reusable_accounts = list(new_accounts)
    if state.existing_accounts:
        existing_sample_size = min(len(state.existing_accounts), max(25, len(new_accounts) * 8))
        reusable_accounts.extend(random.sample(state.existing_accounts, k=existing_sample_size))
    return reusable_accounts


def choose_reusable_customers(state: GeneratorState, new_customers: list[dict]) -> list[dict]:
    reusable_customers = [{**customer, "is_new_customer": True} for customer in new_customers]
    if state.existing_customers:
        existing_sample_size = min(len(state.existing_customers), max(50, len(new_customers) * 10))
        reusable_customers.extend(
            {**customer, "is_new_customer": False}
            for customer in random.sample(state.existing_customers, k=existing_sample_size)
        )
    return reusable_customers


def main() -> None:
    args = parse_args()
    customer_count = random_or_fixed(args.customer_min, args.customer_max, args.customer_count, "customer")
    merchant_count = random_or_fixed(args.merchant_min, args.merchant_max, args.merchant_count, "merchant")
    transaction_count = random_or_fixed(args.transaction_min, args.transaction_max, None, "transaction")
    event_count = random_or_fixed(args.event_min, args.event_max, None, "event")

    batch_start, batch_end, dt, batch_id = current_quarter_hour_batch_window()
    run_id = generator_run_id()
    state = load_generator_state()
    print(state.state_message)

    customers = generate_customers(customer_count, start_number=state.max_customer_number + 1)
    accounts = generate_accounts(customers, start_number=state.max_account_number + 1)
    merchants = generate_merchants(
        merchant_count,
        batch_id,
        batch_start,
        batch_end,
        start_number=state.max_merchant_number + 1,
    )

    reusable_accounts = choose_reusable_accounts(state, accounts)
    reusable_customers = choose_reusable_customers(state, customers)
    reusable_merchants = [*merchants, *state.existing_merchants]

    new_transactions = generate_transactions(
        reusable_accounts,
        merchants=reusable_merchants,
        batch_start=batch_start,
        batch_end=batch_end,
        batch_id=batch_id,
        transaction_count=transaction_count,
    )
    transaction_updates = generate_transaction_status_updates(
        state.existing_transactions,
        batch_start=batch_start,
        batch_end=batch_end,
        batch_id=batch_id,
        max_updates=10,
    )
    transactions = [*new_transactions, *transaction_updates]
    customer_updates = generate_customer_updates(state.existing_customers, batch_end=batch_end, max_updates=5)
    customer_rows = [*customers, *customer_updates]
    product_events = generate_product_events(
        reusable_customers,
        reusable_accounts,
        dt,
        batch_id,
        generator_run_id=run_id,
        event_count=event_count,
        batch_start=batch_start,
        batch_end=batch_end,
    )
    kyc_applications = generate_kyc_applications(
        customers,
        dt,
        batch_id,
        generator_run_id=run_id,
        batch_start=batch_start,
        batch_end=batch_end,
        existing_customers=state.existing_customers,
    )

    validate_transaction_references(transactions, [*reusable_accounts, *state.existing_accounts])
    assert_unique(product_events, "event_id", "product event")
    assert_unique(kyc_applications, "kyc_application_id", "KYC application")

    base = Path(args.output_dir)
    write_jsonl(base / "customers" / f"dt={dt}" / f"batch_id={batch_id}" / "customers.jsonl", customer_rows)
    write_jsonl(base / "accounts" / f"dt={dt}" / f"batch_id={batch_id}" / "accounts.jsonl", accounts)
    write_jsonl(base / "merchants" / f"dt={dt}" / f"batch_id={batch_id}" / "merchants.jsonl", merchants)
    write_jsonl(base / "transactions" / f"dt={dt}" / f"batch_id={batch_id}" / "transactions.jsonl", transactions)
    write_jsonl(base / "product_events" / f"dt={dt}" / f"batch_id={batch_id}" / "product_events.jsonl", product_events)
    write_jsonl(base / "kyc_applications" / f"dt={dt}" / f"batch_id={batch_id}" / "kyc_applications.jsonl", kyc_applications)

    print(f"batch_id={batch_id}")
    print(f"generator_run_id={run_id}")
    print(f"batch_start={batch_start.isoformat()}")
    print(f"batch_end={batch_end.isoformat()}")
    print(f"new_customers={len(customers)}")
    print(f"customer_updates={len(customer_updates)}")
    print(f"accounts={len(accounts)}")
    print(f"new_merchants={len(merchants)}")
    print(f"new_transactions={len(new_transactions)}")
    print(f"transaction_updates={len(transaction_updates)}")
    print(f"transactions={len(transactions)}")
    print(f"product_events={len(product_events)}")
    print(f"kyc_applications={len(kyc_applications)}")
    print(f"neon_state_used={state.neon_state_used}")
    print(
        "max_ids_detected="
        f"customer=C{state.max_customer_number:05d},"
        f"account=A{state.max_account_number:06d},"
        f"merchant=M{state.max_merchant_number:06d}"
    )


if __name__ == "__main__":
    main()
