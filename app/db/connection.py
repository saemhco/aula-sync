import pymssql

from app.config import get_settings


def get_connection() -> pymssql.Connection:
    settings = get_settings()
    return pymssql.connect(
        server=settings.db_host,
        port=settings.db_port,
        user=settings.db_username,
        password=settings.db_password,
        database=settings.db_database,
        login_timeout=10,
        timeout=30,
    )


def fetch_all(query: str, params: tuple = ()) -> list[dict]:
    conn = get_connection()
    try:
        cursor = conn.cursor(as_dict=True)
        cursor.execute(query, params)
        return list(cursor.fetchall())
    finally:
        conn.close()


def fetch_one(query: str, params: tuple = ()) -> dict | None:
    rows = fetch_all(query, params)
    return rows[0] if rows else None
