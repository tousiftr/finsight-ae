from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from urllib.parse import urlencode, urlparse, unquote
from urllib.request import Request, urlopen
import base64

import pg8000.dbapi


def _parse_neon_url(database_url: str) -> dict[str, object]:
    parsed = urlparse(database_url)
    return {
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "database": unquote(parsed.path.lstrip("/")),
    }


def _to_epoch_seconds(value: datetime) -> int:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return int(value.timestamp())


def main() -> int:
    neon_database_url = os.getenv("NEON_DATABASE_URL")
    project_id = os.getenv("MIXPANEL_PROJECT_ID")
    service_user = os.getenv("MIXPANEL_SERVICE_ACCOUNT_USER")
    service_secret = os.getenv("MIXPANEL_SERVICE_ACCOUNT_SECRET")
    region = os.getenv("MIXPANEL_REGION", "api")
    batch_size = int(os.getenv("MIXPANEL_BATCH_SIZE", "20"))
    export_table = os.getenv("MIXPANEL_EXPORT_TABLE", "dbt_fs.mixpanel_events_export")

    required = {
        "NEON_DATABASE_URL": neon_database_url,
        "MIXPANEL_PROJECT_ID": project_id,
        "MIXPANEL_SERVICE_ACCOUNT_USER": service_user,
        "MIXPANEL_SERVICE_ACCOUNT_SECRET": service_secret,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        print(f"Mixpanel sync skipped: missing required environment variable(s): {', '.join(missing)}")
        print("No events sent.")
        return 0

    conn = pg8000.dbapi.connect(ssl_context=True, **_parse_neon_url(neon_database_url))
    cur = conn.cursor()
    cur.execute(
        f"""
        select event_name, distinct_id, event_time, insert_id, event_properties
        from {export_table}
        where event_time is not null
        order by event_time asc
        limit %s
        """,
        (batch_size,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        print(f"No rows found in {export_table}; nothing to send.")
        return 0

    events = []
    for event_name, distinct_id, event_time, insert_id, event_properties in rows:
        props = event_properties or {}
        if isinstance(props, str):
            props = json.loads(props)
        props.update(
            {
                "time": _to_epoch_seconds(event_time),
                "distinct_id": str(distinct_id),
                "$insert_id": str(insert_id),
            }
        )
        events.append({"event": event_name, "properties": props})

    print("First event preview:")
    print(json.dumps(events[0], indent=2, default=str))

    endpoint = f"https://{region}.mixpanel.com/import"
    query = urlencode({"strict": 1, "project_id": project_id})
    payload = json.dumps(events).encode("utf-8")
    auth = base64.b64encode(f"{service_user}:{service_secret}".encode("utf-8")).decode("ascii")

    request = Request(
        url=f"{endpoint}?{query}",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth}",
        },
        method="POST",
    )

    try:
        with urlopen(request) as response:
            body = response.read().decode("utf-8")
            print(f"Mixpanel response status: {response.status}")
            print(f"Mixpanel response body: {body}")
            if response.status != 200:
                raise RuntimeError(f"Mixpanel import failed with status {response.status}: {body}")
    except Exception as exc:
        print(f"Mixpanel import failed: {exc}")
        return 1

    print(f"Successfully sent {len(events)} events to Mixpanel.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
