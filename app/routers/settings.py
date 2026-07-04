from fastapi import APIRouter, Depends, HTTPException

from app.config import get_runtime_config
from app.db import settings_db
from app.dependencies import get_current_user, get_runtime_context, integration_token_from_context, require_configured, require_session
from app.origins import list_origins
from app.schemas import (
    ActiveConfigRequest,
    DestinationCreate,
    DestinationResponse,
    DestinationUpdate,
    OriginResponse,
    SettingsStatusResponse,
)

router = APIRouter(prefix="/settings", tags=["settings"])


def _build_status() -> SettingsStatusResponse:
    config = get_runtime_config()
    selection = settings_db.get_active_selection()
    return SettingsStatusResponse(
        configured=config["configured"],
        active_origin=selection["origin_key"],
        active_destination_id=selection["destination_id"],
        active_anio=selection["active_anio"],
        active_semestre=selection["active_semestre"],
        origin=_origin_response(config["origin"]) if config["origin"] else None,
        destination=DestinationResponse(**settings_db.destination_for_api(selection["destination"]))
        if selection["destination"]
        else None,
        destinations=[DestinationResponse(**d) for d in settings_db.list_destinations()],
        origins=[OriginResponse.from_profile(o) for o in list_origins()],
    )


@router.get("/status", response_model=SettingsStatusResponse)
def settings_status(_: dict = Depends(require_session)):
    return _build_status()


@router.get("/origins", response_model=list[OriginResponse])
def settings_origins(_: dict = Depends(require_session)):
    return [OriginResponse.from_profile(o) for o in list_origins()]


@router.get("/destinations", response_model=list[DestinationResponse])
def settings_destinations(_: dict = Depends(require_session)):
    return [DestinationResponse(**d) for d in settings_db.list_destinations()]


@router.post("/destinations", response_model=DestinationResponse)
def create_destination(body: DestinationCreate, _: dict = Depends(require_session)):
    dest = settings_db.create_destination(
        body.name,
        body.moodle_url,
        body.moodle_public_url,
        body.integration_token,
    )
    return DestinationResponse(**dest)


@router.put("/destinations/{dest_id}", response_model=DestinationResponse)
def update_destination(dest_id: int, body: DestinationUpdate, _: dict = Depends(require_session)):
    dest = settings_db.update_destination(
        dest_id,
        body.name,
        body.moodle_url,
        body.moodle_public_url,
        integration_token=body.integration_token,
    )
    if not dest:
        raise HTTPException(status_code=404, detail="Destino no encontrado")
    return DestinationResponse(**dest)


@router.delete("/destinations/{dest_id}")
def delete_destination(dest_id: int, _: dict = Depends(require_session)):
    if not settings_db.delete_destination(dest_id):
        raise HTTPException(status_code=404, detail="Destino no encontrado")
    return {"status": True}


@router.put("/active", response_model=SettingsStatusResponse)
def set_active_config(body: ActiveConfigRequest, _: dict = Depends(require_session)):
    from app.origins import get_origin

    if not get_origin(body.origin_key):
        raise HTTPException(status_code=400, detail="Origen inválido")
    if not settings_db.get_destination(body.destination_id):
        raise HTTPException(status_code=400, detail="Destino Moodle no encontrado")

    if body.integration_token and body.integration_token.strip():
        try:
            updated = settings_db.update_destination_token(
                body.destination_id,
                body.integration_token.strip(),
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if not updated:
            raise HTTPException(status_code=404, detail="Destino Moodle no encontrado")

    try:
        settings_db.set_active(body.origin_key, body.destination_id, body.anio, body.semestre)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _build_status()


def _origin_response(origin) -> OriginResponse:
    return OriginResponse.from_profile(origin)
