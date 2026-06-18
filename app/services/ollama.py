"""Ollama integration for LLM Inference API."""
import asyncio
import logging
import time
from typing import Any, AsyncGenerator, Dict, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.core.exceptions import InferenceError, ModelNotAvailableError, ModelNotFoundError, OllamaConnectionError

logger = logging.getLogger(__name__)


class OllamaClient:
    """Async client for a single Ollama instance."""
    
    def __init__(self, instance_config):
        self.config = instance_config
        self.base_url = instance_config.base_url
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(
                connect=5.0,
                read=instance_config.timeout_seconds,
                write=30.0,
                pool=30.0,
            ),
            limits=httpx.Limits(
                max_connections=instance_config.max_concurrent_requests,
                max_keepalive_connections=instance_config.max_concurrent_requests,
            ),
        )
        self._healthy = True
        self._last_health_check = 0
        self._models_cache: list[str] = []
        self._models_cache_time = 0
        self._models_cache_ttl = 10

    async def health_check(self) -> bool:
        """Check if Ollama instance is healthy."""
        try:
            response = await self.client.get("/api/tags", timeout=5.0)
            if response.status_code == 200:
                self._healthy = True
                self._last_health_check = time.time()
                return True
        except Exception as e:
            self._healthy = False
            logger.debug("Health check failed for %s: %s", self.base_url, e)
        return False

    async def get_models(self, force_refresh: bool = False) -> list[str]:
        """Get list of available models."""
        now = time.time()
        if not force_refresh and self._models_cache and (now - self._models_cache_time) < self._models_cache_ttl:
            return self._models_cache

        try:
            response = await self.client.get("/api/tags", timeout=10.0)
            response.raise_for_status()
            data = response.json()
            self._models_cache = [m["name"] for m in data.get("models", [])]
            self._models_cache_time = now
            return self._models_cache
        except Exception as e:
            logger.error("Failed to get models from %s: %s", self.base_url, e)
            return self._models_cache or []

    async def has_model(self, model_name: str) -> bool:
        """Check if model is available on this instance."""
        models = await self.get_models()
        # Normalize for comparison
        normalized = model_name.lower().strip()
        return any(m.lower() == normalized or m.lower().startswith(normalized) for m in models)

    async def generate(self, model: str, **kwargs) -> Dict[str, Any]:
        """Generate completion."""
        payload = {"model": model, **kwargs}
        response = await self.client.post("/api/generate", json=payload)
        response.raise_for_status()
        return response.json()

    async def chat(self, model: str, messages: list[dict]) -> Dict[str, Any]:
        """Chat completion."""
        payload = {"model": model, "messages": messages, "stream": False}
        response = await self.client.post("/api/chat", json=payload)
        response.raise_for_status()
        return response.json()

    async def embeddings(self, model: str, prompt: str) -> Dict[str, Any]:
        """Get embeddings."""
        payload = {"model": model, "prompt": prompt}
        response = await self.client.post("/api/embeddings", json=payload)
        response.raise_for_status()
        return response.json()

    async def generate_stream(self, model: str, **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream generate completion."""
        payload = {"model": model, "stream": True, **kwargs}
        async with self.client.stream("POST", "/api/generate", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip():
                    yield {"line": line}

    async def chat_stream(self, model: str, messages: list[dict]) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chat completion."""
        payload = {"model": model, "messages": messages, "stream": True}
        async with self.client.stream("POST", "/api/chat", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip():
                    yield {"line": line}

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()


class OllamaManager:
    """Manage multiple Ollama instances with routing and load balancing."""

    def __init__(self):
        self.clients: Dict[str, OllamaClient] = {}
        self._instances_config: Dict[str, Any] = {}
        self._initialize_clients()

    def _initialize_clients(self):
        """Initialize clients for configured Ollama instances."""
        # Map ports to instance names
        port_to_instance = {}
        for name, instance in settings.ollama_instances.items():
            self._instances_config[name] = instance
            self.clients[name] = OllamaClient(instance)
            port_to_instance[instance.port] = name

    async def health_check_all(self) -> Dict[str, bool]:
        """Health check all instances."""
        results = {}
        for name, client in self.clients.items():
            results[name] = await client.health_check()
        return results

    async def find_instance_for_model(self, model: str) -> Optional[OllamaClient]:
        """Find the right instance for a given model."""
        routing = settings.model_to_gpu_mapping
        
        # By priority, check the assigned instance first
        gpu_type = routing.get(model)
        if gpu_type and gpu_type in self.clients:
            client = self.clients[gpu_type]
            if await client.has_model(model):
                return client
        
        # Auto fallback: search all instances
        for name, client in self.clients.items():
            if await client.has_model(model):
                return client
        
        # Special handling: check if model is actually on the mapped instance
        if gpu_type and gpu_type in self.clients:
            client = self.clients[gpu_type]
            if await client.has_model(model):
                return client

        return None

    async def ensure_model_available(self, model: str) -> None:
        """Raise if model is not available on any instance."""
        # Check assigned instance first
        routing = settings.model_to_gpu_mapping
        gpu_type = routing.get(model)
        
        if gpu_type and gpu_type in self.clients:
            client = self.clients[gpu_type]
            if await client.has_model(model):
                return
            raise ModelNotAvailableError(model, gpu_type)

        # Fallback search
        for name, client in self.clients.items():
            if await client.has_model(model):
                return
        
        raise ModelNotFoundError(model)

    async def close(self) -> None:
        """Close all clients."""
        for client in self.clients.values():
            await client.close()


ollama_manager = OllamaManager()