from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analytics, companies, upload
from app.config import settings
from app.database import Base, engine
from app.models import *  # noqa: F401, F403 — register models with Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Seben CRM",
    description="Customer intelligence CRM — WhatsApp, email, contacts, and invoice processing",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(companies.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(upload.router, prefix="/api")


@app.get("/")
def root():
    return {"name": "Seben CRM API", "version": "0.1.0", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}
