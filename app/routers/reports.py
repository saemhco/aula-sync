from fastapi import APIRouter, Depends

from app.clients.moodle import MoodleClient
from app.db import academic
from app.dependencies import integration_token_from_context, require_configured
from app.schemas import CloseCycleRequest

router = APIRouter(tags=["reports", "cycles"])


@router.get("/reports/alumnos-inscritos")
def report_alumnos_inscritos(ctx: dict = Depends(require_configured)):
    return academic.alumnos_inscritos(ctx["origin"], ctx["anio"], ctx["semestre"])


@router.get("/reports/docentes-secundarios")
def report_docentes_secundarios(ctx: dict = Depends(require_configured)):
    return academic.docentes_secundarios(ctx["origin"], ctx["anio"], ctx["semestre"])


@router.post("/cycles/{anio}/close")
async def close_cycle(anio: str, body: CloseCycleRequest, ctx: dict = Depends(require_configured)):
    client = MoodleClient(ctx)
    return await client.close_cycle(token=integration_token_from_context(ctx), ciclo_academico=anio)
