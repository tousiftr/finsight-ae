import random
from datetime import datetime, timedelta, timezone

KYC_STATUSES = ["pending", "approved", "rejected", "manual_review", "expired"]
KYC_LEVELS = ["basic", "standard", "enhanced"]
DOCUMENT_TYPES = ["passport", "national_id", "driving_license", "residence_permit"]
REVIEW_CHANNELS = ["automated", "manual", "hybrid"]
REVIEWER_TYPES = ["system", "internal_reviewer", "vendor_reviewer"]


def generate_kyc_applications(customers: list[dict], dt: str, batch_id: str) -> list[dict]:
    rows: list[dict] = []
    day_start = datetime.fromisoformat(f"{dt}T00:00:00+00:00")

    for i, customer in enumerate(customers, start=1):
        status = random.choices(KYC_STATUSES, weights=[18, 62, 10, 8, 2], k=1)[0]
        submitted_at = day_start + timedelta(minutes=(i * 13) % 1000)

        reviewed_at = None
        rejection_reason = None

        if status in {"approved", "rejected"}:
            reviewed_at = submitted_at + timedelta(minutes=random.randint(5, 600))
        elif status == "expired" and random.random() < 0.5:
            reviewed_at = submitted_at + timedelta(minutes=random.randint(30, 1200))

        if status == "rejected":
            rejection_reason = random.choice([
                "document_mismatch",
                "blurry_document",
                "sanctions_hit",
                "insufficient_information",
            ])

        rows.append({
            "kyc_application_id": f"kyc_{i:06d}",
            "customer_id": customer["customer_id"],
            "submitted_at": submitted_at.astimezone(timezone.utc).isoformat(),
            "reviewed_at": reviewed_at.astimezone(timezone.utc).isoformat() if reviewed_at else None,
            "kyc_status": status,
            "kyc_level": random.choice(KYC_LEVELS),
            "document_type": random.choice(DOCUMENT_TYPES),
            "country": random.choice(["BD", "US", "GB", "SG", "AE"]),
            "risk_score": round(random.uniform(0, 100), 2),
            "rejection_reason": rejection_reason,
            "review_channel": random.choice(REVIEW_CHANNELS),
            "reviewer_type": random.choice(REVIEWER_TYPES),
            "dt": dt,
            "batch_id": batch_id,
        })

    return rows
