from dataclasses import dataclass
from typing import Literal

OriginKey = Literal["amazon", "profi", "postgrado"]

PREGRADO_FACULTIES = (
    "('01','02','03','04','05','06','07','08','09','10','11','12','13','14')"
)


@dataclass(frozen=True)
class OriginProfile:
    key: OriginKey
    label: str
    area: str
    id_gen: str
    cod_fac: str
    faculty_name: str
    faculties: str
    course_prefix: str | None = None


ORIGINS: dict[OriginKey, OriginProfile] = {
    "amazon": OriginProfile(
        key="amazon",
        label="Pregrado",
        area="Pregrado",
        id_gen="01",
        cod_fac="09",
        faculty_name="PREGRADO",
        faculties=PREGRADO_FACULTIES,
        course_prefix=None,
    ),
    "profi": OriginProfile(
        key="profi",
        label="Segunda especialización",
        area="Segunda especialización",
        id_gen="16",
        cod_fac="05",
        faculty_name="SEGUNDA ESPECIALIZACION",
        faculties="('05')",
        course_prefix="PFI - ",
    ),
    "postgrado": OriginProfile(
        key="postgrado",
        label="Postgrado",
        area="Escuela de Posgrado",
        id_gen="03",
        cod_fac="70",
        faculty_name="ESCUELA DE POSGRADO",
        faculties="('70')",
        course_prefix="POS - ",
    ),
}


def get_origin(key: str) -> OriginProfile | None:
    return ORIGINS.get(key)  # type: ignore[arg-type]


def list_origins() -> list[OriginProfile]:
    return list(ORIGINS.values())
