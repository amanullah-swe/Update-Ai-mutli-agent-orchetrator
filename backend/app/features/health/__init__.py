"""Health feature slice."""

from app.features.health.router import router
from app.features.health.schemas import DatabaseHealth, HealthOut

__all__ = ["DatabaseHealth", "HealthOut", "router"]
