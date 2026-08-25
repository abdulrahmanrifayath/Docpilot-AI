from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from backend.app.core.logging import logger


class DocPilotException(Exception):
    """Base exception for DocPilot AI application."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundException(DocPilotException):
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            message=f"{resource} with id '{identifier}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource": resource, "identifier": identifier},
        )


class ValidationException(DocPilotException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class ConfigurationException(DocPilotException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


async def docpilot_exception_handler(request: Request, exc: DocPilotException) -> JSONResponse:
    logger.error(f"DocPilotException occurred: {exc.message} | URL: {request.url} | Details: {exc.details}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": exc.__class__.__name__,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(f"Unhandled server exception: {str(exc)} | URL: {request.url}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "type": "InternalServerError",
                "message": "An unexpected error occurred while processing your request.",
            }
        },
    )
