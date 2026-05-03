import argparse
import json
from datetime import datetime
from pathlib import Path

VALID_EVENT_NAMES = {
    "app_opened", "signup_started", "signup_completed", "kyc_started", "kyc_submitted",
    "kyc_status_viewed", "account_created", "deposit_started", "deposit_completed",
    "transfer_started", "transfer_completed", "investment_tab_viewed", "crypto_buy_clicked",
    "card_screen_viewed",
}
VALID_KYC_STATUS = {"pending", "approved", "rejected", "manual_review", "expired"}
VALID_KYC_LEVEL = {"basic", "standard", "enhanced"}
VALID_DOCUMENT_TYPE = {"passport", "national_id", "driving_license", "residence_permit"}
VALID_REVIEW_CHANNEL = {"automated", "manual", "hybrid"}
VALID_REVIEWER_TYPE = {"system", "internal_reviewer", "vendor_reviewer"}
VALID_INVESTMENT_SUBTYPE = {"crypto", "etf", "cfd", "fx"}
VALID_ACCOUNT_TYPE = {"savings", "plus", "investment", "super", "salary"}
VALID_TRANSACTION_TYPE = {"card_payment", "bank_transfer", "withdrawal", "deposit"}
VALID_SIGNUP_CHANNEL = {"organic", "paid_search", "referral", "partner", "social"}


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dt")
    parser.add_argument("--batch-id")
    parser.add_argument("--expected-customers", type=int, default=None)
    parser.add_argument("--expected-transactions", type=int, default=None)
    parser.add_argument("--base", default="data/raw")
    return parser.parse_args()


def resolve_batch(dt: str | None, batch_id: str | None) -> tuple[str, str]:
    if not dt or not batch_id:
        raise ValueError("Both --dt and --batch-id are required.")
    return dt, batch_id


def read_expected_jsonl(path: Path) -> tuple[list[dict], int]:
    if not path.exists():
        print(f"MISSING FILE: {path.as_posix()}")
        return [], 1
    return read_jsonl(path), 0


def main() -> None:
    args = parse_args()
    base = Path(args.base)
    dt, batch_id = resolve_batch(args.dt, args.batch_id)

    files = {
        "customers": base / "customers" / f"dt={dt}" / f"batch_id={batch_id}" / "customers.jsonl",
        "accounts": base / "accounts" / f"dt={dt}" / f"batch_id={batch_id}" / "accounts.jsonl",
        "transactions": base / "transactions" / f"dt={dt}" / f"batch_id={batch_id}" / "transactions.jsonl",
        "product_events": base / "product_events" / f"dt={dt}" / f"batch_id={batch_id}" / "product_events.jsonl",
        "kyc_applications": base / "kyc_applications" / f"dt={dt}" / f"batch_id={batch_id}" / "kyc_applications.jsonl",
    }
    missing_errors = 0
    for path in files.values():
        if not path.exists():
            print(f"MISSING FILE: {path.as_posix()}")
            missing_errors += 1
    if missing_errors:
        print(f"local validation errors: {missing_errors}")
        return

    customers = read_jsonl(files["customers"])
    accounts = read_jsonl(files["accounts"])
    transactions = read_jsonl(files["transactions"])
    product_events = read_jsonl(files["product_events"])
    kyc_apps = read_jsonl(files["kyc_applications"])

    customer_ids = {c["customer_id"] for c in customers}
    accounts_by_id = {a["account_id"]: a for a in accounts}

    checks = {k: 0 for k in [
        "accounts_without_customer", "transactions_without_account", "transaction_customer_mismatch",
        "non_investment_accounts_with_investment_sub_type", "investment_accounts_without_valid_sub_type",
        "product_events_without_customer", "product_events_without_account", "product_event_customer_account_mismatch",
        "invalid_product_event_name", "invalid_product_event_timestamp", "invalid_product_event_properties",
        "customers_without_kyc", "kyc_applications_without_customer", "invalid_kyc_status", "invalid_kyc_level", "invalid_document_type",
        "invalid_review_channel", "invalid_reviewer_type", "invalid_risk_score",
        "approved_kyc_without_reviewed_at", "rejected_kyc_without_reviewed_at",
        "rejected_kyc_without_rejection_reason", "pending_kyc_with_review_or_rejection_reason",
        "invalid_account_type", "invalid_transaction_type", "timestamps_after_dt",
        "customers_with_null_signup_channel", "customers_with_invalid_signup_channel",
        "expected_customers_mismatch", "expected_transactions_mismatch",
    ]}

    for c in customers:
        signup_channel = c.get("signup_channel")
        if signup_channel is None or str(signup_channel).strip() == "":
            checks["customers_with_null_signup_channel"] += 1
            continue
        if str(signup_channel).strip().lower() not in VALID_SIGNUP_CHANNEL:
            checks["customers_with_invalid_signup_channel"] += 1

    for a in accounts:
        if a["customer_id"] not in customer_ids:
            checks["accounts_without_customer"] += 1
        subtype = a.get("investment_sub_type")
        if a.get("account_type") not in VALID_ACCOUNT_TYPE:
            checks["invalid_account_type"] += 1
        if a.get("account_type") == "investment" and subtype not in VALID_INVESTMENT_SUBTYPE:
            checks["investment_accounts_without_valid_sub_type"] += 1
        if a.get("account_type") != "investment" and subtype not in (None, ""):
            checks["non_investment_accounts_with_investment_sub_type"] += 1

    for t in transactions:
        acct = accounts_by_id.get(t["account_id"])
        if t.get("transaction_type") not in VALID_TRANSACTION_TYPE:
            checks["invalid_transaction_type"] += 1
        if acct is None:
            checks["transactions_without_account"] += 1
        elif t["customer_id"] != acct["customer_id"]:
            checks["transaction_customer_mismatch"] += 1

    for pe in product_events:
        if pe["customer_id"] not in customer_ids:
            checks["product_events_without_customer"] += 1
        acct_id = pe.get("account_id")
        if acct_id not in (None, ""):
            acct = accounts_by_id.get(acct_id)
            if acct is None:
                checks["product_events_without_account"] += 1
            elif acct["customer_id"] != pe["customer_id"]:
                checks["product_event_customer_account_mismatch"] += 1
        if pe.get("event_name") not in VALID_EVENT_NAMES:
            checks["invalid_product_event_name"] += 1
        try:
            ts = datetime.fromisoformat(str(pe.get("event_timestamp", "")).replace("Z", "+00:00"))
            if ts > datetime.fromisoformat(f"{dt}T23:59:59+00:00"):
                checks["invalid_product_event_timestamp"] += 1
        except Exception:
            checks["invalid_product_event_timestamp"] += 1
        if not isinstance(pe.get("event_properties"), dict):
            checks["invalid_product_event_properties"] += 1

    kyc_by_customer = {}
    for ka in kyc_apps:
        kyc_by_customer[ka["customer_id"]] = kyc_by_customer.get(ka["customer_id"], 0) + 1
        if ka["customer_id"] not in customer_ids:
            checks["kyc_applications_without_customer"] += 1
        if ka.get("kyc_status") not in VALID_KYC_STATUS:
            checks["invalid_kyc_status"] += 1
        if ka.get("kyc_level") not in VALID_KYC_LEVEL:
            checks["invalid_kyc_level"] += 1
        if ka.get("document_type") not in VALID_DOCUMENT_TYPE:
            checks["invalid_document_type"] += 1
        if ka.get("review_channel") not in VALID_REVIEW_CHANNEL:
            checks["invalid_review_channel"] += 1
        if ka.get("reviewer_type") not in VALID_REVIEWER_TYPE:
            checks["invalid_reviewer_type"] += 1
        try:
            if not (0 <= float(ka.get("risk_score")) <= 100):
                checks["invalid_risk_score"] += 1
        except Exception:
            checks["invalid_risk_score"] += 1
        if ka.get("kyc_status") == "approved" and not ka.get("reviewed_at"):
            checks["approved_kyc_without_reviewed_at"] += 1
        if ka.get("kyc_status") == "rejected":
            if not ka.get("reviewed_at"):
                checks["rejected_kyc_without_reviewed_at"] += 1
            if not ka.get("rejection_reason"):
                checks["rejected_kyc_without_rejection_reason"] += 1
        if ka.get("kyc_status") == "pending" and (ka.get("reviewed_at") or ka.get("rejection_reason")):
            checks["pending_kyc_with_review_or_rejection_reason"] += 1

    checks["customers_without_kyc"] = sum(
        1 for customer_id in customer_ids
        if kyc_by_customer.get(customer_id, 0) == 0
    )

    dt_end = datetime.fromisoformat(f"{dt}T23:59:59+00:00")
    timestamp_fields = [
        (customers, "created_at"), (accounts, "opened_at"), (transactions, "transaction_timestamp"),
        (product_events, "event_timestamp"), (kyc_apps, "submitted_at"), (kyc_apps, "reviewed_at"),
    ]
    for rows, field_name in timestamp_fields:
        for row in rows:
            ts_value = row.get(field_name)
            if not ts_value:
                continue
            try:
                ts = datetime.fromisoformat(str(ts_value).replace("Z", "+00:00"))
                if ts > dt_end:
                    checks["timestamps_after_dt"] += 1
            except Exception:
                checks["timestamps_after_dt"] += 1

    if args.expected_customers is not None and len(customers) != args.expected_customers:
        checks["expected_customers_mismatch"] = 1
    if args.expected_transactions is not None and len(transactions) != args.expected_transactions:
        checks["expected_transactions_mismatch"] = 1

    print(f"customers: {len(customers)}")
    print(f"accounts: {len(accounts)}")
    print(f"transactions: {len(transactions)}")
    print(f"product_events: {len(product_events)}")
    print(f"kyc_applications: {len(kyc_apps)}")

    total_errors = sum(checks.values()) + missing_errors
    for name, value in checks.items():
        print(f"{name}: {value}")
    print(f"local validation errors: {total_errors}")


if __name__ == "__main__":
    main()
