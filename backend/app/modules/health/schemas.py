"""Health schema."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class DatabaseHealth(BaseModel):
    status: Literal["ok", "unavailable"]


class HealthOut(BaseModel):
    status: Literal["ok"]
    version: str
    environment: str
    database: DatabaseHealth
    timestamp: datetime