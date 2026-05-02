import os
import ssl
from pathlib import Path
from urllib.parse import unquote, urlparse

import pg8000.dbapi
from dotenv import load_dotenv


def load_project_env() -> None:
    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env", override=True)
    load_dotenv(override=False)


def get_neon_connection():
    database_url = os.getenv("DATABASE_URL") or os.getenv("NEON_DATABASE_URL")

    if database_url:
        parsed = urlparse(database_url)

        return pg8000.dbapi.connect(
            user=unquote(parsed.username or ""),
            password=unquote(parsed.password or ""),
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=unquote(parsed.path.lstrip("/")),
            ssl_context=ssl.create_default_context(),
        )

    return pg8000.dbapi.connect(
        user=os.getenv("PGUSER") or os.getenv("POSTGRES_USER"),
        password=os.getenv("PGPASSWORD") or os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("PGHOST") or os.getenv("POSTGRES_HOST"),
        port=int(os.getenv("PGPORT") or 5432),
        database=os.getenv("PGDATABASE") or os.getenv("POSTGRES_DB"),
        ssl_context=ssl.create_default_context(),
    )


def fetch_all(cursor, sql: str):
    cursor.execute(sql)
    return cursor.fetchall()


def print_table(rows, headers):
    widths = [len(header) for header in headers]

    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(str(value)))

    header_line = "  ".join(
        header.ljust(widths[index]) for index, header in enumerate(headers)
    )
    separator_line = "  ".join("-" * width for width in widths)

    print(header_line)
    print(separator_line)

    for row in rows:
        print(
            "  ".join(
                str(value).ljust(widths[index]) for index, value in enumerate(row)
            )
        )


def main() -> None:
    load_project_env()
    conn = get_neon_connection()

    try:
        cursor = conn.cursor()

        counts = fetch_all(
            cursor,
            """
            select 'raw_accounts' as table_name, count(*) as row_count
            from raw.raw_accounts

            union all

            select 'raw_transactions' as table_name, count(*) as row_count
            from raw.raw_transactions

            order by table_name;
            """,
        )

        print("\nRaw table counts")
        print("----------------")
        print_table(counts, ["table_name", "row_count"])

        batches = fetch_all(
            cursor,
            """
            select 'accounts' as entity, dt, batch_id, source_object_key, count(*) as row_count
            from raw.raw_accounts
            group by dt, batch_id, source_object_key

            union all

            select 'transactions' as entity, dt, batch_id, source_object_key, count(*) as row_count
            from raw.raw_transactions
            group by dt, batch_id, source_object_key

            order by dt desc nulls last, batch_id desc nulls last, entity
            limit 20;
            """,
        )

        print("\nLatest account and transaction batches")
        print("---------------------------------------")
        if batches:
            print_table(
                batches,
                ["entity", "dt", "batch_id", "source_object_key", "row_count"],
            )
        else:
            print("No account or transaction batches loaded yet.")

        cursor.close()

    finally:
        conn.close()


if __name__ == "__main__":
    main()
