import os
import ssl
from urllib.parse import urlparse, unquote  

import pg8000.dbapi
from dotenv import load_dotenv


load_dotenv()

def get_neon_connection():
    database_url = os.getenv("DATABASE_URL") or os.getenv("NEON_DATABASE_URL")

    if database_url:
        parsed = urlparse(database_url)

        return pg8000.dbapi.connect(
            user=unquote(parsed.username),
            password=unquote(parsed.password),
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


def fetch_one(cursor, sql):
    cursor.execute(sql)
    return cursor.fetchone()


def fetch_all(cursor, sql):
    cursor.execute(sql)
    return cursor.fetchall()


def main():
    conn = get_neon_connection()

    try:
        cursor = conn.cursor()

        total_rows = fetch_one(
            cursor,
            """
            select count(*) as total_rows
            from raw.raw_customers;
            """,
        )

        latest_batches = fetch_all(
            cursor,
            """
            select
                dt,
                batch_id,
                source_object_key,
                count(*) as row_count,
                count(distinct raw_record_hash) as distinct_raw_record_hashes
            from raw.raw_customers
            group by
                dt,
                batch_id,
                source_object_key
            order by
                dt desc,
                batch_id desc
            limit 5;
            """,
        )

        sample_payload = fetch_one(
            cursor,
            """
            select payload
            from raw.raw_customers
            order by
                dt desc,
                batch_id desc
            limit 1;
            """,
        )

        print("\nraw.raw_customers verification")
        print("--------------------------------")
        print(f"Total rows: {total_rows[0]}")

        print("\nLatest loaded batches:")
        for row in latest_batches:
            print(
                {
                    "dt": row[0],
                    "batch_id": row[1],
                    "source_object_key": row[2],
                    "row_count": row[3],
                    "distinct_raw_record_hashes": row[4],
                }
            )

        print("\nSample payload:")
        print(sample_payload[0] if sample_payload else None)

    finally:
        conn.close()


if __name__ == "__main__":
    main()