from fastapi import APIRouter, Depends, HTTPException, Query

from app.clients.moodle import MoodleClient, MoodleIntegrationError
from app.db import academic
from app.dependencies import get_runtime_context, integration_token_from_context, require_configured
from app.schemas import MigrateCourseRequest

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("")
def list_courses(
    fac: str | None = Query(None, description="Código de facultad"),
    eap: str | None = Query(None, description="Código de escuela"),
    profe: str | None = Query(None, description="Código de profesor"),
    ctx: dict = Depends(get_runtime_context),
):
    return academic.load_courses(
        ctx["origin"],
        ctx["anio"],
        ctx["semestre"],
        cod_fac=fac,
        cod_eap=eap,
        profe=profe,
    )


@router.get("/facultades")
def list_faculties(ctx: dict = Depends(get_runtime_context)):
    return academic.get_course_filter_faculties(ctx["origin"], ctx["anio"], ctx["semestre"])


@router.get("/filters/facultades")
def list_filter_faculties(ctx: dict = Depends(get_runtime_context)):
    return academic.get_course_filter_faculties(ctx["origin"], ctx["anio"], ctx["semestre"])


@router.get("/filters/escuelas")
def list_filter_escuelas(
    fac: str | None = Query(None, description="Código de facultad"),
    ctx: dict = Depends(get_runtime_context),
):
    return academic.get_course_filter_escuelas(ctx["origin"], ctx["anio"], ctx["semestre"], cod_fac=fac)


@router.get("/filters/profesores")
def list_filter_profesores(
    fac: str | None = Query(None, description="Código de facultad"),
    eap: str | None = Query(None, description="Código de escuela"),
    ctx: dict = Depends(get_runtime_context),
):
    return academic.get_course_filter_profesores(
        ctx["origin"],
        ctx["anio"],
        ctx["semestre"],
        cod_fac=fac,
        cod_eap=eap,
    )


@router.post("/migrate")
async def migrate_course(body: MigrateCourseRequest, ctx: dict = Depends(require_configured)):
    origin = ctx["origin"]
    otros_profesores = academic.get_other_teachers(
        origin,
        body.codicur,
        body.fac,
        body.eap,
        body.anio,
        body.profesor,
        body.semestre,
        body.tipacta,
        body.seccion,
    )
    alumnos = academic.get_course_students(
        origin,
        body.anio,
        body.semestre,
        body.codicur,
        body.grupo,
        body.fac,
        body.eap,
        body.tipacta,
        body.seccion,
    )

    migrupo = int(body.grupo)
    if migrupo < 2:
        migrupo = 1

    categories = academic.get_moodle_categories_for_course(
        origin,
        ctx["anio"],
        ctx["semestre"],
        body.fac,
        body.eap,
    )
    if not categories:
        escuela_idnumber = f"{origin.id_gen}{body.fac}{body.eap}"
        raise HTTPException(
            status_code=404,
            detail=(
                f"No se encontró la categoría {escuela_idnumber} "
                f"(facultad {body.fac}, escuela {body.eap}) en UNHEVAL "
                f"para el periodo {ctx['anio']}-{ctx['semestre']}."
            ),
        )

    client = MoodleClient(ctx)
    integration_token = integration_token_from_context(ctx)
    try:
        categories_sync = await client.sync_categories(integration_token, categories)
        result = await client.migrate_course(
            token=integration_token,
            curso_codigo=body.codcurso,
            profesor=body.profesor,
            grupo=migrupo,
            curso_nombre=body.nomcurso,
            alumnos=alumnos,
            otros_profesores=otros_profesores,
        )
        if isinstance(result, dict) and result.get("status") is False:
            raise MoodleIntegrationError(str(result.get("code") or "Error al migrar curso"))
        return {**result, "categories_sync": categories_sync}
    except MoodleIntegrationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
