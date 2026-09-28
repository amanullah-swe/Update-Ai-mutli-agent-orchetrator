"""GET /api/health."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_app_settings, get_db
from app.modules.health.schemas import DatabaseHealth, HealthOut
from app.shared.core.config import Settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthOut)
def health(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> HealthOut:
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 — report, don't fail
        db_ok = False
    return HealthOut(
        status="ok",
        version=settings.version,
        environment=settings.environment,
        database=DatabaseHealth(status="ok" if db_ok else "unavailable"),
        timestamp=datetime.now(timezone.utc),
    )