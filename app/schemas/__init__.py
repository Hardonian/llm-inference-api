"""Schema exports for LLM Inference API."""
from app.schemas.chat import (
    ChatMessage,
    ChatCompletionRequest,
    ChatCompletionChoice,
    ChatCompletionResponse,
    ChatCompletionChunk,
    MessageRole,
)
from app.schemas.completion import (
    CompletionRequest,
    CompletionChoice,
    CompletionResponse,
    EmbeddingRequest,
    EmbeddingData,
    EmbeddingResponse,
)
from app.schemas.models import (
    Usage,
    ModelInfo,
    ModelListResponse,
    HealthResponse,
    InstanceHealth,
)
from app.schemas.generate import (
    GenerateRequest,
    GenerateResponse,
    ErrorResponse,
)

__all__ = [
    # Chat
    "ChatMessage",
    "ChatCompletionRequest",
    "ChatCompletionChoice",
    "ChatCompletionResponse",
    "ChatCompletionChunk",
    "MessageRole",
    # Completion
    "CompletionRequest",
    "CompletionChoice",
    "CompletionResponse",
    "EmbeddingRequest",
    "EmbeddingData",
    "EmbeddingResponse",
    # Models
    "Usage",
    "ModelInfo",
    "ModelListResponse",
    "HealthResponse",
    "InstanceHealth",
    # Generate
    "GenerateRequest",
    "GenerateResponse",
    "ErrorResponse",
]