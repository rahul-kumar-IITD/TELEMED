"""System endpoints."""
from fastapi import APIRouter, Depends

from telemed.api.deps import get_container
from telemed.service.container import Container

router = APIRouter()

SLOT_WINDOW_DAYS = 14
CHANGE_WINDOW_MINUTES = 60


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/config")
def config(container: Container = Depends(get_container)) -> dict[str, str | int]:
    return {
        "provider_timezone": container.runtime.provider_timezone,
        "slot_window_days": SLOT_WINDOW_DAYS,
        "change_window_minutes": CHANGE_WINDOW_MINUTES,
    }
