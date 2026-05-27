from __future__ import annotations

import base64
import json
import os
import re
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse, unquote
from urllib.request import Request, urlopen

import pg8000.dbapi


SAFE_TABLE_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$")
RESPONSE_BODY_MAX_LEN = 2000


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


def _truncate_response_body(value: str) -> str:
    if len(value) <= RESPONSE_BODY_MAX_LEN:
        return value
    return f"{value[:RESPONSE_BODY_MAX_LEN]}...(truncated)"


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _ensure_sync_log_table(cur: Any) -> None:
    cur.execute("create schema if not exists metadata")
    cur.execute(
        """
        create table if not exists metadata.mixpanel_sync_log (
            insert_id text primary key,
            event_name text not null,
            distinct_id text,
            source_event_id text,
            event_time timestamp,
            export_table text not null,
            sync_status text not null,
            response_code integer,
            response_body text,
            synced_at timestamp default now()
        )
        """
    )


def _log_sync_rows(
    conn: Any,
    export_table: str,
    events_for_log: list[dict[str, Any]],
    sync_status: str,
    response_code: int | None,
    response_body: str,
) -> int:
    rows = []
    for event in events_for_log:
        properties = event["properties"]
        rows.append(
            (
                str(properties["$insert_id"]),
                str(event["event"]),
                str(properties.get("distinct_id")) if properties.get("distinct_id") is not None else None,
                str(properties.get("source_event_id")) if properties.get("source_event_id") is not None else None,
                datetime.fromtimestamp(int(properties["time"]), tz=timezone.utc).replace(tzinfo=None),
                export_table,
                sync_status,
                response_code,
                _truncate_response_body(response_body),
            )
        )

    cur = conn.cursor()
    cur.executemany(
        """
        insert into metadata.mixpanel_sync_log (
            insert_id,
            event_name,
            distinct_id,
            source_event_id,
            event_time,
            export_table,
            sync_status,
            response_code,
            response_body
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (insert_id) do update
        set
            event_name = excluded.event_name,
            distinct_id = excluded.distinct_id,
            source_event_id = excluded.source_event_id,
            event_time = excluded.event_time,
            export_table = excluded.export_table,
            sync_status = excluded.sync_status,
            response_code = excluded.response_code,
            response_body = excluded.response_body,
            synced_at = now()
        """,
        rows,
    )
    cur.close()
    return len(rows)


def main() -> int:
    try:
        neon_database_url = _require_env("NEON_DATABASE_URL")
        project_id = _require_env("MIXPANEL_PROJECT_ID")
        service_user = _require_env("MIXPANEL_SERVICE_ACCOUNT_USER")
        service_secret = _require_env("MIXPANEL_SERVICE_ACCOUNT_SECRET")
        region = _require_env("MIXPANEL_REGION")
        export_table = _validate_export_table(_require_env("MIXPANEL_EXPORT_TABLE"))
    except ValueError as exc:
        print(f"Mixpanel sync skipped: {exc}")
        print("No events sent.")
        return 1

    batch_size = int(os.getenv("MIXPANEL_BATCH_SIZE", "2000"))
    backfill_start_at = os.getenv("MIXPANEL_BACKFILL_START_AT", "2026-03-01 00:00:00")
    dry_run = os.getenv("MIXPANEL_DRY_RUN", "true").lower() in {"1", "true", "yes"}

    print(f"Export table: {export_table}")
    print(f"Batch size: {batch_size}")
    print(f"Backfill start at: {backfill_start_at}")
    print(f"Dry run: {dry_run}")

    conn = pg8000.dbapi.connect(ssl_context=True, **_parse_neon_url(neon_database_url))
    cur = conn.cursor()
    _ensure_sync_log_table(cur)
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
          and event_time >= %s::timestamp
          and event_time is not null
          and insert_id is not null
          and not exists (
              select 1
              from metadata.mixpanel_sync_log log
              where log.insert_id = {export_table}.insert_id
                and log.sync_status = 'success'
          )
        order by event_time asc
        limit %s
        """,
        (backfill_start_at, batch_size),
    )
    rows = cur.fetchall()
    cur.close()

    if not rows:
        print(f"No rows found in {export_table}; nothing to send.")
        conn.close()
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
        conn.close()
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

    response_code: int | None = None
    response_body = ""
    is_success = False

    try:
        with urlopen(request) as response:
            response_code = response.status
            response_body = response.read().decode("utf-8")
            is_success = response_code == 200
    except HTTPError as http_error:
        response_code = http_error.code
        response_body = http_error.read().decode("utf-8")
    except URLError as url_error:
        response_body = str(url_error)
    except Exception as exc:
        response_body = str(exc)

    print(f"Mixpanel response status: {response_code}")
    print(f"Mixpanel response body: {_truncate_response_body(response_body)}")

    status_label = "success" if is_success else "failed"
    logged_count = _log_sync_rows(
        conn=conn,
        export_table=export_table,
        events_for_log=events,
        sync_status=status_label,
        response_code=response_code,
        response_body=response_body,
    )
    conn.commit()
    conn.close()

    print(f"Logged {logged_count} event(s) with sync_status='{status_label}'.")
    if not is_success:
        print("Mixpanel import failed. See response details above.")
        return 1

    print(f"Successfully sent {len(events)} events to Mixpanel.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
