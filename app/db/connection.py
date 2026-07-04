import pymssql

from app.config import get_settings


def get_connection() -> pymssql.Connection:
    settings = get_settings()
    kwargs: dict = {
        "server": settings.db_host,
        "user": settings.db_username,
        "password": settings.db_password,
        "database": settings.db_database,
        "login_timeout": 10,
        "timeout": 30,
    }
    if settings.db_port:
        kwargs["port"] = settings.db_port
    if settings.db_tds_version:
        kwargs["tds_version"] = settings.db_tds_version
    if settings.db_encryption:
        kwargs["encryption"] = settings.db_encryption

    return pymssql.connect(**kwargs)


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
