import pymssql

from app.config import get_settings


def get_connection() -> pymssql.Connection:
    settings = get_settings()
    server = settings.db_host
    if settings.db_port:
        server = f"{settings.db_host},{settings.db_port}"

    kwargs: dict = {
        "server": server,
        "user": settings.db_username,
        "password": settings.db_password,
        "database": settings.db_database,
        "login_timeout": 10,
        "timeout": 30,
    }
    if settings.db_tds_version:
        kwargs["tds_version"] = settings.db_tds_version
    if settings.db_encryption:
        kwargs["encryption"] = settings.db_encryption

    return pymssql.connect(**kwargs)
