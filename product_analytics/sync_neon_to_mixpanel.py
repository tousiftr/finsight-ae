from __future__ import annotations

import base64
import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import urlencode, urlparse, unquote
from urllib.request import Request, urlopen

import pg8000.dbapi


SAFE_TABLE_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$")


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


def _normalize_properties(value: object) -> dict[str, object]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return dict(value)  # type: ignore[arg-type]


def _validate_export_table(export_table: str) -> str:
    if not SAFE_TABLE_PATTERN.match(export_table):
        raise ValueError(
            "Invalid MIXPANEL_EXPORT_TABLE. Use schema.table or table_name with letters, numbers, and underscores only."
        )
    return export_table


def main() -> int:
    neon_database_url = os.getenv("NEON_DATABASE_URL")
    project_id = os.getenv("MIXPANEL_PROJECT_ID")
    service_user = os.getenv("MIXPANEL_SERVICE_ACCOUNT_USER")
    service_secret = os.getenv("MIXPANEL_SERVICE_ACCOUNT_SECRET")
    region = os.getenv("MIXPANEL_REGION", "api")
    batch_size = int(os.getenv("MIXPANEL_BATCH_SIZE", "20"))
    export_table = _validate_export_table(
        os.getenv("MIXPANEL_EXPORT_TABLE", "dbt_fs.mixpanel_events_export")
    )
    dry_run = os.getenv("MIXPANEL_DRY_RUN", "false").lower() in {"1", "true", "yes"}

    required = {
        "NEON_DATABASE_URL": neon_database_url,
        "MIXPANEL_PROJECT_ID": project_id,
        "MIXPANEL_SERVICE_ACCOUNT_USER": service_user,
        "MIXPANEL_SERVICE_ACCOUNT_SECRET": service_secret,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        print(f"Mixpanel sync skipped: missing required environment variable(s): {', '.join(missing)}")
        print("No events sent.")
        return 0

    conn = pg8000.dbapi.connect(ssl_context=True, **_parse_neon_url(neon_database_url))
    cur = conn.cursor()
    cur.execute(
        f"""
        select
            source_event_id,
            event_name,
            distinct_id,
            event_time,
            insert_id,
            event_source,
            event_properties
        from {export_table}
        where event_name is not null
          and distinct_id is not null
          and event_time is not null
          and insert_id is not null
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
    for source_event_id, event_name, distinct_id, event_time, insert_id, event_source, event_properties in rows:
        props = _normalize_properties(event_properties)
        props.update(
            {
                "time": _to_epoch_seconds(event_time),
                "distinct_id": str(distinct_id),
                "$insert_id": str(insert_id),
                "source_event_id": str(source_event_id),
                "event_source": str(event_source),
                "pipeline_source": "finsight_neon_dbt",
            }
        )
        events.append({"event": str(event_name), "properties": props})

    print(f"Prepared {len(events)} event(s) from {export_table}.")
    print("First event preview:")
    print(json.dumps(events[0], indent=2, default=str))

    if dry_run:
        print("MIXPANEL_DRY_RUN=true, no events sent.")
        return 0

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
