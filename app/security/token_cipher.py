import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken


_PREFIX = "enc:v1:"


def _derive_key() -> bytes:
    from app.config import get_settings

    raw = get_settings().integration_token_key.strip()
    if not raw:
        raw = os.environ.get("APP_SECRET", "").strip()
    if not raw:
        raise RuntimeError(
            "Define INTEGRATION_TOKEN_KEY en el entorno para cifrar tokens de integración"
        )
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _fernet() -> Fernet:
    return Fernet(_derive_key())


def is_encrypted(value: str | None) -> bool:
    return bool(value and str(value).startswith(_PREFIX))


def encrypt_token(plain: str) -> str:
    token = plain.strip()
    if not token:
        return ""
    return _PREFIX + _fernet().encrypt(token.encode("utf-8")).decode("ascii")


def decrypt_token(stored: str | None) -> str:
    if not stored:
        return ""
    value = stored.strip()
    if not value:
        return ""
    if not is_encrypted(value):
        return value
    payload = value[len(_PREFIX) :]
    try:
        return _fernet().decrypt(payload.encode("ascii")).decode("utf-8")
    except InvalidToken:
        # Clave distinta o datos corruptos: no tumbar login; reingresar token en Ajustes.
        return ""


def token_fingerprint(plain: str) -> str:
    token = plain.strip()
    if not token:
        return ""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
