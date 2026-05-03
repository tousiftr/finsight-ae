import argparse
import os
import ssl
from urllib.parse import unquote, urlparse

import pg8000.dbapi
from dotenv import load_dotenv


load_dotenv()


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
    raise RuntimeError("Missing DATABASE_URL or NEON_DATABASE_URL")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-id", required=True)
    args = parser.parse_args()

    conn = get_neon_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("select count(*) from raw.raw_customers where batch_id = %s;", (args.batch_id,))
        customers_count = cursor.fetchone()[0]
        print(f"validation counts: customers_count={customers_count}")
        if customers_count <= 0:
            raise RuntimeError(f"customers count must be > 0 for batch_id={args.batch_id}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
