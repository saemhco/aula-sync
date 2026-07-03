from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    status: bool
    token: str | None = None
    configured: bool = False
    username: str = ""
    server: str
    area: str
    origin_label: str
    destination_name: str
    moodle_url: str
    moodle_public_url: str


class ChangeCredentialsRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_username: str | None = Field(default=None, min_length=2, max_length=120)
    new_password: str | None = Field(default=None, min_length=8, max_length=120)


class ChangeCredentialsResponse(BaseModel):
    status: bool = True
    username: str


class MigrateCourseRequest(BaseModel):
    codcurso: str
    profesor: str
    grupo: str
    nomcurso: str
    anio: str
    semestre: str
    fac: str
    eap: str
    codicur: str
    tipacta: str = "01"
    seccion: str = ""


class MigrateUserRequest(BaseModel):
    usuario: str
    nombres: str
    apellidos: str
    email: str


class MigrateCategoryRequest(BaseModel):
    idnumber: str
    name: str
    parent_idnumber: str = ""


class MigrateCategoriesRequest(BaseModel):
    fac: str | None = None
    eap: str | None = None


class EnrollRequest(BaseModel):
    fac: str
    eap: str
    aplan: str
    codcurso: str
    grupo: str
    profe: str
    anio: str
    semestre: str


class UnenrollRequest(BaseModel):
    fac: str
    eap: str
    aplan: str
    codcurso: str
    grupo: str
    profe: str
    anio: str
    semestre: str


class CloseCycleRequest(BaseModel):
    anio: str = Field(..., min_length=4, max_length=4)


class ReportQuery(BaseModel):
    anio: str = Field(..., min_length=4, max_length=4)
    sem: str = Field(..., min_length=2, max_length=2)


class DestinationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    moodle_url: str = Field(..., min_length=8)
    moodle_public_url: str = Field(..., min_length=8)
    integration_token: str = Field(..., min_length=20, max_length=200)


class DestinationUpdate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    moodle_url: str = Field(..., min_length=8)
    moodle_public_url: str = Field(..., min_length=8)
    integration_token: str | None = Field(default=None, min_length=20, max_length=200)


class DestinationResponse(BaseModel):
    id: int
    name: str
    moodle_url: str
    moodle_public_url: str
    created_at: str
    has_integration_token: bool = False


class OriginResponse(BaseModel):
    key: str
    label: str
    area: str
    id_gen: str
    cod_fac: str
    faculty_name: str

    @classmethod
    def from_profile(cls, profile) -> "OriginResponse":
        return cls(
            key=profile.key,
            label=profile.label,
            area=profile.area,
            id_gen=profile.id_gen,
            cod_fac=profile.cod_fac,
            faculty_name=profile.faculty_name,
        )


class ActiveConfigRequest(BaseModel):
    origin_key: str = Field(..., pattern="^(amazon|profi|postgrado)$")
    destination_id: int
    anio: str = Field(..., min_length=4, max_length=4)
    semestre: str = Field(..., min_length=2, max_length=2)
    integration_token: str | None = Field(default=None, min_length=20, max_length=200)


class SettingsStatusResponse(BaseModel):
    configured: bool
    active_origin: str | None = None
    active_destination_id: int | None = None
    active_anio: str | None = None
    active_semestre: str | None = None
    origin: OriginResponse | None = None
    destination: DestinationResponse | None = None
    destinations: list[DestinationResponse]
    origins: list[OriginResponse]
