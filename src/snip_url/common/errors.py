from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    """App error carrying status, code and message."""

    status_code: int
    code: str
    message: str

    # Store the status code, error code and message.
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


# Build the standard error JSON body.
def error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


# Handler: AppError -> JSONResponse with status and error body.
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(exc.code, exc.message),
    )


# Handler: request validation errors -> 422 invalid_request.
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_body("invalid_request", "Request body is invalid"),
    )
