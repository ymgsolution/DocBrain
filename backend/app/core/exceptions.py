class DomainError(Exception):
    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, fields: list[dict] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.fields = fields


class NotFoundError(DomainError):
    status_code = 404
    code = "NOT_FOUND"


class UnauthorizedError(DomainError):
    status_code = 401
    code = "UNAUTHORIZED"


class PermissionDeniedError(DomainError):
    status_code = 403
    code = "PERMISSION_DENIED"


class ConflictError(DomainError):
    status_code = 409
    code = "CONFLICT"


class ValidationError(DomainError):
    status_code = 422
    code = "VALIDATION_FAILED"


class PayloadTooLargeError(DomainError):
    status_code = 413
    code = "PAYLOAD_TOO_LARGE"


class UnsupportedMediaTypeError(DomainError):
    status_code = 415
    code = "UNSUPPORTED_MEDIA_TYPE"


class GoneError(DomainError):
    status_code = 410
    code = "GONE"
