import random
from datetime import datetime, timezone, timedelta


TRANSACTION_TYPES = ["card_payment", "bank_transfer", "withdrawal", "deposit"]
TRANSACTION_STATUSES = ["completed", "pending", "failed", "declined"]
MERCHANT_CATEGORIES = ["groceries", "travel", "utilities", "food", "ecommerce", "subscriptions"]


def current_hourly_batch_window(now: datetime | None = None) -> tuple[datetime, datetime, str, str]:
    now_utc = now or datetime.now(timezone.utc)
    current_hour = now_utc.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    batch_start = current_hour - timedelta(hours=1)
    batch_end = current_hour - timedelta(seconds=1)
    return batch_start, batch_end, batch_start.strftime("%Y-%m-%d"), batch_start.strftime("%Y%m%d_%H00")


def random_time_between(start: datetime, end: datetime) -> datetime:
    if end <= start:
        return start
    total_seconds = int((end - start).total_seconds())
    return start + timedelta(seconds=random.randint(0, total_seconds))


def make_transaction_id(index: int) -> str:
    return f"txn_{index:06d}"


def generate_transactions(
    accounts: list[dict],
    min_per_account: int = 1,
    max_per_account: int = 8,
    merchants: list[dict] | None = None,
    batch_start: datetime | None = None,
    batch_end: datetime | None = None,
    batch_id: str | None = None,
) -> list[dict]:
    if batch_start is None or batch_end is None:
        batch_start, batch_end, _, default_batch_id = current_hourly_batch_window()
        batch_id = batch_id or default_batch_id

    transactions: list[dict] = []
    txn_seq = 1

    for account in accounts:
        tx_count = random.randint(min_per_account, max_per_account)

        for _ in range(tx_count):
            merchant = random.choice(merchants) if merchants else None
            transaction_time = random_time_between(batch_start, batch_end)
            transactions.append(
                {
                    "transaction_id": make_transaction_id(txn_seq),
                    "account_id": account["account_id"],
                    "customer_id": account["customer_id"],
                    "transaction_type": random.choice(TRANSACTION_TYPES),
                    "amount": round(random.uniform(1, 2500), 2),
                    "currency": account.get("currency", "USD"),
                    "status": random.choice(TRANSACTION_STATUSES),
                    "merchant_id": merchant["merchant_id"] if merchant else None,
                    "merchant_category": merchant["merchant_category"] if merchant else random.choice(MERCHANT_CATEGORIES),
                    "transaction_timestamp": transaction_time.isoformat(),
                    "batch_id": batch_id,
                }
            )
            txn_seq += 1

    return transactions
