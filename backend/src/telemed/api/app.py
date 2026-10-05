"""FastAPI application factory."""
from fastapi import FastAPI

from telemed.api.errors import register_error_handlers
from telemed.api.middleware import RequestContextMiddleware
from telemed.api.routers import system
from telemed.service.bootstrap import bootstrap


def create_app() -> FastAPI:
    """Build the app. Aborts (raises) if settings are invalid, e.g. unknown PROVIDER_TIMEZONE."""
    runtime = bootstrap()
    app = FastAPI(title="TeleMed", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.runtime = runtime
    app.add_middleware(RequestContextMiddleware)
    register_error_handlers(app)
    app.include_router(system.router)
    return app
