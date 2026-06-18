"""Pydantic models for LLM Inference API - Models and Health."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str
    permission: List[Dict[str, Any]] = Field(default_factory=list)
    root: Optional[str] = None
    parent: Optional[str] = None
    description: Optional[str] = None
    context_length: Optional[int] = None
    capabilities: Optional[Dict[str, Any]] = None


class ModelListResponse(BaseModel):
    object: str = "list"
    data: List[ModelInfo]


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float
    ollama_instances: Dict[str, Dict[str, Any]]
    redis_connected: bool
    gpu_info: Optional[Dict[str, Any]] = None


class InstanceHealth(BaseModel):
    instance: str
    gpu_type: str
    status: str
    models_available: List[str]
    models_loaded: List[str]
    vram_used_gb: Optional[float] = None
    vram_total_gb: Optional[float] = None
    response_time_ms: Optional[float] = None
    error: Optional[str] = None