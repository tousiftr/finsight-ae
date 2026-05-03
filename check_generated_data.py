import json
from pathlib import Path

DT = "2026-05-02"
BATCH_ID = "20260502_1436"
BASE = Path("data/raw")


def read_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main():
    customers = read_jsonl(BASE / "customers" / f"dt={DT}" / f"batch_id={BATCH_ID}" / "customers.jsonl")
    accounts = read_jsonl(BASE / "accounts" / f"dt={DT}" / f"batch_id={BATCH_ID}" / "accounts.jsonl")
    transactions = read_jsonl(BASE / "transactions" / f"dt={DT}" / f"batch_id={BATCH_ID}" / "transactions.jsonl")
    product_events = read_jsonl(BASE / "product_events" / f"dt={DT}" / f"batch_id={BATCH_ID}" / "product_events.jsonl")
    kyc_apps = read_jsonl(BASE / "kyc_applications" / f"dt={DT}" / f"batch_id={BATCH_ID}" / "kyc_applications.jsonl")

    customer_ids = {c["customer_id"] for c in customers}
    account_to_customer = {a["account_id"]: a["customer_id"] for a in accounts}

    errors = 0
    for pe in product_events:
        if pe["customer_id"] not in customer_ids:
            errors += 1
        account_id = pe.get("account_id")
        if account_id is not None:
            if account_id not in account_to_customer:
                errors += 1
            elif account_to_customer[account_id] != pe["customer_id"]:
                errors += 1

    valid_status = {"pending", "approved", "rejected", "manual_review", "expired"}
    for ka in kyc_apps:
        if ka["customer_id"] not in customer_ids:
            errors += 1
        if ka["kyc_status"] not in valid_status:
            errors += 1
        if ka["kyc_status"] == "approved" and not ka.get("reviewed_at"):
            errors += 1
        if ka["kyc_status"] == "rejected" and not ka.get("rejection_reason"):
            errors += 1
        if ka["kyc_status"] == "pending" and (ka.get("reviewed_at") or ka.get("rejection_reason")):
            errors += 1
        if not (0 <= float(ka["risk_score"]) <= 100):
            errors += 1

    print(f"customers={len(customers)} accounts={len(accounts)} transactions={len(transactions)}")
    print(f"product_events={len(product_events)} kyc_applications={len(kyc_apps)}")
    print(f"error_count={errors}")


if __name__ == "__main__":
    main()
