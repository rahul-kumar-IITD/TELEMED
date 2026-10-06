"""FastAPI application factory."""
import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError

from telemed.api.errors import register_error_handlers
from telemed.api.middleware import RequestContextMiddleware
from telemed.api.routers import admin, appointments, auth, doctors, patients, system
from telemed.service import bootstrap
from telemed.service.container import Clock, Container, build_container


async def _generate_slots(container: Container) -> None:
    """Startup catch-up of the 14-day slot window; a failure is logged, never fatal."""
    try:
        await asyncio.to_thread(container.slot_generator.generate)
    except SQLAlchemyError as exc:
        bootstrap.log_event("slot_generation_failed", error_class=type(exc).__name__)
    else:
        bootstrap.log_event("slot_generation_done")


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    container: Container = app.state.container
    task = asyncio.create_task(_generate_slots(container))  # after accepting connections
    try:
        yield
    finally:
        await task
        container.uow.dispose()


def create_app(clock: Clock | None = None) -> FastAPI:
    """Build the app. Aborts (raises) if settings are invalid, e.g. unknown PROVIDER_TIMEZONE."""
    runtime = bootstrap.bootstrap()
    app = FastAPI(
        title="TeleMed", docs_url=None, redoc_url=None, openapi_url=None, lifespan=_lifespan
    )
    app.state.runtime = runtime
    app.state.container = build_container(runtime, clock)
    app.add_middleware(RequestContextMiddleware)
    register_error_handlers(app)
    app.include_router(system.router)
    app.include_router(auth.router)
    app.include_router(patients.router)
    app.include_router(admin.router)
    app.include_router(doctors.router)
    app.include_router(appointments.router)
    return app
