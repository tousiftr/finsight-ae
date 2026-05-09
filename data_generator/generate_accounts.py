import random
from datetime import datetime, timezone


ACCOUNT_TYPES = ["savings", "plus", "investment", "super", "salary"]
ACCOUNT_TYPE_WEIGHTS = [42, 24, 14, 8, 12]
ACCOUNT_SUB_TYPES = {
    "savings": ["instant_access", "goal_savings", "high_yield", "emergency"],
    "plus": ["standard_checking"],
    "investment": ["crypto", "etf", "cfd", "fx"],
    "super": ["retirement_super"],
    "salary": ["salary_account"],
}
PLAN_TIERS = ["free", "plus", "premium"]
PLAN_TIER_WEIGHTS = [62, 28, 10]


def make_account_id(index: int) -> str:
    return f"A{index:06d}"


def _account_count_for_customer() -> int:
    return random.choices([1, 2], weights=[86, 14], k=1)[0]


def generate_accounts(customers: list[dict], start_number: int = 900001) -> list[dict]:
    accounts: list[dict] = []
    now_iso = datetime.now(timezone.utc).isoformat()
    account_number = start_number

    for customer in customers:
        for _ in range(_account_count_for_customer()):
            account_type = random.choices(ACCOUNT_TYPES, weights=ACCOUNT_TYPE_WEIGHTS, k=1)[0]
            account_sub_type = random.choice(ACCOUNT_SUB_TYPES[account_type])
            investment_sub_type = account_sub_type if account_type == "investment" else None
            status = random.choices(["active", "pending", "closed"], weights=[86, 11, 3], k=1)[0]
            initial_balance = round(random.uniform(0, 5000), 2)
            current_balance = round(max(0, initial_balance + random.uniform(-500, 3500)), 2)
            closed_at = now_iso if status == "closed" and random.random() < 0.75 else None

            accounts.append(
                {
                    "account_id": make_account_id(account_number),
                    "customer_id": customer["customer_id"],
                    "account_type": account_type,
                    "account_sub_type": account_sub_type,
                    "investment_sub_type": investment_sub_type,
                    "plan_tier": random.choices(PLAN_TIERS, weights=PLAN_TIER_WEIGHTS, k=1)[0],
                    "currency": random.choices(["USD", "EUR", "GBP", "BDT"], weights=[45, 18, 14, 23], k=1)[0],
                    "account_status": status,
                    "opened_at": customer.get("created_at") or now_iso,
                    "closed_at": closed_at,
                    "initial_balance": initial_balance,
                    "current_balance": current_balance,
                    "updated_at": now_iso,
                }
            )
            account_number += 1

    return accounts
