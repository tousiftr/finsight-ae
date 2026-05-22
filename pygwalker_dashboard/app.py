import os
import ssl
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from pygwalker.api.streamlit import StreamlitRenderer
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
SPECS_DIR = BASE_DIR / "specs"

SPECS_DIR.mkdir(exist_ok=True)

# Support both:
# 1. finsight-analytics-engineering/.env
# 2. finsight-analytics-engineering/pygwalker_dashboard/.env
load_dotenv(PROJECT_DIR / ".env")
load_dotenv(BASE_DIR / ".env")


def get_database_url() -> URL:
    database_url = (
        os.getenv("NEON_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or os.getenv("DB_URL")
    )

    if not database_url:
        raise ValueError(
            "Missing database connection string. "
            "Set NEON_DATABASE_URL or DATABASE_URL in .env"
        )

    parsed = urlsplit(database_url)

    username = unquote(parsed.username or "")
    password = unquote(parsed.password or "")
    host = parsed.hostname
    port = parsed.port or 5432

    # Important:
    # Neon URL may contain /FinSight%20Analytics.
    # pg8000 needs the decoded database name: FinSight Analytics.
    database = unquote(parsed.path.lstrip("/"))

    if not host:
        raise ValueError("Database host is missing from NEON_DATABASE_URL.")

    if not database:
        raise ValueError("Database name is missing from NEON_DATABASE_URL.")

    return URL.create(
        drivername="postgresql+pg8000",
        username=username,
        password=password,
        host=host,
        port=port,
        database=database,
    )


def get_engine():
    return create_engine(
        get_database_url(),
        pool_pre_ping=True,
        connect_args={
            "ssl_context": ssl.create_default_context(),
        },
    )


@st.cache_data(ttl=300, show_spinner=False)
def get_connection_info() -> dict:
    engine = get_engine()

    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                select
                    current_database() as database_name,
                    current_user as database_user,
                    current_schema() as current_schema,
                    current_setting('search_path') as search_path
                """
            )
        ).mappings().fetchone()

    return dict(row)


@st.cache_data(ttl=300, show_spinner=False)
def get_dbt_fs_objects() -> pd.DataFrame:
    engine = get_engine()

    query = text(
        """
        select
            n.nspname as table_schema,
            c.relname as table_name,
            case c.relkind
                when 'r' then 'TABLE'
                when 'v' then 'VIEW'
                when 'm' then 'MATERIALIZED VIEW'
                when 'p' then 'PARTITIONED TABLE'
                else c.relkind::text
            end as table_type
        from pg_catalog.pg_class c
        join pg_catalog.pg_namespace n
            on n.oid = c.relnamespace
        where n.nspname = 'dbt_fs'
          and c.relkind in ('r', 'v', 'm', 'p')
        order by c.relname
        """
    )

    with engine.connect() as conn:
        return pd.read_sql(query, conn)


@st.cache_data(ttl=900, show_spinner=True)
def load_selected_table(table_name: str, row_limit: int) -> pd.DataFrame:
    objects_df = get_dbt_fs_objects()
    allowed_tables = objects_df["table_name"].tolist()

    if table_name not in allowed_tables:
        raise ValueError(
            f"Selected table/view '{table_name}' does not exist in dbt_fs."
        )

    if not table_name.replace("_", "").isalnum():
        raise ValueError(f"Invalid table name: {table_name}")

    row_limit = int(row_limit)

    query = text(
        f"""
        select *
        from "dbt_fs"."{table_name}"
        limit {row_limit}
        """
    )

    engine = get_engine()

    with engine.connect() as conn:
        return pd.read_sql(query, conn)


def main() -> None:
    st.set_page_config(
        page_title="FinSight PyGWalker Dashboard",
        page_icon="📊",
        layout="wide",
    )

    st.title("FinSight PyGWalker Dashboard")
    st.caption("Database-connected PyGWalker explorer for real dbt_fs tables/views.")

    st.sidebar.title("FinSight Explorer")

    refresh_clicked = st.sidebar.button("Refresh from Neon")

    if refresh_clicked:
        st.cache_data.clear()
        st.sidebar.success("Cache cleared. Reloading from Neon.")

    try:
        conn_info = get_connection_info()

        st.sidebar.success("Database connected")
        st.sidebar.caption(f"Database: {conn_info['database_name']}")
        st.sidebar.caption(f"User: {conn_info['database_user']}")
        st.sidebar.caption(f"Current schema: {conn_info['current_schema']}")
        st.sidebar.caption(f"Search path: {conn_info['search_path']}")

        objects_df = get_dbt_fs_objects()

        st.subheader("All objects found in dbt_fs")
        st.dataframe(objects_df, use_container_width=True)

        if objects_df.empty:
            st.error("No tables or views found in schema dbt_fs from this connection.")
            st.write(
                "This means your .env Neon URL is connected to a database or branch "
                "where schema dbt_fs has no objects."
            )
            return

        only_mrt = st.sidebar.checkbox(
            "Show only mrt tables/views",
            value=True,
        )

        selectable_df = objects_df.copy()

        if only_mrt:
            selectable_df = selectable_df[
                selectable_df["table_name"].str.startswith("mrt")
            ]

        if selectable_df.empty:
            st.warning(
                "dbt_fs exists, but no mrt tables/views were found. "
                "Uncheck 'Show only mrt tables/views' to select any dbt_fs table."
            )
            selectable_df = objects_df.copy()

        table_names = selectable_df["table_name"].tolist()

        selected_table = st.sidebar.selectbox(
            "Select table/view",
            table_names,
        )

        row_limit = st.sidebar.number_input(
            "Row limit",
            min_value=100,
            max_value=100000,
            value=50000,
            step=1000,
        )

        st.divider()

        df = load_selected_table(selected_table, row_limit)

        st.subheader(f"dbt_fs.{selected_table}")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Rows loaded", f"{len(df):,}")

        with col2:
            st.metric("Columns", f"{len(df.columns):,}")

        with col3:
            object_type = selectable_df.loc[
                selectable_df["table_name"] == selected_table,
                "table_type",
            ].iloc[0]
            st.metric("Object type", object_type)

        if df.empty:
            st.warning("Selected table/view returned zero rows.")
            return

        with st.expander("Preview first 50 rows", expanded=True):
            st.dataframe(df.head(50), use_container_width=True)

        with st.expander("Column list", expanded=False):
            st.write(list(df.columns))

        st.divider()

        st.subheader("PyGWalker Explorer")
        st.caption("Drag fields to build charts from the selected dbt_fs table/view.")

        spec_path = str(SPECS_DIR / f"{selected_table}.json")

        renderer = StreamlitRenderer(
            df,
            spec=spec_path,
            spec_io_mode="rw",
        )

        renderer.explorer()

    except Exception as exc:
        st.error("Dashboard failed to load.")
        st.write(
            "This app only connects to Neon and reads actual dbt_fs objects. "
            "It does not use fake tables or dbt profile settings."
        )
        st.exception(exc)


if __name__ == "__main__":
    main()