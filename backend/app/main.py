from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from app.config import get_settings
from app.database import init_db
from app.routers import applications, templates, consultations

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    yield


app = FastAPI(
    title="LegalService API",
    description="Платформа юридических услуг: консультации, шаблоны документов, AI-квалификация",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статические файлы (шаблоны для скачивания)
if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Роутеры
app.include_router(applications.router, prefix="/api")
app.include_router(templates.router, prefix="/api")
app.include_router(consultations.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": settings.APP_NAME}
