# Aula Sync API

Servicio de integración académica UNHEVAL → Moodle para **Escuela de Posgrado** (Id_Gen `03`, Fac. `70`). Reemplaza el panel Laravel legacy (`aula`) con una API FastAPI dockerizada.

## Requisitos

- Docker y Docker Compose (`docker compose`, plugin integrado en Docker Desktop)
- Archivo de configuración `compose.yaml` en la raíz del proyecto
- ~20 GB de espacio libre (backup SQL Server ~10 GB + datos restaurados)
- Backup `DB_UNHEVAL.bak` en `../aula/DB_UNHEVAL.bak`

## Levantar el stack

Un solo comando levanta **SQL Server + restore del `.bak` + API**:

```bash
cd /Users/saulescandon/Dev/saem/aula-sync
cp .env.example .env   # si no existe
docker compose up -d --build
```

- Panel web: http://localhost:8092/
- API docs: http://localhost:8092/docs
- `DB_HOST=sqlserver` en `.env` (host interno de Docker)

La primera restauración de `../aula/DB_UNHEVAL.bak` (~10 GB) puede tardar varios minutos:

```bash
docker compose logs -f sqlserver
```

En arranques siguientes, el restore se omite si la BD ya existe.

### Apple Silicon (Mac M1/M2/M3/M4)

SQL Server 2022 requiere emulación amd64. Activa Rosetta en Docker Desktop:

1. **Settings → General → Use Rosetta for x86_64/amd64 emulation on Apple Silicon**
2. Reinicia Docker Desktop

Si SQL Server falla con `Invalid mapping of address`, Rosetta no está activo.

### SQL Server remoto (VPN UNHEVAL)

Si usas BD remota en lugar del contenedor local, comenta el servicio `sqlserver` en `compose.yaml` y levanta solo la API:

```bash
docker compose up -d api
```

Y en `.env`: `DB_HOST=<host-remoto>`

## Moodle local

1. Levantar Moodle (monta scripts legacy de `../integracion`):

```bash
cd /Users/saulescandon/Dev/saem/moodle
docker compose up -d
```

2. Crear tabla `user_token` y config `ciclo_academico`:

```bash
docker exec -i moodle_db mysql -uroot -prootpassword moodle < scripts/moodle-integracion-setup.sql
```

3. Crear usuario admin en Moodle si no existe, y usar esas credenciales en `/auth/login`.

## Uso de la API

### Panel web

Abre http://localhost:8092/ e inicia sesión con credenciales de administrador Moodle. Desde ahí puedes:

- Cargar y migrar cursos (individual o en lote)
- Migrar alumnos y docentes
- Matricular / desmatricular cursos activos
- Generar reportes y cerrar ciclo académico

La sesión Moodle se guarda en el navegador (`sessionStorage`).

### Login (API)

```bash
curl -X POST http://localhost:8092/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin123!"}'
```

### Endpoints protegidos

Incluir header en requests que consultan SQL Server:

- `X-Moodle-Token`: token obtenido del login

### Migrar curso

```bash
curl -X POST http://localhost:8092/courses/migrate \
  -H "Content-Type: application/json" \
  -d '{
    "token": "YOUR_TOKEN",
    "codcurso": "...",
    "profesor": "12345678",
    "grupo": "01",
    "nomcurso": "Nombre del curso",
    "anio": "2024",
    "semestre": "01",
    "fac": "70",
    "eap": "10",
    "codicur": "1205",
    "tipacta": "01",
    "seccion": "01"
  }'
```

## Mapeo desde Laravel

| Laravel | FastAPI |
|---------|---------|
| `POST /validar` | `POST /auth/login` |
| `GET /usuarios/cargarcursos` | `GET /courses?anio=&semestre=` |
| `GET /usuarios/migrarcurso/...` | `POST /courses/migrate` |
| `GET /usuarios/anios` | `GET /users/years` |
| `GET /usuarios/verusuarios/{tipo}/{anio}` | `GET /users?tipo=&anio=` |
| `GET /usuarios/migrar/...` | `POST /users/migrate` |
| `GET /matricula/cursos` | `GET /enrollments/courses` |
| `GET /usuarios/matricular/...` | `POST /enrollments/enroll` |
| `GET /usuarios/desmatricular/...` | `POST /enrollments/unenroll` |
| `GET /cerrarc/ciclo/{anio}` | `POST /cycles/{anio}/close` |
| `GET /api/alumnos-inscritos` | `GET /reports/alumnos-inscritos` |
| `GET /api/docentes-secundarios` | `GET /reports/docentes-secundarios` |

## Fase 2

Plugin Moodle `local_unheval` (scaffold en `moodle/moodle/local/unheval/`) reemplazará los scripts PHP legacy cuando el flujo esté validado.
