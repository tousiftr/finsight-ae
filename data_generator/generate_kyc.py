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
    next_app_id = 1

    # Initial applications: one per customer with realistic status distribution.
    base_statuses = random.choices(
        KYC_STATUSES,
        weights=[8, 75, 5, 10, 2],
        k=len(customers),
    )

    for i, customer in enumerate(customers, start=1):
        status = base_statuses[i - 1]
        submitted_at = day_start + timedelta(minutes=(i * 13) % 1000)

        reviewed_at = None
        rejection_reason = None

        if status in {"approved", "rejected", "manual_review"}:
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
            "kyc_application_id": f"kyc_{batch_id}_{next_app_id:06d}",
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
        next_app_id += 1

        # Small fraction of customers have a follow-up application (resubmission/expiry).
        if random.random() < 0.07:
            follow_up_status = random.choices(
                ["approved", "rejected", "expired", "manual_review", "pending"],
                weights=[55, 18, 10, 10, 7],
                k=1,
            )[0]
            follow_up_submitted_at = submitted_at + timedelta(hours=random.randint(6, 72))
            follow_up_reviewed_at = None
            follow_up_rejection_reason = None

            if follow_up_status in {"approved", "rejected", "manual_review"}:
                follow_up_reviewed_at = follow_up_submitted_at + timedelta(minutes=random.randint(10, 900))
            elif follow_up_status == "expired" and random.random() < 0.5:
                follow_up_reviewed_at = follow_up_submitted_at + timedelta(minutes=random.randint(30, 1200))

            if follow_up_status == "rejected":
                follow_up_rejection_reason = random.choice([
                    "document_mismatch",
                    "blurry_document",
                    "sanctions_hit",
                    "insufficient_information",
                ])

            rows.append({
                "kyc_application_id": f"kyc_{batch_id}_{next_app_id:06d}",
                "customer_id": customer["customer_id"],
                "submitted_at": follow_up_submitted_at.astimezone(timezone.utc).isoformat(),
                "reviewed_at": follow_up_reviewed_at.astimezone(timezone.utc).isoformat() if follow_up_reviewed_at else None,
                "kyc_status": follow_up_status,
                "kyc_level": random.choice(KYC_LEVELS),
                "document_type": random.choice(DOCUMENT_TYPES),
                "country": random.choice(["BD", "US", "GB", "SG", "AE"]),
                "risk_score": round(random.uniform(0, 100), 2),
                "rejection_reason": follow_up_rejection_reason,
                "review_channel": random.choice(REVIEW_CHANNELS),
                "reviewer_type": random.choice(REVIEWER_TYPES),
                "dt": dt,
                "batch_id": batch_id,
            })
            next_app_id += 1

    return rows
