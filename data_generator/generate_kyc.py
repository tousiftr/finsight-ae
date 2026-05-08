import random
from datetime import datetime, timedelta, timezone

KYC_STATUSES = ["pending", "approved", "rejected", "manual_review", "expired"]
KYC_LEVELS = ["basic", "standard", "enhanced"]
DOCUMENT_TYPES = ["passport", "national_id", "driving_license", "residence_permit"]
REVIEW_CHANNELS = ["automated", "manual", "hybrid"]
REVIEWER_TYPES = ["system", "internal_reviewer", "vendor_reviewer"]
REJECTION_REASONS = ["document_mismatch", "blurry_document", "sanctions_hit", "insufficient_information"]


def random_time_between(start: datetime, end: datetime) -> datetime:
    if end <= start:
        return start
    total_seconds = int((end - start).total_seconds())
    return start + timedelta(seconds=random.randint(0, total_seconds))


def _kyc_row(customer: dict, status: str, submitted_at: datetime, batch_id: str, app_id: int, dt: str) -> dict:
    reviewed_at = None
    rejection_reason = None

    if status in {"approved", "rejected", "manual_review"}:
        reviewed_at = submitted_at + timedelta(minutes=random.randint(3, 180))
    elif status == "expired" and random.random() < 0.5:
        reviewed_at = submitted_at + timedelta(minutes=random.randint(30, 240))

    if status == "rejected":
        rejection_reason = random.choice(REJECTION_REASONS)

    risk_score = round(random.triangular(0, 100, 28 if status == "approved" else 62), 2)
    return {
        "kyc_application_id": f"kyc_{batch_id}_{app_id:06d}",
        "customer_id": customer["customer_id"],
        "submitted_at": submitted_at.astimezone(timezone.utc).isoformat(),
        "reviewed_at": reviewed_at.astimezone(timezone.utc).isoformat() if reviewed_at else None,
        "kyc_status": status,
        "kyc_level": random.choices(KYC_LEVELS, weights=[45, 43, 12], k=1)[0],
        "document_type": random.choice(DOCUMENT_TYPES),
        "country": customer.get("country") or random.choice(["BD", "US", "GB", "SG", "AE"]),
        "risk_score": risk_score,
        "rejection_reason": rejection_reason,
        "review_channel": random.choices(REVIEW_CHANNELS, weights=[62, 18, 20], k=1)[0],
        "reviewer_type": random.choices(REVIEWER_TYPES, weights=[60, 28, 12], k=1)[0],
        "dt": dt,
        "batch_id": batch_id,
    }


def generate_kyc_applications(
    customers: list[dict],
    dt: str,
    batch_id: str,
    batch_start: datetime | None = None,
    batch_end: datetime | None = None,
    existing_customers: list[dict] | None = None,
) -> list[dict]:
    if batch_start is None:
        batch_start = datetime.fromisoformat(f"{dt}T00:00:00+00:00")
    if batch_end is None:
        batch_end = batch_start + timedelta(minutes=20) - timedelta(seconds=1)

    rows: list[dict] = []
    next_app_id = 1

    for customer in customers:
        if random.random() > 0.82:
            continue
        status = random.choices(KYC_STATUSES, weights=[13, 64, 6, 14, 3], k=1)[0]
        submitted_at = random_time_between(batch_start, batch_end)
        rows.append(_kyc_row(customer, status, submitted_at, batch_id, next_app_id, dt))
        next_app_id += 1

    follow_up_candidates = existing_customers or []
    for customer in random.sample(follow_up_candidates, k=min(len(follow_up_candidates), random.randint(0, 3))):
        if random.random() > 0.35:
            continue
        status = random.choices(["approved", "rejected", "manual_review", "pending", "expired"], weights=[38, 12, 28, 15, 7], k=1)[0]
        submitted_at = random_time_between(batch_start, batch_end)
        rows.append(_kyc_row(customer, status, submitted_at, batch_id, next_app_id, dt))
        next_app_id += 1

    return rows
