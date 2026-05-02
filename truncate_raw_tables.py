import os
from urllib.parse import urlparse, unquote

from dotenv import load_dotenv
import pg8000.dbapi

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

    cur.execute("""
        truncate table
            raw.raw_transactions,
            raw.raw_accounts,
            raw.raw_customers
        restart identity;
    """)

    conn.commit()

    print("Raw customer/account/transaction tables truncated.")

finally:
    conn.close()