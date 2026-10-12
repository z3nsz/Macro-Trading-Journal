"""Health-check endpoint: proves the backend is running and reports database status."""

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.db import database_is_reachable, get_db

router = APIRouter()


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    app: str
    environment: str
    database: Literal["connected", "unavailable"]
    server_time: datetime


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)) -> HealthResponse:
    db_ok = database_is_reachable(db)
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        app=settings.app_name,
        environment=settings.environment,
        database="connected" if db_ok else "unavailable",
        server_time=datetime.now(timezone.utc),
    )
