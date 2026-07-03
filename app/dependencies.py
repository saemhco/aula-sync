from fastapi import Depends, Header, HTTPException

from app.config import get_runtime_config
from app.db import auth_db


def require_configured() -> dict:
    config = get_runtime_config()
    if not config["configured"]:
        raise HTTPException(
            status_code=412,
            detail="Configura origen y destino Moodle en Ajustes antes de continuar",
        )
    return config


def get_current_user(
    x_session_token: str = Header(..., alias="X-Session-Token"),
) -> dict:
    user = auth_db.validate_session(x_session_token)
    if not user:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
    return user


def get_runtime_context(
    _: dict = Depends(get_current_user),
    config: dict = Depends(require_configured),
) -> dict:
    return config


def require_session(
    _: dict = Depends(get_current_user),
) -> dict:
    return _


def integration_token_from_context(ctx: dict) -> str:
    token = (ctx.get("integration_token") or "").strip()
    if not token:
        raise HTTPException(
            status_code=502,
            detail="No hay token de integración configurado para el destino Moodle",
        )
    return token
