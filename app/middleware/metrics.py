"""Prometheus metrics middleware."""
import logging
import time
from typing import Callable

from fastapi import Request, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

logger = logging.getLogger("llm-inference-api")


# Metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

http_request_size_bytes = Histogram(
    "http_request_size_bytes",
    "HTTP request size in bytes",
    ["method", "endpoint"],
    buckets=[100, 1000, 10000, 100000, 1000000, 10000000],
)

http_response_size_bytes = Histogram(
    "http_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "endpoint"],
    buckets=[100, 1000, 10000, 100000, 1000000, 10000000],
)

active_requests = Gauge(
    "http_active_requests",
    "Number of active HTTP requests",
    ["method", "endpoint"],
)

ollama_requests_total = Counter(
    "ollama_requests_total",
    "Total requests to Ollama instances",
    ["instance", "model", "status"],
)

ollama_request_duration_seconds = Histogram(
    "ollama_request_duration_seconds",
    "Ollama request duration in seconds",
    ["instance", "model"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
)

ollama_active_connections = Gauge(
    "ollama_active_connections",
    "Active connections to Ollama instances",
    ["instance"],
)

model_load_duration_seconds = Histogram(
    "model_load_duration_seconds",
    "Model load duration in seconds",
    ["instance", "model"],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
)

token_usage_total = Counter(
    "token_usage_total",
    "Total tokens used",
    ["model", "type"],  # type: prompt, completion, total
)

rate_limit_exceeded_total = Counter(
    "rate_limit_exceeded_total",
    "Total rate limit exceeded events",
    ["key_type"],  # apikey, ip
)

auth_failures_total = Counter(
    "auth_failures_total",
    "Total authentication failures",
    ["reason"],  # missing_token, invalid_token, expired_token
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Allow WebSocket upgrade requests to pass through without blocking
        is_ws = request.headers.get("upgrade", "").lower() == "websocket"
        path = request.url.path
        logger.debug(f"metrics_middleware: path={path}, is_ws={is_ws}")
        if is_ws:
            logger.debug(f"metrics_middleware: SKIPPING for WS path={path}")
            return await call_next(request)
        if not settings.metrics_enabled:
            return await call_next(request)

        method = request.method
        endpoint = request.url.path

        # Skip metrics for metrics endpoint
        if endpoint == "/metrics":
            return await call_next(request)

        # Track active requests
        active_requests.labels(method=method, endpoint=endpoint).inc()

        start_time = time.time()
        request_size = 0
        if request.headers.get("content-length"):
            request_size = int(request.headers["content-length"])

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Record metrics
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=response.status_code,
            ).inc()

            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration)

            if request_size:
                http_request_size_bytes.labels(
                    method=method,
                    endpoint=endpoint,
                ).observe(request_size)

            # Get response size
            response_size = 0
            if hasattr(response, "body"):
                response_size = len(response.body)
            elif response.headers.get("content-length"):
                response_size = int(response.headers["content-length"])

            if response_size:
                http_response_size_bytes.labels(
                    method=method,
                    endpoint=endpoint,
                ).observe(response_size)

            return response

        except Exception as e:
            duration = time.time() - start_time
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=500,
            ).inc()
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration)
            raise

        finally:
            active_requests.labels(method=method, endpoint=endpoint).dec()


def metrics_endpoint() -> Response:
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)