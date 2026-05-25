from __future__ import annotations

import os


def main() -> int:
    neon_database_url = os.getenv("NEON_DATABASE_URL")
    mixpanel_project_id = os.getenv("MIXPANEL_PROJECT_ID")
    mixpanel_service_account_user = os.getenv("MIXPANEL_SERVICE_ACCOUNT_USER")
    mixpanel_service_account_secret = os.getenv("MIXPANEL_SERVICE_ACCOUNT_SECRET")
    mixpanel_region = os.getenv("MIXPANEL_REGION", "api")
    mixpanel_batch_size = os.getenv("MIXPANEL_BATCH_SIZE", "1000")

    required = {
        "MIXPANEL_PROJECT_ID": mixpanel_project_id,
        "MIXPANEL_SERVICE_ACCOUNT_USER": mixpanel_service_account_user,
        "MIXPANEL_SERVICE_ACCOUNT_SECRET": mixpanel_service_account_secret,
    }
    missing = [key for key, value in required.items() if not value]

    if missing:
        print(
            "Mixpanel sync skipped: missing required environment variable(s): "
            + ", ".join(missing)
            + "."
        )
        print("No events were sent. This is expected until Mixpanel credentials are configured.")
        return 0

    if not neon_database_url:
        print("Mixpanel sync skipped: NEON_DATABASE_URL is not set.")
        print("No events were sent.")
        return 0

    print("Mixpanel sync placeholder: credentials detected; no API call implemented yet.")
    print(
        f"Planned source: dbt model/view mixpanel_events_export from Neon. region={mixpanel_region}, batch_size={mixpanel_batch_size}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
