# Prueba conexion SQL Server leyendo .env (Windows / produccion).
# Uso: .\.venv\Scripts\python.exe scripts\test_db_connection.py

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pymssql  # noqa: E402

from app.config import get_settings  # noqa: E402


def _attempt(label: str, **connect_kwargs) -> bool:
    try:
        conn = pymssql.connect(**connect_kwargs)
        conn.close()
        print(f"OK  {label}")
        return True
    except Exception as exc:
        print(f"FAIL {label}: {exc}")
        return False


def main() -> int:
    s = get_settings()
    base = {
        "user": s.db_username,
        "password": s.db_password,
        "database": s.db_database,
        "login_timeout": 10,
        "timeout": 30,
    }
    host = s.db_host
    port = s.db_port

    print(f"Host={host} Port={port} User={s.db_username} DB={s.db_database}")
    print(f"TDS={s.db_tds_version or '(default)'} Encryption={s.db_encryption or '(default)'}")
    print("---")

    variants = [
        ("separate host+port (env tds/enc)", {**base, "server": host, "port": port,
         **({"tds_version": s.db_tds_version} if s.db_tds_version else {}),
         **({"encryption": s.db_encryption} if s.db_encryption else {})}),
        ("host+port tds=7.0 enc=off", {**base, "server": host, "port": port,
         "tds_version": "7.0", "encryption": "off"}),
        ("host+port tds=7.4 enc=off", {**base, "server": host, "port": port,
         "tds_version": "7.4", "encryption": "off"}),
        (f"server={host},{port} tds=7.0 enc=off", {**base, "server": f"{host},{port}",
         "tds_version": "7.0", "encryption": "off"}),
    ]

    for label, kwargs in variants:
        if _attempt(label, **kwargs):
            print("\nUsa en .env los parametros de la variante que funciono.")
            return 0

    print("\nNinguna variante conecto. Verifica SSMS con las mismas credenciales.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
