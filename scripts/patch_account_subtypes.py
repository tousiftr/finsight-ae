import argparse
import json
import random
from pathlib import Path

SUBTYPES_BY_ACCOUNT_TYPE = {
    "savings": ["instant_access", "goal_savings", "high_yield", "emergency"],
    "plus": ["standard_checking"],
    "investment": ["crypto", "etf", "cfd", "fx", "brokerage"],
    "super": ["retirement_super"],
    "salary": ["salary_account"],
}

PLAN_TIERS_BY_ACCOUNT_TYPE = {
    "plus": ["plus"],
    "savings": ["free", "plus", "premium"],
    "investment": ["free", "plus", "premium"],
    "super": ["free", "plus", "premium"],
    "salary": ["free", "plus", "premium"],
}

INVESTMENT_SUBTYPES = {"crypto", "etf", "cfd", "fx"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dt", required=True)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)

    path = (
        Path("data/raw/accounts")
        / f"dt={args.dt}"
        / f"batch_id={args.batch_id}"
        / "accounts.jsonl"
    )

    if not path.exists():
        raise FileNotFoundError(path)

    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                row = json.loads(line)

                account_type = row.get("account_type")
                valid_subtypes = SUBTYPES_BY_ACCOUNT_TYPE.get(account_type, ["standard"])
                account_sub_type = random.choice(valid_subtypes)

                row["account_sub_type"] = account_sub_type
                row["plan_tier"] = random.choice(
                    PLAN_TIERS_BY_ACCOUNT_TYPE.get(account_type, ["free"])
                )

                # Keep old compatibility field populated only for investment accounts.
                if account_type == "investment":
                    if account_sub_type in INVESTMENT_SUBTYPES:
                        row["investment_sub_type"] = account_sub_type
                    else:
                        row["investment_sub_type"] = random.choice(sorted(INVESTMENT_SUBTYPES))
                else:
                    row["investment_sub_type"] = None

                rows.append(row)

    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, default=str) + "\n")

    print(f"patched accounts: {len(rows)}")
    print(f"path: {path}")


if __name__ == "__main__":
    main()