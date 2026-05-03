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


def scalar(cursor, sql: str, params: tuple):
    cursor.execute(sql, params)
    return cursor.fetchone()[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-id", required=True)
    args = parser.parse_args()

    conn = get_neon_connection()
    try:
        c = conn.cursor()
        bid = args.batch_id
        accounts_count = scalar(c, "select count(*) from raw.raw_accounts where batch_id = %s;", (bid,))
        transactions_count = scalar(c, "select count(*) from raw.raw_transactions where batch_id = %s;", (bid,))
        accounts_without_customer = scalar(c, """
            select count(*)
            from raw.raw_accounts a
            left join raw.raw_customers c
              on (a.payload->>'customer_id') = (c.payload->>'customer_id')
             and c.batch_id = a.batch_id
            where a.batch_id = %s and c.id is null;
        """, (bid,))
        transactions_without_account = scalar(c, """
            select count(*)
            from raw.raw_transactions t
            left join raw.raw_accounts a
              on (t.payload->>'account_id') = (a.payload->>'account_id')
             and a.batch_id = t.batch_id
            where t.batch_id = %s and a.id is null;
        """, (bid,))
        transaction_customer_mismatch = scalar(c, """
            select count(*)
            from raw.raw_transactions t
            join raw.raw_accounts a
              on (t.payload->>'account_id') = (a.payload->>'account_id')
             and a.batch_id = t.batch_id
            where t.batch_id = %s
              and (t.payload->>'customer_id') <> (a.payload->>'customer_id');
        """, (bid,))

        print(f"validation counts: accounts_count={accounts_count}, transactions_count={transactions_count}, accounts_without_customer={accounts_without_customer}, transactions_without_account={transactions_without_account}, transaction_customer_mismatch={transaction_customer_mismatch}")

        if accounts_count <= 0:
            raise RuntimeError("accounts count must be > 0")
        if transactions_count <= 0:
            raise RuntimeError("transactions count must be > 0")
        if accounts_without_customer != 0 or transactions_without_account != 0 or transaction_customer_mismatch != 0:
            raise RuntimeError("referential integrity checks failed")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
