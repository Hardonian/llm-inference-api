"""Custom exceptions for LLM Inference API."""
from typing import Any, Dict, Optional


class LLMInferenceError(Exception):
    """Base exception for LLM Inference API."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}


class OllamaConnectionError(LLMInferenceError):
    """Raised when Ollama connection fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, instance: str = "unknown"):
        super().__init__(
            message,
            status_code=503,
            error_code="OLLAMA_CONNECTION_ERROR",
            details={**details, "instance": instance} if details else {"instance": instance},
        )


class ModelNotFoundError(LLMInferenceError):
    """Raised when model is not found on any instance."""

    def __init__(self, model: str):
        super().__init__(
            f"Model '{model}' not found on any Ollama instance",
            status_code=404,
            error_code="MODEL_NOT_FOUND",
            details={"model": model},
        )


class ModelNotAvailableError(LLMInferenceError):
    """Raised when model is not available on the target GPU instance."""

    def __init__(self, model: str, instance: str):
        super().__init__(
            f"Model '{model}' not available on {instance}",
            status_code=503,
            error_code="MODEL_NOT_AVAILABLE",
            details={"model": model, "instance": instance},
        )


class InferenceError(LLMInferenceError):
    """Raised when inference fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            status_code=500,
            error_code="INFERENCE_ERROR",
            details=details,
        )


class RateLimitError(LLMInferenceError):
    """Raised when rate limit is exceeded."""

    def __init__(self, limit: int, window: int, retry_after: int):
        super().__init__(
            f"Rate limit exceeded: {limit} requests per {window}s",
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"limit": limit, "window": window, "retry_after": retry_after},
        )


class AuthenticationError(LLMInferenceError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR",
        )


class AuthorizationError(LLMInferenceError):
    """Raised when authorization fails."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message,
            status_code=403,
            error_code="AUTHORIZATION_ERROR",
        )


class ValidationError(LLMInferenceError):
    """Raised when request validation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class HealthCheckError(LLMInferenceError):
    """Raised when health check fails."""

    def __init__(self, instance: str, message: str):
        super().__init__(
            f"Health check failed for {instance}: {message}",
            status_code=503,
            error_code="HEALTH_CHECK_FAILED",
            details={"instance": instance, "message": message},
        )