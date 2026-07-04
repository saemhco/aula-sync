import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any

import bcrypt

from app.db.settings_db import _connect, _db_path


def init_auth_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS app_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS app_sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES app_users(id) ON DELETE CASCADE
            );
            """
        )
        count = conn.execute("SELECT COUNT(*) FROM app_users").fetchone()[0]
        if count == 0:
            from app.config import get_settings

            settings = get_settings()
            username = settings.app_admin_username.strip()
            password = settings.app_admin_password.strip()
            if username and password:
                conn.execute(
                    """
                    INSERT INTO app_users (username, password_hash)
                    VALUES (?, ?)
                    """,
                    (username, _hash_password(password)),
                )


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        return False


def _hash_session_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash FROM app_users WHERE username = ? COLLATE NOCASE",
            (username.strip(),),
        ).fetchone()
        if not row or not _verify_password(password, row["password_hash"]):
            return None
        return {"id": row["id"], "username": row["username"]}


def create_session(user_id: int, *, hours: int = 8) -> str:
    token = f"sess_{secrets.token_urlsafe(48)}"
    expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO app_sessions (token_hash, user_id, expires_at)
            VALUES (?, ?, ?)
            """,
            (_hash_session_token(token), user_id, expires_at.isoformat()),
        )
    return token


def validate_session(token: str) -> dict[str, Any] | None:
    token = token.strip()
    if not token:
        return None

    token_hash = _hash_session_token(token)
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT s.user_id, s.expires_at, u.username
            FROM app_sessions s
            JOIN app_users u ON u.id = s.user_id
            WHERE s.token_hash = ?
            """,
            (token_hash,),
        ).fetchone()
        if not row:
            return None

        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            conn.execute("DELETE FROM app_sessions WHERE token_hash = ?", (token_hash,))
            return None

        return {"id": row["user_id"], "username": row["username"]}


def revoke_session(token: str) -> None:
    token_hash = _hash_session_token(token.strip())
    with _connect() as conn:
        conn.execute("DELETE FROM app_sessions WHERE token_hash = ?", (token_hash,))


def update_credentials(
    user_id: int,
    current_password: str,
    *,
    new_username: str | None = None,
    new_password: str | None = None,
) -> dict[str, Any]:
    new_username = (new_username or "").strip()
    new_password = (new_password or "").strip()

    if not new_username and not new_password:
        raise ValueError("Indica un nuevo usuario o contraseña")

    with _connect() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash FROM app_users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            raise ValueError("Usuario no encontrado")
        if not _verify_password(current_password, row["password_hash"]):
            raise ValueError("Contraseña actual incorrecta")

        target_username = new_username or row["username"]
        if new_username and new_username.lower() != row["username"].lower():
            exists = conn.execute(
                "SELECT id FROM app_users WHERE username = ? COLLATE NOCASE AND id != ?",
                (new_username, user_id),
            ).fetchone()
            if exists:
                raise ValueError("Ese nombre de usuario ya está en uso")

        password_hash = _hash_password(new_password) if new_password else row["password_hash"]
        conn.execute(
            "UPDATE app_users SET username = ?, password_hash = ? WHERE id = ?",
            (target_username, password_hash, user_id),
        )

    return {"id": user_id, "username": target_username}
