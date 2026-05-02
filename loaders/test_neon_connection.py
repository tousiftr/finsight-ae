import os
from pathlib import Path
from urllib.parse import unquote, urlparse

import pg8000.dbapi
from dotenv import load_dotenv


def connect_to_neon():
    database_url = os.getenv("NEON_DATABASE_URL")
    if not database_url:
        raise ValueError("Missing NEON_DATABASE_URL in .env")

    parsed = urlparse(database_url)

    return pg8000.dbapi.connect(
        user=unquote(parsed.username or ""),
        password=unquote(parsed.password or ""),
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=unquote(parsed.path.lstrip("/")),
        ssl_context=True,
    )


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    env_path = project_root / ".env"

    load_dotenv(env_path)

    conn = connect_to_neon()

    try:
        cur = conn.cursor()
        cur.execute("select current_database(), current_user, now();")
        row = cur.fetchone()
        cur.close()

        print("Connected to Neon successfully.")
        print(f"database={row[0]}")
        print(f"user={row[1]}")
        print(f"server_time={row[2]}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()