import random
from datetime import datetime, timedelta, timezone


TRANSACTION_TYPES = ["card_payment", "bank_transfer", "withdrawal", "deposit"]
TRANSACTION_TYPE_WEIGHTS = [52, 18, 10, 20]
TRANSACTION_STATUSES = ["completed", "pending", "failed", "declined"]
TRANSACTION_STATUS_WEIGHTS = [84, 8, 5, 3]
MERCHANT_CATEGORIES = ["groceries", "travel", "utilities", "food", "ecommerce", "subscriptions", "transport", "healthcare", "entertainment"]
PAYMENT_METHODS = ["debit_card", "bank_account", "wallet", "virtual_card", "ach"]
FAILURE_REASONS = ["insufficient_funds", "card_expired", "suspected_fraud", "merchant_unavailable", "network_timeout", "kyc_required"]
CATEGORY_AMOUNT_RANGES = {
    "groceries": (8, 220),
    "food": (5, 160),
    "transport": (3, 90),
    "utilities": (25, 450),
    "ecommerce": (10, 1200),
    "subscriptions": (3, 80),
    "travel": (40, 3500),
    "healthcare": (15, 900),
    "entertainment": (8, 350),
}
TYPE_AMOUNT_RANGES = {
    "bank_transfer": (25, 5000),
    "withdrawal": (20, 1500),
    "deposit": (25, 7000),
}


def current_hourly_batch_window(now: datetime | None = None) -> tuple[datetime, datetime, str, str]:
    now_utc = now or datetime.now(timezone.utc)
    current_slot_minute = (now_utc.astimezone(timezone.utc).minute // 20) * 20
    current_slot = now_utc.astimezone(timezone.utc).replace(minute=current_slot_minute, second=0, microsecond=0)
    batch_start = current_slot - timedelta(minutes=20)
    batch_end = current_slot - timedelta(seconds=1)
    return batch_start, batch_end, batch_start.strftime("%Y-%m-%d"), batch_start.strftime("%Y%m%d_%H%M")


def random_time_between(start: datetime, end: datetime) -> datetime:
    if end <= start:
        return start
    total_seconds = int((end - start).total_seconds())
    return start + timedelta(seconds=random.randint(0, total_seconds))


def make_transaction_id(index: int, batch_id: str | None = None) -> str:
    if batch_id:
        return f"txn_{batch_id}_{index:06d}"
    return f"txn_{index:06d}"


def _amount_for(transaction_type: str, merchant_category: str | None) -> float:
    low, high = TYPE_AMOUNT_RANGES.get(transaction_type, CATEGORY_AMOUNT_RANGES.get(merchant_category or "ecommerce", (5, 1000)))
    return round(random.triangular(low, high, low + ((high - low) * 0.25)), 2)


def generate_transactions(
    accounts: list[dict],
    min_per_account: int = 1,
    max_per_account: int = 8,
    merchants: list[dict] | None = None,
    batch_start: datetime | None = None,
    batch_end: datetime | None = None,
    batch_id: str | None = None,
    transaction_count: int | None = None,
) -> list[dict]:
    if batch_start is None or batch_end is None:
        batch_start, batch_end, _, default_batch_id = current_hourly_batch_window()
        batch_id = batch_id or default_batch_id

    if not accounts:
        return []

    if transaction_count is None:
        transaction_count = sum(random.randint(min_per_account, max_per_account) for _ in accounts)

    transactions: list[dict] = []
    for txn_seq in range(1, transaction_count + 1):
        account = random.choice(accounts)
        merchant = random.choice(merchants) if merchants and random.random() < 0.72 else None
        transaction_type = random.choices(TRANSACTION_TYPES, weights=TRANSACTION_TYPE_WEIGHTS, k=1)[0]
        merchant_category = merchant["merchant_category"] if merchant else random.choice(MERCHANT_CATEGORIES)
        status = random.choices(TRANSACTION_STATUSES, weights=TRANSACTION_STATUS_WEIGHTS, k=1)[0]
        amount = _amount_for(transaction_type, merchant_category)
        fee_amount = None
        if status == "completed" and transaction_type in {"bank_transfer", "withdrawal"} and random.random() < 0.35:
            fee_amount = round(max(0.25, min(25, amount * random.uniform(0.002, 0.012))), 2)
        failure_reason = random.choice(FAILURE_REASONS) if status in {"failed", "declined"} else None

        transactions.append(
            {
                "transaction_id": make_transaction_id(txn_seq, batch_id),
                "account_id": account["account_id"],
                "customer_id": account["customer_id"],
                "transaction_type": transaction_type,
                "amount": amount,
                "currency": account.get("currency", "USD"),
                "status": status,
                "merchant_id": merchant["merchant_id"] if merchant else None,
                "merchant_category": merchant_category,
                "payment_method": random.choice(PAYMENT_METHODS),
                "fee_amount": fee_amount,
                "failure_reason": failure_reason,
                "transaction_timestamp": random_time_between(batch_start, batch_end).isoformat(),
                "batch_id": batch_id,
            }
        )

    return transactions
