"""
Error classes and DRF exception handler for ComfyUI integration.

Provides custom exception hierarchy for ComfyUI-related errors
and integrates with DRF for proper error responses.
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


class ComfyAPIError(Exception):
    """Base exception for all ComfyUI-related errors."""
    pass


class ComfyConnectionError(ComfyAPIError):
    """Raised when ComfyUI is unreachable or returns an error HTTP response."""
    pass


class ComfyValidationError(ComfyAPIError):
    """Raised when workflow JSON has node validation errors."""
    
    def __init__(self, message: str, node_errors: dict = None):
        super().__init__(message)
        self.node_errors = node_errors or {}


class ComfyExecutionError(ComfyAPIError):
    """Raised when a runtime error occurs inside ComfyUI during generation."""
    
    def __init__(self, message: str, node_id: str = None, node_type: str = None):
        super().__init__(message)
        self.node_id = node_id
        self.node_type = node_type


class ComfyTimeoutError(ComfyAPIError):
    """Raised when a workflow execution times out."""
    pass


class ComfyNotFoundError(ComfyAPIError):
    """Raised when a job or file is not found."""
    pass


def comfy_exception_handler(exc, context):
    """
    DRF custom exception handler that translates ComfyAPIError
    subclasses into proper DRF JSON responses.
    
    Register this in settings.py:
    REST_FRAMEWORK = {"EXCEPTION_HANDLER": "comfyui.errors.comfy_exception_handler"}
    """
    if isinstance(exc, ComfyConnectionError):
        return Response(
            {"error": "ComfyUI Unavailable", "detail": str(exc)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    
    if isinstance(exc, ComfyValidationError):
        return Response(
            {"error": "Workflow Validation Failed", "node_errors": exc.node_errors},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    
    if isinstance(exc, ComfyExecutionError):
        return Response(
            {"error": "Execution Error", "detail": str(exc), "node_id": exc.node_id},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    
    if isinstance(exc, ComfyTimeoutError):
        return Response(
            {"error": "Generation Timeout", "detail": str(exc)},
            status=status.HTTP_504_GATEWAY_TIMEOUT,
        )
    
    if isinstance(exc, ComfyNotFoundError):
        return Response(
            {"error": "Not Found", "detail": str(exc)},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Fall back to DRF default handler for everything else
    return exception_handler(exc, context)
