import random
from datetime import datetime, timezone


TRANSACTION_TYPES = ["card_payment", "bank_transfer", "withdrawal", "deposit"]
TRANSACTION_STATUSES = ["completed", "pending", "failed", "declined"]
MERCHANT_CATEGORIES = ["groceries", "travel", "utilities", "food", "ecommerce", "subscriptions"]


def make_transaction_id(index: int) -> str:
    return f"txn_{index:06d}"


def generate_transactions(accounts: list[dict], min_per_account: int = 1, max_per_account: int = 8) -> list[dict]:
    transactions: list[dict] = []
    txn_seq = 1

    for account in accounts:
        tx_count = random.randint(min_per_account, max_per_account)

        for _ in range(tx_count):
            transactions.append(
                {
                    "transaction_id": make_transaction_id(txn_seq),
                    "account_id": account["account_id"],
                    "customer_id": account["customer_id"],
                    "transaction_type": random.choice(TRANSACTION_TYPES),
                    "amount": round(random.uniform(1, 2500), 2),
                    "currency": account.get("currency", "USD"),
                    "status": random.choice(TRANSACTION_STATUSES),
                    "merchant_category": random.choice(MERCHANT_CATEGORIES),
                    "transaction_timestamp": datetime.now(timezone.utc).isoformat(),
                    "batch_id": datetime.now(timezone.utc).strftime("%Y%m%d_%H%M"),
                }
            )
            txn_seq += 1

    return transactions
