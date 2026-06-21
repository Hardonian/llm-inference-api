"""Application configuration using Pydantic Settings."""
from functools import lru_cache
from typing import Dict, List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class OllamaInstanceConfig(BaseSettings):
    """Configuration for a single Ollama instance."""
    host: str = "localhost"
    port: int = 11434
    gpu_type: str = "auto"
    models: List[str] = Field(default_factory=list)
    max_concurrent_requests: int = 4
    timeout_seconds: int = 300
    health_check_interval: int = 30

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def vram_gb(self) -> int:
        return {"v100": 16, "p40": 24, "3060": 12}.get(self.gpu_type.lower(), 0)


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "LLM Inference API"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "production"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4

    # Authentication
    secret_key: str = Field(..., min_length=32)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6380
    redis_db: int = 0
    redis_password: Optional[str] = None
    redis_ssl: bool = False

    # Postgres/pgvector
    postgres_host: str = "localhost"
    postgres_port: int = 5433
    postgres_db: str = "llm_inference"

    # Metrics
    metrics_enabled: bool = True

    # Rate Limiting
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst: int = 10

    # Dashboard auth (shared secret sent in Authorization header from browser)
    dashboard_api_token: Optional[str] = None

    # Demo mode (fake GPU/services data)
    demo_mode: bool = False

    # Caching TTLs (seconds)
    cache_disk_rescue_ttl: int = 3600
    cache_models_truth_ttl: int = 3600

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def ollama_instances(self) -> Dict[str, OllamaInstanceConfig]:
        return {
            "default": OllamaInstanceConfig(host="localhost", port=11434, gpu_type="v100"),
            "v100": OllamaInstanceConfig(host="localhost", port=11437, gpu_type="v100"),
            "p40": OllamaInstanceConfig(host="localhost", port=11435, gpu_type="p40"),
            "3060": OllamaInstanceConfig(host="localhost", port=11436, gpu_type="3060"),
        }

    @property
    def model_to_gpu_mapping(self) -> Dict[str, str]:
        return {
            "qwen3:32b": "v100",
            "deepseek-r1:32b": "v100",
            "mistral-small3.2": "p40",
            "llama3.1:8b": "p40",
            "qwen2.5-coder:7b": "3060",
            "hermes3": "3060",
            "qwen3-vl": "3060",
            "granite4.1:3b": "3060",
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
