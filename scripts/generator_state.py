"""State lookup helpers for the live fintech data generator.

The raw Neon tables remain the source of truth for IDs and reusable customer,
account, and merchant relationships. These helpers intentionally use pg8000 via
scripts.raw_db.connect_to_neon and only read ingestion-owned raw tables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from raw_db import connect_to_neon


@dataclass(frozen=True)
class GeneratorState:
    """Existing raw-state snapshot used by one generator run."""

    neon_state_used: bool = False
    max_customer_number: int = 0
    max_account_number: int = 900000
    max_merchant_number: int = 0
    existing_customers: list[dict[str, Any]] = field(default_factory=list)
    existing_accounts: list[dict[str, Any]] = field(default_factory=list)
    existing_merchants: list[dict[str, Any]] = field(default_factory=list)
    state_message: str = "Running without Neon state; using fallback ID seeds."


def _scalar_int(conn, sql: str, fallback: int = 0) -> int:
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        row = cursor.fetchone()
        if not row or row[0] is None:
            return fallback
        return int(row[0])
    finally:
        cursor.close()


def get_max_customer_number(conn) -> int:
    """Return the largest numeric customer suffix from raw.raw_customers."""
    return _scalar_int(
        conn,
        """
        select coalesce(max(substring(coalesce(customer_id, payload ->> 'customer_id') from 2)::int), 0)
        from raw.raw_customers
        where coalesce(customer_id, payload ->> 'customer_id') ~ '^C[0-9]{5}$';
        """,
        fallback=0,
    )


def get_max_account_number(conn) -> int:
    """Return the largest numeric account suffix from raw.raw_accounts."""
    return _scalar_int(
        conn,
        """
        select coalesce(max(substring(payload ->> 'account_id' from 2)::int), 900000)
        from raw.raw_accounts
        where payload ->> 'account_id' ~ '^A[0-9]{6}$';
        """,
        fallback=900000,
    )


def get_max_merchant_number(conn) -> int:
    """Return the largest numeric merchant suffix from raw.raw_merchants."""
    return _scalar_int(
        conn,
        """
        select coalesce(max(substring(coalesce(merchant_id, payload ->> 'merchant_id') from 2)::int), 0)
        from raw.raw_merchants
        where coalesce(merchant_id, payload ->> 'merchant_id') ~ '^M[0-9]{6}$';
        """,
        fallback=0,
    )


def load_existing_customers(conn, limit: int = 5000) -> list[dict[str, Any]]:
    """Load recent distinct customers from raw payloads for live event reuse."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            with ranked as (
                select
                    payload ->> 'customer_id' as customer_id,
                    payload ->> 'country' as country,
                    payload ->> 'city' as city,
                    payload ->> 'kyc_status' as kyc_status,
                    payload,
                    row_number() over (
                        partition by payload ->> 'customer_id'
                        order by loaded_at desc, dt desc nulls last, batch_id desc nulls last
                    ) as rn
                from raw.raw_customers
                where payload ->> 'customer_id' ~ '^C[0-9]{5}$'
            )
            select customer_id, country, city, kyc_status, payload
            from ranked
            where rn = 1
            order by customer_id desc
            limit %s;
            """,
            (limit,),
        )
        return [
            {
                "customer_id": row[0],
                "country": row[1],
                "city": row[2],
                "kyc_status": row[3],
                **(row[4] if isinstance(row[4], dict) else {}),
            }
            for row in cursor.fetchall()
        ]
    finally:
        cursor.close()


def load_existing_accounts(conn, limit: int = 10000) -> list[dict[str, Any]]:
    """Load recent distinct accounts with customer relationships."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            with ranked as (
                select
                    payload ->> 'account_id' as account_id,
                    payload ->> 'customer_id' as customer_id,
                    payload ->> 'account_type' as account_type,
                    payload ->> 'currency' as currency,
                    payload,
                    row_number() over (
                        partition by payload ->> 'account_id'
                        order by loaded_at desc, dt desc, batch_id desc
                    ) as rn
                from raw.raw_accounts
                where payload ->> 'account_id' ~ '^A[0-9]{6}$'
                  and payload ->> 'customer_id' ~ '^C[0-9]{5}$'
            )
            select account_id, customer_id, account_type, currency, payload
            from ranked
            where rn = 1
              and exists (
                  select 1
                  from raw.raw_customers c
                  where c.payload ->> 'customer_id' = ranked.customer_id
              )
            order by account_id desc
            limit %s;
            """,
            (limit,),
        )
        return [
            {
                "account_id": row[0],
                "customer_id": row[1],
                "account_type": row[2],
                "currency": row[3],
                **(row[4] if isinstance(row[4], dict) else {}),
            }
            for row in cursor.fetchall()
        ]
    finally:
        cursor.close()


def load_existing_merchants(conn, limit: int = 1000) -> list[dict[str, Any]]:
    """Load recent distinct merchants for transaction enrichment."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            with ranked as (
                select
                    coalesce(merchant_id, payload ->> 'merchant_id') as merchant_id,
                    payload ->> 'merchant_name' as merchant_name,
                    payload ->> 'merchant_category' as merchant_category,
                    payload ->> 'merchant_country' as merchant_country,
                    payload ->> 'merchant_city' as merchant_city,
                    payload ->> 'risk_tier' as risk_tier,
                    payload,
                    row_number() over (
                        partition by coalesce(merchant_id, payload ->> 'merchant_id')
                        order by loaded_at desc, dt desc, batch_id desc
                    ) as rn
                from raw.raw_merchants
                where coalesce(merchant_id, payload ->> 'merchant_id') ~ '^M[0-9]{6}$'
            )
            select merchant_id, merchant_name, merchant_category, merchant_country, merchant_city, risk_tier, payload
            from ranked
            where rn = 1
            order by merchant_id desc
            limit %s;
            """,
            (limit,),
        )
        return [
            {
                "merchant_id": row[0],
                "merchant_name": row[1],
                "merchant_category": row[2],
                "merchant_country": row[3],
                "merchant_city": row[4],
                "risk_tier": row[5],
                **(row[6] if isinstance(row[6], dict) else {}),
            }
            for row in cursor.fetchall()
        ]
    finally:
        cursor.close()


def load_generator_state() -> GeneratorState:
    """Connect to Neon and return generator state, or safe fallback state offline."""
    try:
        conn = connect_to_neon()
    except Exception as exc:  # noqa: BLE001 - offline mode should tolerate any env/connectivity failure.
        return GeneratorState(state_message=f"Running without Neon state; using fallback ID seeds. Reason: {exc}")

    try:
        state = GeneratorState(
            neon_state_used=True,
            max_customer_number=get_max_customer_number(conn),
            max_account_number=get_max_account_number(conn),
            max_merchant_number=get_max_merchant_number(conn),
            existing_customers=load_existing_customers(conn),
            existing_accounts=load_existing_accounts(conn),
            existing_merchants=load_existing_merchants(conn),
            state_message="Loaded generator state from Neon raw tables.",
        )
        return state
    except Exception as exc:  # noqa: BLE001 - fall back rather than blocking local generation.
        return GeneratorState(state_message=f"Running without Neon state; raw-state lookup failed. Reason: {exc}")
    finally:
        conn.close()
