from fastapi import APIRouter, Depends, HTTPException, Query

from app.clients.moodle import MoodleClient, MoodleIntegrationError
from app.db import academic
from app.dependencies import get_runtime_context, integration_token_from_context, require_configured
from app.schemas import MigrateCategoriesRequest

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("")
def list_categories(
    fac: str | None = Query(None, description="Código de facultad"),
    eap: str | None = Query(None, description="Código de escuela"),
    ctx: dict = Depends(get_runtime_context),
):
    return academic.get_moodle_categories(
        ctx["origin"],
        ctx["anio"],
        ctx["semestre"],
        cod_fac=fac,
        cod_eap=eap,
    )


@router.post("/migrate")
async def migrate_categories(body: MigrateCategoriesRequest, ctx: dict = Depends(require_configured)):
    categories = academic.get_moodle_categories(
        ctx["origin"],
        ctx["anio"],
        ctx["semestre"],
        cod_fac=body.fac,
        cod_eap=body.eap,
    )
    client = MoodleClient(ctx)
    try:
        summary = await client.sync_categories(integration_token_from_context(ctx), categories)
    except MoodleIntegrationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if summary["errors"] and not summary["created"] and not summary["updated"] and not summary["skipped"]:
        raise HTTPException(status_code=502, detail=summary)
    return summary
