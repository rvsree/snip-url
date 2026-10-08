from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from snip_url.api.routes import router
from snip_url.common.config import Settings, load_settings
from snip_url.common.errors import (
    AppError,
    app_error_handler,
    validation_error_handler,
)
from snip_url.repo.db import init_db


# Build the FastAPI app with settings, database, handlers and routes.
def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = load_settings()
    new_app = FastAPI(title="snip-url")
    new_app.state.settings = settings
    init_db(settings.db_path)
    new_app.add_exception_handler(AppError, app_error_handler)
    new_app.add_exception_handler(RequestValidationError, validation_error_handler)
    new_app.include_router(router)
    return new_app


app = create_app()
