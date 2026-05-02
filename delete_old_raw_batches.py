import os
from urllib.parse import urlparse, unquote

from dotenv import load_dotenv
import pg8000.dbapi

KEEP_BATCH_ID = "20260502_1436"

load_dotenv()

database_url = os.getenv("DATABASE_URL") or os.getenv("NEON_DATABASE_URL")

if not database_url:
    raise SystemExit("DATABASE_URL or NEON_DATABASE_URL is not set.")

parsed = urlparse(database_url)

conn = pg8000.dbapi.connect(
    user=unquote(parsed.username or ""),
    password=unquote(parsed.password or ""),
    host=parsed.hostname,
    port=parsed.port or 5432,
    database=unquote(parsed.path.lstrip("/")),
    ssl_context=True,
)

try:
    cur = conn.cursor()

    print(f"Deleting old raw batches. Keeping only batch_id={KEEP_BATCH_ID}")

    # Delete child-like tables first.
    tables = [
        "raw.raw_transactions",
        "raw.raw_accounts",
        "raw.raw_customers",
    ]

    for table in tables:
        cur.execute(
            f"""
            delete from {table}
            where batch_id <> %s
               or batch_id is null;
            """,
            (KEEP_BATCH_ID,),
        )
        print(f"{table}: deleted {cur.rowcount} old rows")

    conn.commit()

    print("\nRemaining row counts:")
    for table in reversed(tables):
        cur.execute(
            f"""
            select batch_id, count(*)
            from {table}
            group by batch_id
            order by batch_id;
            """
        )
        print(f"\n{table}")
        for row in cur.fetchall():
            print(row)

finally:
    conn.close()