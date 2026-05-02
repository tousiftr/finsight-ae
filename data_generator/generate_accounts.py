import random
from datetime import datetime, timezone


ACCOUNT_TYPES = ["savings", "plus", "investment", "super", "salary"]
INVESTMENT_SUB_TYPES = ["crypto", "etf", "cfd", "fx"]


def make_account_id(index: int) -> str:
    return f"A{900000 + index:06d}"


def generate_accounts(customers: list[dict]) -> list[dict]:
    accounts: list[dict] = []
    now_iso = datetime.now(timezone.utc).isoformat()
    account_seq = 1

    for customer in customers:
        account_count = random.randint(1, 4)

        for _ in range(account_count):
            account_type = random.choice(ACCOUNT_TYPES)
            investment_sub_type = (
                random.choice(INVESTMENT_SUB_TYPES)
                if account_type == "investment"
                else None
            )

            accounts.append(
                {
                    "account_id": make_account_id(account_seq),
                    "customer_id": customer["customer_id"],
                    "account_type": account_type,
                    "investment_sub_type": investment_sub_type,
                    "currency": random.choice(["USD", "EUR", "GBP", "BDT"]),
                    "account_status": random.choice(["active", "pending", "closed"]),
                    "opened_at": customer.get("created_at") or now_iso,
                    "updated_at": now_iso,
                }
            )
            account_seq += 1

    return accounts
