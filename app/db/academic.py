from app.origins import OriginProfile
from app.db.connection import fetch_all, fetch_one


def _course_list_filters(cod_fac: str | None, cod_eap: str | None, profe: str | None) -> tuple[str, list]:
    clause = ""
    params: list = []
    if cod_fac:
        clause += " AND cc.Cod_Fac=%s"
        params.append(cod_fac)
    if cod_eap:
        clause += " AND cc.Cod_EAP=%s"
        params.append(cod_eap)
    if profe:
        clause += " AND RTRIM(cc.Cod_Profe)=%s"
        params.append(profe)
    return clause, params


def load_courses(
    origin: OriginProfile,
    anio: str,
    semestre: str,
    cod_fac: str | None = None,
    cod_eap: str | None = None,
    profe: str | None = None,
) -> list[dict]:
    extra, extra_params = _course_list_filters(cod_fac, cod_eap, profe)
    if origin.key == "amazon":
        return fetch_all(
            f"""
            SELECT cc.Id_Gen+cc.Cod_Fac+cc.Cod_EAP+cc.Anio_Acad+cc.Semestre+cc.Anio_Plan+RTRIM(cc.Cod_Curso)+cc.Id_Tip_Act+RTRIM(cc.Grupo)+cc.Id_Seccion as codcurso,
            CASE WHEN cc.Grupo = '  ' THEN '00' ELSE cc.Grupo END as grupo,
            RTRIM(cc.Cod_Profe) as profe,
            CASE WHEN cc.Id_Tip_Act = '01' THEN 'R - '
                 WHEN cc.Id_Tip_Act = '26' THEN 'V - '
                 WHEN cc.Id_Tip_Act = '14' THEN 'MOV - '
                 WHEN cc.Id_Tip_Act = '05' THEN 'N - '
                 WHEN cc.Id_Tip_Act IN ('04','20','21') THEN 'D - '
                 ELSE '' END + c.Desc_Curso + ' (' + s.Desc_Seccion + ')' as curso,
            f.Desc_Facu as facultad,
            e.Desc_EAP as escuela,
            cc.Cod_Fac as fac, cc.Cod_EAP as eap, REPLACE(cc.Cod_Curso,' ','') as codicur,
            cc.Id_Tip_Act as tipacta, cc.Id_Seccion as seccion
            FROM Carga_Curso cc
            JOIN Curso c ON c.Id_Gen=cc.Id_Gen AND c.Cod_Fac=cc.Cod_Fac AND c.Cod_EAP=cc.Cod_EAP
                        AND c.Anio_Plan=cc.Anio_Plan AND c.Cod_Curso=cc.Cod_Curso
            JOIN Seccion s ON s.Id_Seccion = cc.Id_Seccion
            JOIN Escuela e ON e.Id_Gen=cc.Id_Gen AND e.Cod_Fac=cc.Cod_Fac AND e.Cod_EAP=cc.Cod_EAP
            JOIN Facultad f ON f.Id_Gen=cc.Id_Gen AND f.Cod_Fac=cc.Cod_Fac
            WHERE cc.Id_Gen=%s AND cc.Anio_Acad=%s AND (cc.Semestre=%s OR cc.Semestre='00')
              AND cc.Cod_Fac IN {origin.faculties}
              AND cc.Id_Tip_Act IN ('01','14') AND cc.Cod_Profe<>'00000000'
              AND cc.Serie IS NULL AND cc.Id_Serie IS NULL{extra}
            """,
            (origin.id_gen, anio, semestre, *extra_params),
        )

    if origin.key == "profi":
        return fetch_all(
            f"""
            SELECT cc.Id_Gen+cc.Cod_Fac+cc.Cod_EAP+cc.Anio_Acad+cc.Semestre+cc.Anio_Plan+RTRIM(cc.Cod_Curso)+cc.Id_Tip_Act+RTRIM(cc.Grupo) as codcurso,
            CASE cc.Grupo WHEN '  ' THEN '00' ELSE cc.Grupo END as grupo,
            RTRIM(cc.Cod_Profe) as profe,
            'PFI - '+c.Desc_Curso as curso,
            f.Desc_Facu as facultad,
            e.Desc_EAP as escuela,
            cc.Cod_Fac as fac, cc.Cod_EAP as eap, REPLACE(cc.Cod_Curso,' ','') as codicur,
            cc.Id_Tip_Act as tipacta, '' as seccion
            FROM Carga_Curso cc
            JOIN Curso c ON c.Id_Gen=cc.Id_Gen AND c.Cod_Fac=cc.Cod_Fac AND c.Cod_EAP=cc.Cod_EAP
                        AND c.Anio_Plan=cc.Anio_Plan AND c.Cod_Curso=cc.Cod_Curso
            JOIN Escuela e ON e.Id_Gen=cc.Id_Gen AND e.Cod_Fac=cc.Cod_Fac AND e.Cod_EAP=cc.Cod_EAP
            JOIN Facultad f ON f.Id_Gen=cc.Id_Gen AND f.Cod_Fac=cc.Cod_Fac
            WHERE cc.Id_Gen=%s AND cc.Anio_Acad=%s AND cc.Semestre=%s
              AND cc.Cod_Profe<>'00000000' AND cc.Cod_Fac IN {origin.faculties}{extra}
            """,
            (origin.id_gen, anio, semestre, *extra_params),
        )

    return fetch_all(
        f"""
        SELECT cc.Id_Gen+cc.Cod_Fac+cc.Cod_EAP+cc.Anio_Acad+cc.Semestre+cc.Anio_Plan+RTRIM(cc.Cod_Curso)+cc.Id_Tip_Act+RTRIM(cc.Grupo)+cc.Id_Seccion as codcurso,
        CASE WHEN cc.Grupo = '  ' THEN '00' ELSE cc.Grupo END as grupo,
        RTRIM(cc.Cod_Profe) as profe,
        'POS - '+c.Desc_Curso as curso,
        f.Desc_Facu as facultad,
        e.Desc_EAP as escuela,
        cc.Cod_Fac as fac, cc.Cod_EAP as eap, REPLACE(cc.Cod_Curso,' ','') as codicur,
        cc.Id_Tip_Act as tipacta, cc.Id_Seccion as seccion
        FROM Carga_Curso cc
        JOIN Curso c ON c.Id_Gen=cc.Id_Gen AND c.Cod_Fac=cc.Cod_Fac AND c.Cod_EAP=cc.Cod_EAP
                    AND c.Anio_Plan=cc.Anio_Plan AND c.Cod_Curso=cc.Cod_Curso
        JOIN Escuela e ON e.Id_Gen=cc.Id_Gen AND e.Cod_Fac=cc.Cod_Fac AND e.Cod_EAP=cc.Cod_EAP
        JOIN Facultad f ON f.Id_Gen=cc.Id_Gen AND f.Cod_Fac=cc.Cod_Fac
        WHERE cc.Id_Gen=%s AND cc.Anio_Acad=%s AND cc.Semestre=%s
          AND cc.Cod_Profe<>'00000000' AND cc.Cod_Fac IN {origin.faculties}{extra}
        """,
        (origin.id_gen, anio, semestre, *extra_params),
    )


def get_other_teachers(
    origin: OriginProfile,
    codicur: str,
    fac: str,
    eap: str,
    anio: str,
    profesor: str,
    semestre: str,
    tipacta: str,
    seccion: str,
) -> list[str]:
    if origin.key != "amazon":
        return []

    rows = fetch_all(
        """
        SELECT Profe02, Profe03, Profe04, Profe05, Profe06
        FROM Carga_Curso
        WHERE Id_Gen=%s AND Cod_Curso=%s AND Cod_Fac=%s AND Cod_EAP=%s
          AND Anio_Acad=%s AND Cod_Profe=%s AND Semestre=%s
          AND Id_Tip_Act=%s AND Id_Seccion=%s
        """,
        (origin.id_gen, codicur, fac, eap, anio, profesor, semestre, tipacta, seccion),
    )
    if not rows:
        return []

    otros: list[str] = []
    row = rows[0]
    for field in ("Profe02", "Profe03", "Profe04", "Profe05", "Profe06"):
        value = str(row.get(field) or "").strip()
        if value and value != "00000000" and len(value) == 8:
            otros.append(value)
    return otros


def get_course_students(
    origin: OriginProfile,
    anio: str,
    semestre: str,
    codicur: str,
    grupo: str,
    fac: str,
    eap: str,
    tipacta: str,
    seccion: str = "",
) -> list[dict]:
    if origin.key == "profi":
        return fetch_all(
            """
            SELECT a.Id_Alumno as codigo, p.Nombres as nombres,
                   p.Paterno+' '+p.Materno as apellidos,
                   CASE WHEN p.E_Mail LIKE '%@%' THEN p.E_Mail ELSE p.Codigo+'@unheval.edu.pe' END as email
            FROM Nota_Alumno na
            JOIN Alumno a ON a.Id_Gen=na.Id_Gen AND a.Cod_Fac=na.Cod_Fac AND a.Cod_EAP=na.Cod_EAP AND a.Codigo=na.Codigo
            JOIN Persona p ON p.Codigo=na.Codigo
            WHERE na.Anio_Acad=%s AND (na.Semestre=%s OR na.Semestre='00')
              AND na.cod_curso=%s AND na.Grupo IN (%s, '')
              AND na.Id_Gen=%s AND na.Cod_Fac=%s AND na.Cod_EAP=%s AND na.Id_Tip_Act=%s
            """,
            (anio, semestre, codicur, grupo, origin.id_gen, fac, eap, tipacta),
        )

    return fetch_all(
        """
        SELECT a.Id_Alumno as codigo, p.Nombres as nombres,
               p.Paterno+' '+p.Materno as apellidos,
               CASE WHEN a.Email_UNHV LIKE '%@%' THEN a.Email_UNHV ELSE a.Id_Alumno+'@unheval.pe' END as email
        FROM Nota_Alumno na
        JOIN Alumno a ON a.Id_Gen=na.Id_Gen AND a.Cod_Fac=na.Cod_Fac AND a.Cod_EAP=na.Cod_EAP AND a.Codigo=na.Codigo
        JOIN Persona p ON p.Codigo=na.Codigo
        WHERE na.Anio_Acad=%s AND (na.Semestre=%s OR na.Semestre='00')
          AND na.cod_curso=%s AND na.Grupo IN (%s, '')
          AND na.Id_Gen=%s AND na.Cod_Fac=%s AND na.Cod_EAP=%s
          AND na.Id_Tip_Act=%s AND na.Id_Seccion=%s
        """,
        (anio, semestre, codicur, grupo, origin.id_gen, fac, eap, tipacta, seccion),
    )


def get_enrollment_students(
    origin: OriginProfile,
    fac: str,
    eap: str,
    codcurso: str,
    grupo: str,
    anio: str,
    semestre: str,
) -> list[dict]:
    return fetch_all(
        """
        SELECT a.Id_Alumno as codigo, p.Nombres as nombres,
               p.Paterno+' '+p.Materno as apellidos,
               CASE WHEN a.Email_UNHV LIKE '%@%' THEN a.Email_UNHV ELSE a.Id_Alumno+'@unheval.pe' END as email
        FROM Nota_Alumno na
        JOIN Alumno a ON a.Id_Gen=na.Id_Gen AND a.Cod_Fac=na.Cod_Fac AND a.Cod_EAP=na.Cod_EAP AND a.Codigo=na.Codigo
        JOIN Persona p ON p.Codigo=na.Codigo
        WHERE na.Anio_Acad=%s AND (na.Semestre=%s OR na.Semestre='00')
          AND na.cod_curso=%s AND na.Grupo IN (%s, '')
          AND na.Id_Gen=%s AND na.Cod_Fac=%s AND na.Cod_EAP=%s AND na.Id_Tip_Act='01'
        """,
        (anio, semestre, codcurso, grupo, origin.id_gen, fac, eap),
    )


def get_unenrollment_students(
    origin: OriginProfile,
    fac: str,
    eap: str,
    codcurso: str,
    grupo: str,
    anio: str,
    semestre: str,
) -> list[dict]:
    return fetch_all(
        """
        SELECT a.Id_Alumno as codigo, p.Nombres as nombres,
               p.Paterno+' '+p.Materno as apellidos,
               CASE WHEN a.Email_UNHV LIKE '%@%' THEN a.Email_UNHV ELSE a.Id_Alumno+'@unheval.pe' END as email
        FROM Nota_Alumno na
        JOIN Alumno a ON a.Id_Gen=na.Id_Gen AND a.Cod_Fac=na.Cod_Fac AND a.Cod_EAP=na.Cod_EAP AND a.Codigo=na.Codigo
        JOIN Persona p ON p.Codigo=na.Codigo
        WHERE na.Anio_Acad=%s AND na.Semestre=%s AND na.cod_curso=%s AND na.Grupo=''
          AND na.Id_Gen=%s AND na.Cod_Fac=%s AND na.Cod_EAP=%s AND na.Id_Tip_Act='01'
        """,
        (anio, semestre, codcurso, origin.id_gen, fac, eap),
    )


def get_years(origin: OriginProfile) -> list[dict]:
    if origin.key == "amazon":
        return fetch_all(
            f"""
            SELECT DISTINCT na.Anio_Acad as anio
            FROM Nota_Alumno na
            WHERE na.Id_Gen=%s AND na.Cod_Fac IN {origin.faculties} AND na.Anio_Acad > '1997'
            ORDER BY na.Anio_Acad DESC
            """,
            (origin.id_gen,),
        )

    return fetch_all(
        """
        SELECT DISTINCT na.Anio_Acad as anio
        FROM Nota_Alumno na
        WHERE na.Id_Gen=%s AND na.Cod_Fac=%s AND na.Anio_Acad > '1997'
        ORDER BY na.Anio_Acad DESC
        """,
        (origin.id_gen, origin.cod_fac),
    )


def _user_scope_filters(cod_fac: str | None, cod_eap: str | None, prefix: str = "") -> tuple[str, list]:
    clause = ""
    params: list = []
    if cod_fac:
        clause += f" AND {prefix}Cod_Fac=%s"
        params.append(cod_fac)
    if cod_eap:
        clause += f" AND {prefix}Cod_EAP=%s"
        params.append(cod_eap)
    return clause, params


def get_users(
    origin: OriginProfile,
    tipo: str,
    anio: str,
    semestre: str,
    cod_fac: str | None = None,
    cod_eap: str | None = None,
) -> list[dict]:
    if origin.key == "amazon":
        semestre_clause = "AND (na.Semestre=%s OR na.Semestre='00')"
        cc_semestre_clause = "AND (cc.Semestre=%s OR cc.Semestre='00')"
    else:
        semestre_clause = "AND na.Semestre=%s"
        cc_semestre_clause = "AND cc.Semestre=%s"

    if tipo == "1":
        extra, extra_params = _user_scope_filters(cod_fac, cod_eap, "na.")
        return fetch_all(
            f"""
            SELECT p.Paterno+' '+p.Materno as apellidos, p.Nombres as nombres, RTRIM(a.Id_Alumno) as usuario,
                   CASE WHEN p.E_Mail LIKE '%@%' THEN p.E_Mail ELSE a.Id_Alumno+'@unheval.pe' END as correo
            FROM Alumno a
            JOIN Persona p ON p.Codigo=a.Codigo
            JOIN Nota_Alumno na ON na.Id_Gen+na.Cod_Fac+na.Cod_EAP+na.Codigo = a.Id_Gen+a.Cod_Fac+a.Cod_EAP+a.Codigo
            WHERE na.Anio_Acad=%s {semestre_clause} AND na.Id_Gen=%s AND na.Cod_Fac IN {origin.faculties}
              AND RTRIM(a.Id_Alumno)<>'00000000'{extra}
            GROUP BY p.Paterno+' '+p.Materno, p.Nombres, a.Id_Alumno, p.E_Mail
            """,
            (anio, semestre, origin.id_gen, *extra_params)
            if origin.key == "amazon"
            else (anio, semestre, origin.id_gen, *extra_params),
        )

    extra, extra_params = _user_scope_filters(cod_fac, cod_eap, "cc.")
    return fetch_all(
        f"""
        SELECT p.Paterno+' '+p.Materno as apellidos, p.Nombres as nombres, RTRIM(cc.Cod_Profe) as usuario,
               CASE WHEN p.EMail_UNHV LIKE '%@%' THEN p.EMail_UNHV ELSE RTRIM(cc.Cod_Profe)+'@unheval.edu.pe' END as correo
        FROM Carga_Curso cc
        JOIN Persona p ON p.Codigo=cc.Cod_Profe
        WHERE cc.Id_Gen=%s AND cc.Anio_Acad=%s {cc_semestre_clause} AND cc.Cod_Fac IN {origin.faculties}
          AND cc.Cod_Profe<>'00000000'{extra}
        GROUP BY p.Paterno+' '+p.Materno, p.Nombres, cc.Cod_Profe, p.EMail_UNHV
        """,
        (origin.id_gen, anio, semestre, *extra_params)
        if origin.key == "amazon"
        else (origin.id_gen, anio, semestre, *extra_params),
    )


def get_enrollment_courses(origin: OriginProfile, anio: str, semestre: str) -> list[dict]:
    if origin.key == "amazon":
        return fetch_all(
            f"""
            SELECT
                (SELECT f.Desc_Facu FROM Facultad f WHERE f.Id_Gen=cc.Id_Gen AND f.Cod_Fac=cc.Cod_Fac) as facu,
                (SELECT e.Desc_EAP FROM Escuela e WHERE e.Id_Gen=cc.Id_Gen AND e.Cod_Fac=cc.Cod_Fac AND e.Cod_EAP=cc.Cod_EAP) as escu,
                (SELECT c.Desc_Curso FROM Curso c WHERE c.Id_Gen=cc.Id_Gen AND c.Cod_Fac=cc.Cod_Fac AND c.Cod_EAP=cc.Cod_EAP
                 AND c.Anio_Plan=cc.Anio_Plan AND c.Cod_Curso=cc.Cod_Curso) as curso,
                CASE cc.Grupo WHEN '' THEN '0' ELSE cc.GRUPO END as Grupo,
                cc.Cod_Fac as fac, cc.Cod_EAP as eap, cc.Anio_Plan as aplan,
                REPLACE(cc.Cod_Curso,' ','') as codcurso, RTRIM(cc.Cod_Profe) as profe,
                cc.Anio_Acad as anio, cc.Semestre as semestre
            FROM Carga_Curso cc
            WHERE cc.Id_Gen=%s AND Anio_Acad=%s AND (Semestre=%s OR Semestre='00')
              AND Cod_Fac IN {origin.faculties}
              AND Cod_EAP IN ('10','20','30','28')
              AND Id_Tip_Act IN ('01','14') AND cc.Cod_Profe<>'00000000'
              AND cc.Serie IS NULL AND cc.Id_Serie IS NULL
            """,
            (origin.id_gen, anio, semestre),
        )

    if origin.key == "profi":
        return fetch_all(
            f"""
            SELECT
                (SELECT f.Desc_Facu FROM Facultad f WHERE f.Id_Gen=cc.Id_Gen AND f.Cod_Fac=cc.Cod_Fac) as facu,
                (SELECT e.Desc_EAP FROM Escuela e WHERE e.Id_Gen=cc.Id_Gen AND e.Cod_Fac=cc.Cod_Fac AND e.Cod_EAP=cc.Cod_EAP) as escu,
                (SELECT c.Desc_Curso FROM Curso c WHERE c.Id_Gen=cc.Id_Gen AND c.Cod_Fac=cc.Cod_Fac AND c.Cod_EAP=cc.Cod_EAP
                 AND c.Anio_Plan=cc.Anio_Plan AND c.Cod_Curso=cc.Cod_Curso) as curso,
                CASE cc.Grupo WHEN '' THEN '0' ELSE cc.GRUPO END as Grupo,
                cc.Cod_Fac as fac, cc.Cod_EAP as eap, cc.Anio_Plan as aplan,
                REPLACE(cc.Cod_Curso,' ','') as codcurso, RTRIM(cc.Cod_Profe) as profe,
                cc.Anio_Acad as anio, cc.Semestre as semestre
            FROM Carga_Curso cc
            WHERE cc.Id_Gen=%s AND Anio_Acad=%s AND (Semestre=%s OR Semestre='00')
              AND Cod_Fac IN {origin.faculties}
              AND Cod_EAP IN ('10','11','20')
              AND Id_Tip_Act='01' AND cc.Cod_Profe<>'00000000'
            """,
            (origin.id_gen, anio, semestre),
        )

    return fetch_all(
        f"""
        SELECT
            (SELECT f.Desc_Facu FROM Facultad f WHERE f.Id_Gen=cc.Id_Gen AND f.Cod_Fac=cc.Cod_Fac) as facu,
            (SELECT e.Desc_EAP FROM Escuela e WHERE e.Id_Gen=cc.Id_Gen AND e.Cod_Fac=cc.Cod_Fac AND e.Cod_EAP=cc.Cod_EAP) as escu,
            (SELECT c.Desc_Curso FROM Curso c WHERE c.Id_Gen=cc.Id_Gen AND c.Cod_Fac=cc.Cod_Fac AND c.Cod_EAP=cc.Cod_EAP
             AND c.Anio_Plan=cc.Anio_Plan AND c.Cod_Curso=cc.Cod_Curso) as curso,
            CASE cc.Grupo WHEN '' THEN '0' ELSE cc.GRUPO END as Grupo,
            cc.Cod_Fac as fac, cc.Cod_EAP as eap, cc.Anio_Plan as aplan,
            REPLACE(cc.Cod_Curso,' ','') as codcurso, RTRIM(cc.Cod_Profe) as profe,
            cc.Anio_Acad as anio, cc.Semestre as semestre
        FROM Carga_Curso cc
        WHERE cc.Id_Gen=%s AND cc.Cod_Fac=%s AND Anio_Acad=%s AND (Semestre=%s OR Semestre='00')
          AND Cod_EAP IN ('10','20','30','04','01')
          AND Id_Tip_Act='01' AND cc.Cod_Profe<>'00000000'
          AND cc.Serie IS NULL AND cc.Id_Serie IS NULL
        """,
        (origin.id_gen, origin.cod_fac, anio, semestre),
    )


def get_faculties(origin: OriginProfile, anio: str, semestre: str) -> list[dict]:
    return get_course_filter_faculties(origin, anio, semestre)


def get_course_filter_faculties(origin: OriginProfile, anio: str, semestre: str) -> list[dict]:
    if origin.key == "amazon":
        return fetch_all(
            f"""
            SELECT f.Cod_Fac as cod_fac, f.Desc_Facu as facultad
            FROM Carga_Curso cc
            JOIN Facultad f ON f.Id_Gen=cc.Id_Gen AND f.Cod_Fac=cc.Cod_Fac
            WHERE cc.Id_Gen=%s AND cc.Anio_Acad=%s AND (cc.Semestre=%s OR cc.Semestre='00')
              AND cc.Cod_Fac IN {origin.faculties}
              AND cc.Id_Tip_Act IN ('01','14') AND cc.Cod_Profe<>'00000000'
              AND cc.Serie IS NULL AND cc.Id_Serie IS NULL
            GROUP BY f.Cod_Fac, f.Desc_Facu
            ORDER BY f.Desc_Facu
            """,
            (origin.id_gen, anio, semestre),
        )

    if origin.key == "profi":
        return fetch_all(
            f"""
            SELECT f.Cod_Fac as cod_fac, f.Desc_Facu as facultad
            FROM Carga_Curso cc
            JOIN Facultad f ON f.Id_Gen=cc.Id_Gen AND f.Cod_Fac=cc.Cod_Fac
            WHERE cc.Id_Gen=%s AND cc.Anio_Acad=%s AND cc.Semestre=%s
              AND cc.Cod_Profe<>'00000000' AND cc.Cod_Fac IN {origin.faculties}
            GROUP BY f.Cod_Fac, f.Desc_Facu
            ORDER BY f.Desc_Facu
            """,
            (origin.id_gen, anio, semestre),
        )

    return fetch_all(
        f"""
        SELECT f.Cod_Fac as cod_fac, f.Desc_Facu as facultad
        FROM Carga_Curso cc
        JOIN Facultad f ON f.Id_Gen=cc.Id_Gen AND f.Cod_Fac=cc.Cod_Fac
        WHERE cc.Id_Gen=%s AND cc.Anio_Acad=%s AND cc.Semestre=%s
          AND cc.Cod_Profe<>'00000000' AND cc.Cod_Fac IN {origin.faculties}
        GROUP BY f.Cod_Fac, f.Desc_Facu
        ORDER BY f.Desc_Facu
        """,
        (origin.id_gen, anio, semestre),
    )


def get_course_filter_escuelas(
    origin: OriginProfile,
    anio: str,
    semestre: str,
    cod_fac: str | None = None,
) -> list[dict]:
    extra, extra_params = _course_list_filters(cod_fac, None, None)
    if origin.key == "amazon":
        return fetch_all(
            f"""
            SELECT e.Cod_EAP as cod_eap, e.Desc_EAP as escuela
            FROM Carga_Curso cc
            JOIN Escuela e ON e.Id_Gen=cc.Id_Gen AND e.Cod_Fac=cc.Cod_Fac AND e.Cod_EAP=cc.Cod_EAP
            WHERE cc.Id_Gen=%s AND cc.Anio_Acad=%s AND (cc.Semestre=%s OR cc.Semestre='00')
              AND cc.Cod_Fac IN {origin.faculties}
              AND cc.Id_Tip_Act IN ('01','14') AND cc.Cod_Profe<>'00000000'
              AND cc.Serie IS NULL AND cc.Id_Serie IS NULL{extra}
            GROUP BY e.Cod_EAP, e.Desc_EAP
            ORDER BY e.Desc_EAP
            """,
            (origin.id_gen, anio, semestre, *extra_params),
        )

    if origin.key == "profi":
        return fetch_all(
            f"""
            SELECT e.Cod_EAP as cod_eap, e.Desc_EAP as escuela
            FROM Carga_Curso cc
            JOIN Escuela e ON e.Id_Gen=cc.Id_Gen AND e.Cod_Fac=cc.Cod_Fac AND e.Cod_EAP=cc.Cod_EAP
            WHERE cc.Id_Gen=%s AND cc.Anio_Acad=%s AND cc.Semestre=%s
              AND cc.Cod_Profe<>'00000000' AND cc.Cod_Fac IN {origin.faculties}{extra}
            GROUP BY e.Cod_EAP, e.Desc_EAP
            ORDER BY e.Desc_EAP
            """,
            (origin.id_gen, anio, semestre, *extra_params),
        )

    return fetch_all(
        f"""
        SELECT e.Cod_EAP as cod_eap, e.Desc_EAP as escuela
        FROM Carga_Curso cc
        JOIN Escuela e ON e.Id_Gen=cc.Id_Gen AND e.Cod_Fac=cc.Cod_Fac AND e.Cod_EAP=cc.Cod_EAP
        WHERE cc.Id_Gen=%s AND cc.Anio_Acad=%s AND cc.Semestre=%s
          AND cc.Cod_Profe<>'00000000' AND cc.Cod_Fac IN {origin.faculties}{extra}
        GROUP BY e.Cod_EAP, e.Desc_EAP
        ORDER BY e.Desc_EAP
        """,
        (origin.id_gen, anio, semestre, *extra_params),
    )


def get_course_filter_profesores(
    origin: OriginProfile,
    anio: str,
    semestre: str,
    cod_fac: str | None = None,
    cod_eap: str | None = None,
) -> list[dict]:
    extra, extra_params = _course_list_filters(cod_fac, cod_eap, None)
    profe_select = """
            SELECT RTRIM(cc.Cod_Profe) as profe,
                   p.Paterno+' '+p.Materno+', '+p.Nombres as nombre
            FROM Carga_Curso cc
            JOIN Persona p ON p.Codigo=cc.Cod_Profe
    """
    profe_group = """
            GROUP BY RTRIM(cc.Cod_Profe), p.Paterno, p.Materno, p.Nombres
            ORDER BY p.Paterno, p.Materno, p.Nombres
    """
    if origin.key == "amazon":
        return fetch_all(
            f"""
            {profe_select}
            WHERE cc.Id_Gen=%s AND cc.Anio_Acad=%s AND (cc.Semestre=%s OR cc.Semestre='00')
              AND cc.Cod_Fac IN {origin.faculties}
              AND cc.Id_Tip_Act IN ('01','14') AND cc.Cod_Profe<>'00000000'
              AND cc.Serie IS NULL AND cc.Id_Serie IS NULL{extra}
            {profe_group}
            """,
            (origin.id_gen, anio, semestre, *extra_params),
        )

    if origin.key == "profi":
        return fetch_all(
            f"""
            {profe_select}
            WHERE cc.Id_Gen=%s AND cc.Anio_Acad=%s AND cc.Semestre=%s
              AND cc.Cod_Profe<>'00000000' AND cc.Cod_Fac IN {origin.faculties}{extra}
            {profe_group}
            """,
            (origin.id_gen, anio, semestre, *extra_params),
        )

    return fetch_all(
        f"""
        {profe_select}
        WHERE cc.Id_Gen=%s AND cc.Anio_Acad=%s AND cc.Semestre=%s
          AND cc.Cod_Profe<>'00000000' AND cc.Cod_Fac IN {origin.faculties}{extra}
        {profe_group}
        """,
        (origin.id_gen, anio, semestre, *extra_params),
    )


def get_user_filter_faculties(origin: OriginProfile, tipo: str, anio: str, semestre: str) -> list[dict]:
    if tipo == "1":
        if origin.key == "amazon":
            return fetch_all(
                f"""
                SELECT f.Cod_Fac as cod_fac, f.Desc_Facu as facultad
                FROM Nota_Alumno na
                JOIN Facultad f ON f.Id_Gen=na.Id_Gen AND f.Cod_Fac=na.Cod_Fac
                WHERE na.Anio_Acad=%s AND (na.Semestre=%s OR na.Semestre='00')
                  AND na.Id_Gen=%s AND na.Cod_Fac IN {origin.faculties}
                GROUP BY f.Cod_Fac, f.Desc_Facu
                ORDER BY f.Desc_Facu
                """,
                (anio, semestre, origin.id_gen),
            )
        return fetch_all(
            f"""
            SELECT f.Cod_Fac as cod_fac, f.Desc_Facu as facultad
            FROM Nota_Alumno na
            JOIN Facultad f ON f.Id_Gen=na.Id_Gen AND f.Cod_Fac=na.Cod_Fac
            WHERE na.Anio_Acad=%s AND na.Semestre=%s
              AND na.Id_Gen=%s AND na.Cod_Fac IN {origin.faculties}
            GROUP BY f.Cod_Fac, f.Desc_Facu
            ORDER BY f.Desc_Facu
            """,
            (anio, semestre, origin.id_gen),
        )

    if origin.key == "amazon":
        return fetch_all(
            f"""
            SELECT f.Cod_Fac as cod_fac, f.Desc_Facu as facultad
            FROM Carga_Curso cc
            JOIN Facultad f ON f.Id_Gen=cc.Id_Gen AND f.Cod_Fac=cc.Cod_Fac
            WHERE cc.Id_Gen=%s AND cc.Anio_Acad=%s AND (cc.Semestre=%s OR cc.Semestre='00')
              AND cc.Cod_Fac IN {origin.faculties} AND cc.Cod_Profe<>'00000000'
            GROUP BY f.Cod_Fac, f.Desc_Facu
            ORDER BY f.Desc_Facu
            """,
            (origin.id_gen, anio, semestre),
        )

    return fetch_all(
        f"""
        SELECT f.Cod_Fac as cod_fac, f.Desc_Facu as facultad
        FROM Carga_Curso cc
        JOIN Facultad f ON f.Id_Gen=cc.Id_Gen AND f.Cod_Fac=cc.Cod_Fac
        WHERE cc.Id_Gen=%s AND cc.Anio_Acad=%s AND cc.Semestre=%s
          AND cc.Cod_Fac IN {origin.faculties} AND cc.Cod_Profe<>'00000000'
        GROUP BY f.Cod_Fac, f.Desc_Facu
        ORDER BY f.Desc_Facu
        """,
        (origin.id_gen, anio, semestre),
    )


def get_user_filter_escuelas(
    origin: OriginProfile,
    tipo: str,
    anio: str,
    semestre: str,
    cod_fac: str | None = None,
) -> list[dict]:
    extra, extra_params = _user_scope_filters(cod_fac, None, "na." if tipo == "1" else "cc.")
    if tipo == "1":
        if origin.key == "amazon":
            return fetch_all(
                f"""
                SELECT e.Cod_EAP as cod_eap, e.Desc_EAP as escuela
                FROM Nota_Alumno na
                JOIN Escuela e ON e.Id_Gen=na.Id_Gen AND e.Cod_Fac=na.Cod_Fac AND e.Cod_EAP=na.Cod_EAP
                WHERE na.Anio_Acad=%s AND (na.Semestre=%s OR na.Semestre='00')
                  AND na.Id_Gen=%s AND na.Cod_Fac IN {origin.faculties}{extra}
                GROUP BY e.Cod_EAP, e.Desc_EAP
                ORDER BY e.Desc_EAP
                """,
                (anio, semestre, origin.id_gen, *extra_params),
            )
        return fetch_all(
            f"""
            SELECT e.Cod_EAP as cod_eap, e.Desc_EAP as escuela
            FROM Nota_Alumno na
            JOIN Escuela e ON e.Id_Gen=na.Id_Gen AND e.Cod_Fac=na.Cod_Fac AND e.Cod_EAP=na.Cod_EAP
            WHERE na.Anio_Acad=%s AND na.Semestre=%s
              AND na.Id_Gen=%s AND na.Cod_Fac IN {origin.faculties}{extra}
            GROUP BY e.Cod_EAP, e.Desc_EAP
            ORDER BY e.Desc_EAP
            """,
            (anio, semestre, origin.id_gen, *extra_params),
        )

    if origin.key == "amazon":
        return fetch_all(
            f"""
            SELECT e.Cod_EAP as cod_eap, e.Desc_EAP as escuela
            FROM Carga_Curso cc
            JOIN Escuela e ON e.Id_Gen=cc.Id_Gen AND e.Cod_Fac=cc.Cod_Fac AND e.Cod_EAP=cc.Cod_EAP
            WHERE cc.Id_Gen=%s AND cc.Anio_Acad=%s AND (cc.Semestre=%s OR cc.Semestre='00')
              AND cc.Cod_Fac IN {origin.faculties} AND cc.Cod_Profe<>'00000000'{extra}
            GROUP BY e.Cod_EAP, e.Desc_EAP
            ORDER BY e.Desc_EAP
            """,
            (origin.id_gen, anio, semestre, *extra_params),
        )

    return fetch_all(
        f"""
        SELECT e.Cod_EAP as cod_eap, e.Desc_EAP as escuela
        FROM Carga_Curso cc
        JOIN Escuela e ON e.Id_Gen=cc.Id_Gen AND e.Cod_Fac=cc.Cod_Fac AND e.Cod_EAP=cc.Cod_EAP
        WHERE cc.Id_Gen=%s AND cc.Anio_Acad=%s AND cc.Semestre=%s
          AND cc.Cod_Fac IN {origin.faculties} AND cc.Cod_Profe<>'00000000'{extra}
        GROUP BY e.Cod_EAP, e.Desc_EAP
        ORDER BY e.Desc_EAP
        """,
        (origin.id_gen, anio, semestre, *extra_params),
    )


def alumnos_inscritos(origin: OriginProfile, anio: str, sem: str) -> list[dict]:
    extra = "" if origin.key == "amazon" else f"AND na.Cod_Fac = '{origin.cod_fac}'"
    return fetch_all(
        f"""
        SELECT f.Desc_Facu, e.Desc_EAP, a.Id_Alumno, p.Codigo, p.Paterno, p.Materno, p.Nombres,
               COUNT(*) as Curs_Inscritos
        FROM Alumno a
        JOIN Persona p ON p.Codigo=a.Codigo
        JOIN Nota_Alumno na ON na.Id_Gen=a.Id_Gen AND na.Cod_Fac=a.Cod_Fac AND na.Cod_EAP=a.Cod_EAP AND na.Codigo=a.Codigo
        JOIN Facultad f ON f.Id_Gen=a.Id_Gen AND f.Cod_Fac=a.Cod_Fac
        JOIN Escuela e ON e.Id_Gen=a.Id_Gen AND e.Cod_Fac=a.Cod_Fac AND e.Cod_EAP=a.Cod_EAP
        WHERE na.Id_Gen=%s {extra} AND na.Anio_Acad=%s AND na.Semestre=%s
          AND na.Id_Tip_Act IN ('01')
        GROUP BY f.Desc_Facu, e.Desc_EAP, a.Id_Alumno, p.Codigo, p.Paterno, p.Materno, p.Nombres
        ORDER BY f.Desc_Facu, e.Desc_EAP, p.Paterno, p.Materno, p.Nombres
        """,
        (origin.id_gen, anio, sem),
    )


def docentes_secundarios(origin: OriginProfile, anio: str, sem: str) -> list[dict]:
    extra = "" if origin.key == "amazon" else f"AND cc.Cod_Fac = '{origin.cod_fac}'"
    return fetch_all(
        f"""
        SELECT f.Desc_Facu, e.Desc_EAP,
               cc.Cod_Fac+cc.Cod_EAP+cc.Anio_Plan+REPLACE(cc.Cod_Curso,' ','')+cc.Id_Tip_Act+cc.Anio_Acad+cc.Semestre as Id_Carga,
               c.Desc_Curso,
               CASE WHEN Grupo='  ' THEN '00' ELSE Grupo END as Grupo,
               c.Cod_Curso, Cod_Profe, Profe02, Profe03, Profe04,
               Jefe_Prac, Jefe_Prac02, Jefe_Prac03, Jefe_Prac04, Jefe_Prac05
        FROM Carga_Curso cc
        JOIN Curso c ON c.Id_Gen=cc.Id_Gen AND c.Cod_Fac=cc.Cod_Fac AND c.Cod_EAP=cc.Cod_EAP
                    AND c.Cod_Curso=cc.Cod_Curso AND c.Anio_Plan=cc.Anio_Plan
        JOIN Facultad f ON f.Id_Gen=cc.Id_Gen AND f.Cod_Fac=cc.Cod_Fac
        JOIN Escuela e ON e.Id_Gen=cc.Id_Gen AND e.Cod_Fac=cc.Cod_Fac AND e.Cod_EAP=cc.Cod_EAP
        WHERE cc.Id_Gen=%s {extra} AND cc.Anio_Acad=%s AND cc.Semestre=%s AND cc.Id_Tip_Act='01'
          AND cc.Cod_Profe<>'00000000'
          AND (cc.Profe02<>'00000000' OR cc.Profe03<>'00000000' OR cc.Profe04<>'00000000'
               OR cc.Profe05<>'00000000' OR cc.Profe06<>'00000000' OR cc.Jefe_Prac<>'00000000'
               OR cc.Jefe_Prac02<>'00000000' OR cc.Jefe_Prac03<>'00000000'
               OR cc.Jefe_Prac04<>'00000000' OR cc.Jefe_Prac05<>'00000000')
        ORDER BY Desc_Facu, Desc_EAP, Desc_Curso
        """,
        (origin.id_gen, anio, sem),
    )


def get_moodle_categories(
    origin: OriginProfile,
    anio: str,
    semestre: str,
    cod_fac: str | None = None,
    cod_eap: str | None = None,
) -> list[dict]:
    extra, extra_params = _course_list_filters(cod_fac, cod_eap, None)
    if origin.key == "amazon":
        rows = fetch_all(
            f"""
            SELECT DISTINCT
                cc.Id_Gen as id_gen,
                f.Cod_Fac as cod_fac,
                f.Desc_Facu as facultad,
                e.Cod_EAP as cod_eap,
                e.Desc_EAP as escuela
            FROM Carga_Curso cc
            JOIN Facultad f ON f.Id_Gen=cc.Id_Gen AND f.Cod_Fac=cc.Cod_Fac
            JOIN Escuela e ON e.Id_Gen=cc.Id_Gen AND e.Cod_Fac=cc.Cod_Fac AND e.Cod_EAP=cc.Cod_EAP
            WHERE cc.Id_Gen=%s AND cc.Anio_Acad=%s AND (cc.Semestre=%s OR cc.Semestre='00')
              AND cc.Cod_Fac IN {origin.faculties}
              AND cc.Id_Tip_Act IN ('01','14') AND cc.Cod_Profe<>'00000000'
              AND cc.Serie IS NULL AND cc.Id_Serie IS NULL{extra}
            ORDER BY f.Desc_Facu, e.Desc_EAP
            """,
            (origin.id_gen, anio, semestre, *extra_params),
        )
    elif origin.key == "profi":
        rows = fetch_all(
            f"""
            SELECT DISTINCT
                cc.Id_Gen as id_gen,
                f.Cod_Fac as cod_fac,
                f.Desc_Facu as facultad,
                e.Cod_EAP as cod_eap,
                e.Desc_EAP as escuela
            FROM Carga_Curso cc
            JOIN Facultad f ON f.Id_Gen=cc.Id_Gen AND f.Cod_Fac=cc.Cod_Fac
            JOIN Escuela e ON e.Id_Gen=cc.Id_Gen AND e.Cod_Fac=cc.Cod_Fac AND e.Cod_EAP=cc.Cod_EAP
            WHERE cc.Id_Gen=%s AND cc.Anio_Acad=%s AND cc.Semestre=%s
              AND cc.Cod_Profe<>'00000000' AND cc.Cod_Fac IN {origin.faculties}{extra}
            ORDER BY f.Desc_Facu, e.Desc_EAP
            """,
            (origin.id_gen, anio, semestre, *extra_params),
        )
    else:
        rows = fetch_all(
            f"""
            SELECT DISTINCT
                cc.Id_Gen as id_gen,
                f.Cod_Fac as cod_fac,
                f.Desc_Facu as facultad,
                e.Cod_EAP as cod_eap,
                e.Desc_EAP as escuela
            FROM Carga_Curso cc
            JOIN Facultad f ON f.Id_Gen=cc.Id_Gen AND f.Cod_Fac=cc.Cod_Fac
            JOIN Escuela e ON e.Id_Gen=cc.Id_Gen AND e.Cod_Fac=cc.Cod_Fac AND e.Cod_EAP=cc.Cod_EAP
            WHERE cc.Id_Gen=%s AND cc.Anio_Acad=%s AND cc.Semestre=%s
              AND cc.Cod_Profe<>'00000000' AND cc.Cod_Fac IN {origin.faculties}{extra}
            ORDER BY f.Desc_Facu, e.Desc_EAP
            """,
            (origin.id_gen, anio, semestre, *extra_params),
        )

    categories: list[dict] = []
    seen: set[str] = set()

    def add_category(level: str, idnumber: str, name: str, parent_idnumber: str, meta: dict) -> None:
        if idnumber in seen:
            return
        seen.add(idnumber)
        categories.append(
            {
                "level": level,
                "idnumber": idnumber,
                "name": name.strip(),
                "parent_idnumber": parent_idnumber,
                **meta,
            }
        )

    for row in rows:
        id_gen = str(row["id_gen"]).strip()
        cod_fac = str(row["cod_fac"]).strip()
        cod_eap = str(row["cod_eap"]).strip()
        facultad_idnumber = f"{id_gen}{cod_fac}00"
        escuela_idnumber = f"{id_gen}{cod_fac}{cod_eap}"

        add_category(
            "facultad",
            facultad_idnumber,
            str(row["facultad"]).strip(),
            "",
            {"cod_fac": cod_fac, "cod_eap": ""},
        )
        add_category(
            "escuela",
            escuela_idnumber,
            str(row["escuela"]).strip(),
            facultad_idnumber,
            {"cod_fac": cod_fac, "cod_eap": cod_eap},
        )

    categories.sort(key=lambda item: (item["level"] != "facultad", item["idnumber"]))
    return categories


def get_moodle_categories_for_course(
    origin: OriginProfile,
    anio: str,
    semestre: str,
    cod_fac: str,
    cod_eap: str,
) -> list[dict]:
    """Categorías facultad + escuela requeridas por curso.php (idnumber de 6 dígitos)."""
    categories = get_moodle_categories(origin, anio, semestre, cod_fac=cod_fac, cod_eap=cod_eap)
    escuela_idnumber = f"{origin.id_gen}{cod_fac}{cod_eap}"
    if any(category["level"] == "escuela" and category["idnumber"] == escuela_idnumber for category in categories):
        return categories
    return []
