from fastapi import APIRouter, Depends

from app.clients.moodle import MoodleClient
from app.db import academic
from app.dependencies import get_runtime_context, integration_token_from_context, require_configured
from app.schemas import EnrollRequest, UnenrollRequest

router = APIRouter(prefix="/enrollments", tags=["enrollments"])


def _pad_profe(profe: str) -> str:
    return profe.zfill(8)


def _pad_semestre(semestre: str) -> str:
    return semestre.zfill(2)


@router.get("/courses")
def list_enrollment_courses(ctx: dict = Depends(get_runtime_context)):
    return academic.get_enrollment_courses(ctx["origin"], ctx["anio"], ctx["semestre"])


@router.post("/enroll")
async def enroll(body: EnrollRequest, ctx: dict = Depends(require_configured)):
    origin = ctx["origin"]
    profe = _pad_profe(body.profe)
    semestre = _pad_semestre(body.semestre)

    alumnos = academic.get_enrollment_students(
        origin, body.fac, body.eap, body.codcurso, body.grupo, body.anio, semestre
    )
    if not alumnos:
        return {
            "status": False,
            "code": "404 No se encontraron alumnos matriculados en este curso, solicite una foto del intranet",
        }

    migrupo = int(body.grupo)
    if migrupo < 2:
        migrupo = 1

    curso_codigo = f"{body.fac}{body.eap}{body.aplan}{body.codcurso}{body.anio}{semestre}"
    client = MoodleClient(ctx)
    return await client.enroll(
        token=integration_token_from_context(ctx),
        curso_codigo=curso_codigo,
        profesor=profe,
        grupo=migrupo,
        alumnos=alumnos,
    )


@router.post("/unenroll")
async def unenroll(body: UnenrollRequest, ctx: dict = Depends(require_configured)):
    origin = ctx["origin"]
    fac = body.fac.zfill(2) if len(body.fac) == 1 else body.fac
    eap = body.eap.zfill(2) if len(body.eap) == 1 else body.eap
    grupo = body.grupo
    if grupo == "0":
        grupo = ""
    elif len(grupo) == 1:
        grupo = grupo.zfill(2)
    else:
        grupo = ""
    profe = _pad_profe(body.profe)
    semestre = _pad_semestre(body.semestre)

    alumnos = academic.get_unenrollment_students(
        origin, fac, eap, body.codcurso, grupo, body.anio, semestre
    )

    curso_codigo = f"{fac}{eap}{body.aplan}{body.codcurso}"
    client = MoodleClient(ctx)
    return await client.unenroll(
        token=integration_token_from_context(ctx),
        curso_codigo=curso_codigo,
        profesor=profe,
        alumnos=alumnos,
    )
