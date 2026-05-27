from __future__ import annotations

import os
from urllib.parse import unquote, urlparse

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


def main() -> int:
    neon_database_url = os.getenv("NEON_DATABASE_URL")
    if not neon_database_url:
        print("Missing required environment variable: NEON_DATABASE_URL")
        return 1

    conn = pg8000.dbapi.connect(ssl_context=True, **_parse_neon_url(neon_database_url))
    cur = conn.cursor()

    print("=== Sync status counts (event_time >= 2026-03-01) ===")
    cur.execute(
        """
        select sync_status, count(*)
        from metadata.mixpanel_sync_log
        where event_time >= %s::timestamp
        group by sync_status
        order by sync_status
        """,
        ("2026-03-01 00:00:00",),
    )
    for sync_status, cnt in cur.fetchall():
        print(f"{sync_status}: {cnt}")

    print("\n=== Success counts by event_name (event_time >= 2026-03-01) ===")
    cur.execute(
        """
        select event_name, count(*)
        from metadata.mixpanel_sync_log
        where sync_status = 'success'
          and event_time >= %s::timestamp
        group by event_name
        order by count(*) desc, event_name asc
        """,
        ("2026-03-01 00:00:00",),
    )
    for event_name, cnt in cur.fetchall():
        print(f"{event_name}: {cnt}")

    print("\n=== Success window summary (event_time >= 2026-03-01) ===")
    cur.execute(
        """
        select min(event_time), max(event_time), count(*)
        from metadata.mixpanel_sync_log
        where sync_status = 'success'
          and event_time >= %s::timestamp
        """,
        ("2026-03-01 00:00:00",),
    )
    min_event_time, max_event_time, total_count = cur.fetchone()
    print(f"min(event_time): {min_event_time}")
    print(f"max(event_time): {max_event_time}")
    print(f"count(*): {total_count}")

    cur.close()
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
