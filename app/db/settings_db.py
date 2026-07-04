import sqlite3
from pathlib import Path
from typing import Any

from app.security.token_cipher import decrypt_token, encrypt_token, is_encrypted

_SCHEMA = """
CREATE TABLE IF NOT EXISTS moodle_destinations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    moodle_url TEXT NOT NULL,
    moodle_public_url TEXT NOT NULL,
    integration_token TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS app_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS migration_log (
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    destination_id INTEGER NOT NULL,
    origin_key TEXT NOT NULL,
    migrated_at TEXT NOT NULL,
    PRIMARY KEY (entity_type, entity_id, destination_id, origin_key)
);
"""


def _db_path() -> Path:
    from app.config import get_settings

    configured = get_settings().settings_db_path.strip()
    path = Path(configured) if configured else Path("/app/data/settings.db")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(_SCHEMA)
        _ensure_destination_columns(conn)
        _migrate_plain_tokens(conn)
        count = conn.execute("SELECT COUNT(*) FROM moodle_destinations").fetchone()[0]
        if count == 0:
            from app.config import get_settings

            settings = get_settings()
            moodle_url = settings.moodle_url.strip()
            moodle_public_url = settings.moodle_public_url.strip()
            if moodle_url and moodle_public_url:
                conn.execute(
                    """
                    INSERT INTO moodle_destinations (name, moodle_url, moodle_public_url)
                    VALUES (?, ?, ?)
                    """,
                    (
                        "Moodle local",
                        moodle_url.rstrip("/"),
                        moodle_public_url.rstrip("/"),
                    ),
                )


def _get_config(key: str) -> str | None:
    with _connect() as conn:
        row = conn.execute("SELECT value FROM app_config WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None


def _set_config(key: str, value: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO app_config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


def _ensure_destination_columns(conn: sqlite3.Connection) -> None:
    columns = {
        row["name"] for row in conn.execute("PRAGMA table_info(moodle_destinations)").fetchall()
    }
    if "integration_token" not in columns:
        conn.execute(
            "ALTER TABLE moodle_destinations ADD COLUMN integration_token TEXT NOT NULL DEFAULT ''"
        )


def _migrate_plain_tokens(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT id, integration_token FROM moodle_destinations WHERE integration_token != ''"
    ).fetchall()
    for row in rows:
        stored = row["integration_token"] or ""
        if is_encrypted(stored):
            continue
        conn.execute(
            "UPDATE moodle_destinations SET integration_token = ? WHERE id = ?",
            (encrypt_token(stored), row["id"]),
        )


def destination_for_api(data: dict[str, Any]) -> dict[str, Any]:
    stored = (data.get("integration_token") or "").strip()
    return {
        "id": data["id"],
        "name": data["name"],
        "moodle_url": data["moodle_url"],
        "moodle_public_url": data["moodle_public_url"],
        "created_at": data["created_at"],
        "has_integration_token": bool(stored),
    }


def destination_with_plain_token(data: dict[str, Any]) -> dict[str, Any]:
    result = dict(data)
    stored = (result.get("integration_token") or "").strip()
    result["integration_token"] = decrypt_token(stored) if stored else ""
    return result


def list_destinations() -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, name, moodle_url, moodle_public_url, integration_token, created_at
            FROM moodle_destinations ORDER BY id
            """
        ).fetchall()
        return [destination_for_api(dict(row)) for row in rows]


def _fetch_destination_row(dest_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT id, name, moodle_url, moodle_public_url, integration_token, created_at
            FROM moodle_destinations WHERE id = ?
            """,
            (dest_id,),
        ).fetchone()
        return dict(row) if row else None


def get_destination(dest_id: int) -> dict[str, Any] | None:
    row = _fetch_destination_row(dest_id)
    return destination_with_plain_token(row) if row else None


def get_destination_public(dest_id: int) -> dict[str, Any] | None:
    row = _fetch_destination_row(dest_id)
    return destination_for_api(row) if row else None


def create_destination(
    name: str,
    moodle_url: str,
    moodle_public_url: str,
    integration_token: str,
) -> dict[str, Any]:
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO moodle_destinations (name, moodle_url, moodle_public_url, integration_token)
            VALUES (?, ?, ?, ?)
            """,
            (
                name.strip(),
                moodle_url.rstrip("/"),
                moodle_public_url.rstrip("/"),
                encrypt_token(integration_token),
            ),
        )
        dest_id = cur.lastrowid
    row = _fetch_destination_row(dest_id)
    assert row is not None
    return destination_for_api(row)


def update_destination(
    dest_id: int,
    name: str,
    moodle_url: str,
    moodle_public_url: str,
    integration_token: str | None = None,
) -> dict[str, Any] | None:
    if get_destination(dest_id) is None:
        return None

    token_value = integration_token.strip() if integration_token is not None else None
    with _connect() as conn:
        if token_value is not None:
            conn.execute(
                """
                UPDATE moodle_destinations
                SET name = ?, moodle_url = ?, moodle_public_url = ?, integration_token = ?
                WHERE id = ?
                """,
                (
                    name.strip(),
                    moodle_url.rstrip("/"),
                    moodle_public_url.rstrip("/"),
                    encrypt_token(token_value),
                    dest_id,
                ),
            )
        else:
            conn.execute(
                """
                UPDATE moodle_destinations
                SET name = ?, moodle_url = ?, moodle_public_url = ?
                WHERE id = ?
                """,
                (
                    name.strip(),
                    moodle_url.rstrip("/"),
                    moodle_public_url.rstrip("/"),
                    dest_id,
                ),
            )
    row = _fetch_destination_row(dest_id)
    return destination_for_api(row) if row else None


def update_destination_token(dest_id: int, integration_token: str) -> dict[str, Any] | None:
    existing = get_destination(dest_id)
    if existing is None:
        return None
    return update_destination(
        dest_id,
        existing["name"],
        existing["moodle_url"],
        existing["moodle_public_url"],
        integration_token=integration_token,
    )


def delete_destination(dest_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM moodle_destinations WHERE id = ?", (dest_id,))
        if cur.rowcount == 0:
            return False
        row = conn.execute(
            "SELECT value FROM app_config WHERE key = 'active_destination_id'"
        ).fetchone()
        if row and row["value"] == str(dest_id):
            conn.execute(
                "DELETE FROM app_config WHERE key IN "
                "('active_destination_id', 'active_origin', 'active_anio', 'active_semestre')"
            )
    return True


def get_active_selection() -> dict[str, Any]:
    origin_key = _get_config("active_origin")
    dest_raw = _get_config("active_destination_id")
    destination = (
        destination_with_plain_token(raw)
        if (raw := _fetch_destination_row(int(dest_raw)))
        else None
    )
    return {
        "origin_key": origin_key,
        "destination_id": int(dest_raw) if dest_raw else None,
        "destination": destination,
        "active_anio": _get_config("active_anio"),
        "active_semestre": _get_config("active_semestre"),
    }


def set_active(origin_key: str, destination_id: int, anio: str, semestre: str) -> dict[str, Any]:
    if get_destination(destination_id) is None:
        raise ValueError("Destino Moodle no encontrado")
    _set_config("active_origin", origin_key)
    _set_config("active_destination_id", str(destination_id))
    _set_config("active_anio", anio)
    _set_config("active_semestre", semestre)
    return get_active_selection()


def is_configured() -> bool:
    selection = get_active_selection()
    from app.origins import get_origin

    return bool(
        selection["origin_key"]
        and selection["destination_id"]
        and selection["active_anio"]
        and selection["active_semestre"]
        and get_origin(selection["origin_key"])
        and selection["destination"]
    )


def record_user_migration(usuario: str, destination_id: int, origin_key: str) -> str:
    entity_id = usuario.strip()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO migration_log (entity_type, entity_id, destination_id, origin_key, migrated_at)
            VALUES ('user', ?, ?, ?, datetime('now'))
            ON CONFLICT(entity_type, entity_id, destination_id, origin_key)
            DO UPDATE SET migrated_at = excluded.migrated_at
            """,
            (entity_id, destination_id, origin_key),
        )
        row = conn.execute(
            """
            SELECT migrated_at FROM migration_log
            WHERE entity_type = 'user' AND entity_id = ? AND destination_id = ? AND origin_key = ?
            """,
            (entity_id, destination_id, origin_key),
        ).fetchone()
    assert row is not None
    return row["migrated_at"]


def get_user_migrations(
    destination_id: int,
    origin_key: str,
    entity_ids: list[str],
) -> dict[str, str]:
    cleaned = sorted({entity_id.strip() for entity_id in entity_ids if entity_id and entity_id.strip()})
    if not cleaned:
        return {}

    placeholders = ",".join("?" * len(cleaned))
    with _connect() as conn:
        rows = conn.execute(
            f"""
            SELECT entity_id, migrated_at FROM migration_log
            WHERE entity_type = 'user' AND destination_id = ? AND origin_key = ?
              AND entity_id IN ({placeholders})
            """,
            (destination_id, origin_key, *cleaned),
        ).fetchall()
    return {row["entity_id"]: row["migrated_at"] for row in rows}
