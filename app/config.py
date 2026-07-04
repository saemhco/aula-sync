from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.db import settings_db
from app.origins import OriginProfile, get_origin


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    db_host: str = "sqlserver"
    db_port: int = 1433  # red interna Docker; en host/Windows usar 11433
    db_database: str = "DB_UNHEVAL"
    db_username: str = ""
    db_password: str = ""

    moodle_url: str = "http://host.docker.internal:8046"
    moodle_public_url: str = "http://localhost:8046"
    settings_db_path: str = "/app/data/settings.db"
    integration_token_key: str = ""
    aula_sync_public_url: str = "http://localhost:8092"
    app_admin_username: str = "admin"
    app_admin_password: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_runtime_config() -> dict:
    selection = settings_db.get_active_selection()
    origin = get_origin(selection["origin_key"]) if selection["origin_key"] else None
    destination = selection["destination"]

    if not origin or not destination or not selection["active_anio"] or not selection["active_semestre"]:
        return {"configured": False, "origin": None, "destination": None}

    return {
        "configured": True,
        "origin": origin,
        "destination": destination,
        "server": origin.key,
        "url": destination["moodle_url"].rstrip("/"),
        "public_url": destination["moodle_public_url"].rstrip("/"),
        "integration_token": (destination.get("integration_token") or "").strip(),
        "aula_sync_origin": get_settings().aula_sync_public_url.rstrip("/"),
        "area": origin.area,
        "id_gen": origin.id_gen,
        "cod_fac": origin.cod_fac,
        "faculty_name": origin.faculty_name,
        "faculties": origin.faculties,
        "anio": selection["active_anio"],
        "semestre": selection["active_semestre"],
    }


def get_bootstrap_moodle_config() -> dict:
    settings = get_settings()
    return {
        "configured": False,
        "url": settings.moodle_url.rstrip("/"),
        "public_url": settings.moodle_public_url.rstrip("/"),
    }


def get_login_moodle_config() -> dict:
    runtime = get_runtime_config()
    if runtime["configured"]:
        return runtime
    return get_bootstrap_moodle_config()
