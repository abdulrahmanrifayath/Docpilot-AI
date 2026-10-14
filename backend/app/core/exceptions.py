from typing import Any, Dict, Optional


class DocPilotException(Exception):
    """Base exception for all DocPilot application exceptions."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class EntityNotFoundException(DocPilotException):
    def __init__(
        self,
        entity_name: str = "Entity",
        entity_id: str = "",
        message: Optional[str] = None,
        entity_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        name = entity_type or entity_name
        msg = message or f"{name} with ID '{entity_id}' was not found."
        det = details or {"entity_name": name, "entity_id": entity_id}
        super().__init__(
            message=msg,
            code="NOT_FOUND",
            status_code=404,
            details=det,
        )


class ValidationException(DocPilotException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=400,
            details=details,
        )


class SecurityException(DocPilotException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            code="SECURITY_VIOLATION",
            status_code=400,
            details=details,
        )


class StorageException(DocPilotException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            code="STORAGE_ERROR",
            status_code=500,
            details=details,
        )


class GitCloneException(DocPilotException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            code="GIT_CLONE_ERROR",
            status_code=400,
            details=details,
        )
