from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.db.connection import fetch_one
from app.db.settings_db import init_db
from app.db.auth_db import init_auth_db
from app.routers import auth, categories, courses, enrollments, reports, settings, users

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    init_auth_db()
    yield


app = FastAPI(
    title="Aula Sync API",
    description="Integración académica UNHEVAL → Moodle",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(settings.router)
app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(categories.router)
app.include_router(users.router)
app.include_router(enrollments.router)
app.include_router(reports.router)

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def panel():
    index = STATIC_DIR / "index.html"
    if index.is_file():
        return FileResponse(index)
    return {"message": "Panel web no disponible. Usa /docs para la API."}


@app.get("/health")
def health():
    try:
        fetch_one("SELECT 1 as ok")
        db_status = "connected"
    except Exception as exc:
        db_status = f"error: {exc}"
    return {"status": "ok", "database": db_status}
