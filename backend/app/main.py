"""Entry point: creates the FastAPI app and plugs in each group of endpoints."""

from fastapi import FastAPI

from app.api import health
from app.config import settings

app = FastAPI(title=settings.app_name)

# Every backend URL starts with /api so the frontend can tell them apart from pages.
app.include_router(health.router, prefix="/api", tags=["health"])
