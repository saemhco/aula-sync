from fastapi import APIRouter, Depends, HTTPException, Query

from app.clients.moodle import MoodleClient, MoodleIntegrationError
from app.db import academic
from app.db import settings_db
from app.dependencies import get_runtime_context, integration_token_from_context, require_configured
from app.schemas import MigrateUserRequest

router = APIRouter(prefix="/users", tags=["users"])


def _attach_user_migrations(users: list[dict], ctx: dict) -> list[dict]:
    destination = ctx["destination"]
    migrations = settings_db.get_user_migrations(
        destination["id"],
        ctx["server"],
        [user["usuario"] for user in users],
    )
    for user in users:
        user["ultima_migracion"] = migrations.get(str(user["usuario"]).strip())
    return users


@router.get("/years")
def list_years(ctx: dict = Depends(require_configured)):
    return academic.get_years(ctx["origin"])


@router.get("")
def list_users(
    tipo: str = Query(..., description="1=alumnos, 2=docentes"),
    fac: str | None = Query(None, description="Código de facultad"),
    eap: str | None = Query(None, description="Código de escuela"),
    ctx: dict = Depends(get_runtime_context),
):
    users = academic.get_users(
        ctx["origin"],
        tipo,
        ctx["anio"],
        ctx["semestre"],
        cod_fac=fac,
        cod_eap=eap,
    )
    return _attach_user_migrations(users, ctx)


@router.get("/filters/facultades")
def list_filter_faculties(
    tipo: str = Query(..., description="1=alumnos, 2=docentes"),
    ctx: dict = Depends(get_runtime_context),
):
    return academic.get_user_filter_faculties(ctx["origin"], tipo, ctx["anio"], ctx["semestre"])


@router.get("/filters/escuelas")
def list_filter_escuelas(
    tipo: str = Query(..., description="1=alumnos, 2=docentes"),
    fac: str | None = Query(None, description="Código de facultad"),
    ctx: dict = Depends(get_runtime_context),
):
    return academic.get_user_filter_escuelas(
        ctx["origin"],
        tipo,
        ctx["anio"],
        ctx["semestre"],
        cod_fac=fac,
    )


@router.post("/migrate")
async def migrate_user(body: MigrateUserRequest, ctx: dict = Depends(require_configured)):
    client = MoodleClient(ctx)
    try:
        result = await client.migrate_user(
            token=integration_token_from_context(ctx),
            usuario=body.usuario,
            nombres=body.nombres,
            apellidos=body.apellidos,
            email=body.email,
        )
    except MoodleIntegrationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    migrated_at = settings_db.record_user_migration(
        body.usuario,
        ctx["destination"]["id"],
        ctx["server"],
    )
    return {**result, "ultima_migracion": migrated_at}
