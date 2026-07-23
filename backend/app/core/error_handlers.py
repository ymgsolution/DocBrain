import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import DomainError


def _envelope(code: str, message: str, correlation_id: str, fields: list[dict] | None = None) -> dict:
    error: dict = {"code": code, "message": message, "correlationId": correlation_id}
    if fields:
        error["fields"] = fields
    return {"error": error}


def _correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", str(uuid.uuid4()))


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(exc.code, exc.message, _correlation_id(request), exc.fields),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [
            {"field": ".".join(str(p) for p in err["loc"][1:]), "message": err["msg"]}
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=_envelope(
                "VALIDATION_FAILED", "One or more fields are invalid.", _correlation_id(request), fields
            ),
        )
