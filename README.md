# Aula Sync API

Servicio de integración académica UNHEVAL → Moodle para **Escuela de Posgrado** (Id_Gen `03`, Fac. `70`). API FastAPI con panel web de migración.

**Moodle** se despliega por separado; en el servidor Moodle solo se instala el plugin [`local_aulasync`](https://github.com/saemhco/aulasync). Este repo es **solo el servidor API**.

## Puertos (no estándar)

| Servicio | Puerto | Notas |
|---|---|---|
| **Aula Sync API** | `8092` | Panel y `/docs` |
| **Moodle** | `8046` | Otro despliegue (WAMP, etc.) |
| **SQL Server** | `11433` | Instancia nativa en Windows (evitar `1433` en el host) |

---

## Producción — Windows Server (recomendado)

No requiere Docker. WAMP/Apache sirve **Moodle (PHP)**; esta API corre en **Python** aparte.

### Requisitos en el servidor

- Windows Server con **Python 3.12+**
- **SQL Server** accesible (`DB_UNHEVAL`, puerto `11433` recomendado)
- **Moodle** ya operativo + plugin `local_aulasync` instalado

### Instalación

```powershell
cd C:\apps
git clone https://github.com/saemhco/aula-sync.git
cd aula-sync
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install-windows.ps1
```

Editar `.env` (plantilla en `.env.windows.example`):

```env
DB_HOST=localhost
DB_PORT=11433
MOODLE_URL=http://localhost:8046
MOODLE_PUBLIC_URL=http://moodle.tudominio.edu.pe:8046
SETTINGS_DB_PATH=C:/apps/aula-sync/data/settings.db
AULA_SYNC_PUBLIC_URL=http://servidor:8092
APP_ADMIN_USERNAME=admin
APP_ADMIN_PASSWORD=...
INTEGRATION_TOKEN_KEY=...
```

### Arrancar

```powershell
.\scripts\run-api.ps1
```

- Panel: http://servidor:8092/
- Docs: http://servidor:8092/docs
- Health: http://servidor:8092/health

### Servicio permanente

Usar **NSSM** o **Programador de tareas** para ejecutar al inicio:

```
C:\apps\aula-sync\.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8092
```

Directorio de trabajo: `C:\apps\aula-sync`. Variable `PYTHONPATH=C:\apps\aula-sync`.

### Proxy opcional (WAMP / Apache)

Si quieres publicar por el puerto 80/443 de Apache, deja uvicorn en `8092` y configura proxy reverso. Ver `scripts/apache-proxy.example.conf`.

### Enlace con Moodle

1. En Moodle: **Plugins → local_aulasync → Administrar token** → generar token.
2. En Aula Sync: **Ajustes → destino Moodle** → pegar token y URLs.
3. `AULA_SYNC_PUBLIC_URL` debe coincidir con la URL real de este API (Moodle bloquea el origen en la primera petición).

---

## Desarrollo local (Docker)

Para desarrollo con SQL Server en contenedor:

```bash
cp .env.example .env   # COMPOSE_PROFILES=local-db, DB_HOST=sqlserver
docker compose up -d --build
# o solo API + BD externa:
docker compose -f compose.prod.yaml up -d --build
```

- SQL Server en Docker se expone en host `11433` (`MSSQL_HOST_PORT`)
- Backup inicial: `../aula/DB_UNHEVAL.bak` (~10 GB)

### Apple Silicon

SQL Server en Docker requiere Rosetta en Docker Desktop.

---

## Uso del panel

Login con usuario **Aula Sync** (`APP_ADMIN_*` en `.env`), no credenciales Moodle.

Desde el panel:

- Configurar origen académico y destino Moodle
- Migrar cursos, usuarios, matrículas
- Reportes y cerrar ciclo

Sesión: header `X-Session-Token` (token `sess_…` del login).

### Login (API)

```bash
curl -X POST http://localhost:8092/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"..."}'
```

---

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

---

**Desarrollado por Sumaq IT E.I.R.L.**  
Contacto: [github.com/saemhco](https://github.com/saemhco)
