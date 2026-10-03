from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    message: str = "Success"


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[dict[str, Any]] | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


def ok(data: Any = None, message: str = "Success") -> ApiResponse:
    return ApiResponse(success=True, data=data, message=message)


ERROR_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Missing, invalid or expired token"},
    404: {"model": ErrorResponse, "description": "Resource not found (or not owned by the caller)"},
    422: {"model": ErrorResponse, "description": "Validation error"},
}
