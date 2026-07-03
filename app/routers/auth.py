from fastapi import APIRouter, Depends, Header, HTTPException

from app.config import get_bootstrap_moodle_config, get_runtime_config
from app.db import auth_db
from app.dependencies import get_current_user
from app.schemas import ChangeCredentialsRequest, ChangeCredentialsResponse, LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    user = auth_db.authenticate_user(body.username, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    session_token = auth_db.create_session(user["id"])
    runtime = get_runtime_config()

    if runtime["configured"]:
        origin = runtime["origin"]
        destination = runtime["destination"]
        return LoginResponse(
            status=True,
            token=session_token,
            configured=True,
            username=user["username"],
            server=origin.key,
            area=origin.area,
            origin_label=origin.label,
            destination_name=destination["name"],
            moodle_url=runtime["url"],
            moodle_public_url=runtime["public_url"],
        )

    bootstrap = get_bootstrap_moodle_config()
    return LoginResponse(
        status=True,
        token=session_token,
        configured=False,
        username=user["username"],
        server="bootstrap",
        area="Administración del sistema",
        origin_label="",
        destination_name="Acceso inicial",
        moodle_url=bootstrap["url"],
        moodle_public_url=bootstrap["public_url"],
    )


@router.post("/logout")
async def logout(x_session_token: str = Header(default="", alias="X-Session-Token")):
    if x_session_token.strip():
        auth_db.revoke_session(x_session_token)
    return {"status": True}


@router.put("/credentials", response_model=ChangeCredentialsResponse)
async def change_credentials(
    body: ChangeCredentialsRequest,
    user: dict = Depends(get_current_user),
):
    try:
        updated = auth_db.update_credentials(
            user["id"],
            body.current_password,
            new_username=body.new_username,
            new_password=body.new_password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ChangeCredentialsResponse(username=updated["username"])
