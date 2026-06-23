"""Security middleware for headers, audit logging, and threat protection."""
import time
import uuid
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

logger = logging.getLogger("security")

# Security headers configuration
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://fonts.googleapis.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: blob:; "
        "connect-src 'self' ws: wss: http://localhost:*; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    ),
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Server": "AI-Lab",
}

# Paths that don't require authentication
PUBLIC_PATHS = {
    "/health",
    "/healthz",
    "/metrics",
    "/",
    "/dashboard",
    "/static/",
    "/favicon.ico",
    "/api/improve-prompt",
    "/api/generate",
    "/api/tools/custom",
    "/api/mcp/agents",
    "/api/mcp/run",
    "/api/views",
    "/api/jobs",
    "/api/achievements",
    "/api/system/snapshot",
    "/api/system/self-heal",
    "/api/system/watchdog",
    "/api/money/leads",
    "/api/cooperator/briefing",
    "/api/cooperator/run",
    "/api/cooperator/repos",
    "/api/private-creations",
    "/gpu-status",
    "/ollama-status",
    "/api/ollama/route",
    "/api/comfy/workflows",
    "/api/comfy/queue",
    "/api/comfy/models",
    "/api/comfy/nodes",
    "/api/comfy/view",
    "/api/upload",
    "/api/upscale",
    "/api/variations",
    "/api/cleanup",
    "/api/backup",
    "/api/heal",
    "/api/report",
    "/api/security/scan",
    "/api/security/audit",
    "/api/security/stats",
    "/api/disk/rescue",
    "/api/models/truth",
    "/api/dashboard/smoke",
    "/api/dashboard/logs",
    "/api/workstation/op",
    "/api/epic/dashboard",
    "/api/trends",
    "/api/insights",
    "/api/p50",
    "/ws",
    "/ws/epic",
    "/api/users/me",
    "/api/users",
    "/api/operator/repos",
    "/api/operator/next-action",
    "/api/workforce/status",
    "/api/workforce/reports",
    "/api/verification/latest",
    "/api/verification/record",
    "/api/auth/me",
    "/api/workflows/productize",
    "/bootstrap",
    "/offer/",
    "/offer/{slug}",
    "/offer/{slug}/checkout",
    "/offers",
    "/stripe/webhook",
}

# Paths that require admin role
ADMIN_PATHS = {
    "/api/security/", "/api/comfy/download", "/api/comfy/install-node",
    "/api/gpu/", "/api/process/", "/api/security/",
}


class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for security headers, audit logging, and request validation."""

    def __init__(self, app, enable_auth: bool = True):
        super().__init__(app)
        self.enable_auth = enable_auth

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        
        # Allow WebSocket upgrade requests to pass through without auth check
        # Auth will be validated in the WebSocket handler itself
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)

        def add_security_headers(response: Response) -> Response:
            for header, value in SECURITY_HEADERS.items():
                response.headers[header] = value
            return response

        path = request.url.path

        def _is_public(p: str) -> bool:
            """Match public path exactly, or as a prefix when the rule ends with '/'.
            Prevents '/' from being a wildcard. Export endpoints are never public."""
            if p == path:
                return True
            if p == "/":
                return False
            if p.endswith("/"):
                return True if path.startswith(p) else False
            if "/export" in path:
                return False
            if path.startswith(p + "/"):
                return True
            return False

        public_dashboard_read = request.method == "GET" and path.startswith("/api/gpu/") and path.endswith("/processes")
        if self.enable_auth and not public_dashboard_read and not any(_is_public(p) for p in PUBLIC_PATHS):
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Authentication required", "error": "UNAUTHORIZED"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
            token = auth_header[7:].strip()
            try:
                from app.utils.auth import get_dashboard_token as _gdt
                _dash_tok = _gdt()
                if token == _dash_tok:
                    pass
                else:
                    import jwt as _jwt
                    from app.config import settings as _settings
                    _jwt.decode(token, _settings.secret_key, algorithms=[_settings.algorithm])
            except Exception as _exc:
                return JSONResponse(
                    status_code=401,
                    content={"detail": f"Invalid token: {_exc}", "error": "INVALID_AUTH"},
                )

        content_length = request.headers.get("Content-Length")
        max_request_bytes = 30 * 1024 * 1024 * 1024 if path.startswith("/api/upload") else 10 * 1024 * 1024
        if content_length and int(content_length) > max_request_bytes:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request too large", "error": "PAYLOAD_TOO_LARGE"},
            )

        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(f"[{request_id}] Request failed: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "error": "INTERNAL_ERROR"},
            )

        response = add_security_headers(response)
        duration = time.time() - start_time
        await self._audit_log(request, response, duration, request_id)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration:.3f}s"

        return response

    async def _audit_log(self, request: Request, response: Response, duration: float, request_id: str):
        path = request.url.path
        method = request.method
        status = response.status_code
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "unknown")[:100]

        user_info = "anonymous"
        if hasattr(request.state, "user") and request.state.user:
            user_info = request.state.user.get("sub", "unknown")

        log_data = {
            "request_id": request_id,
            "method": method,
            "path": path,
            "status": status,
            "duration_ms": round(duration * 1000, 2),
            "client_ip": client_ip,
            "user": user_info,
            "user_agent": user_agent,
        }

        if status >= 500:
            logger.error(f"AUDIT ERROR: {log_data}")
        elif status >= 400:
            logger.warning(f"AUDIT WARN: {log_data}")
        else:
            logger.info(f"AUDIT: {log_data}")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enhanced rate limiting with per-IP and per-user tracking."""

    def __init__(self, app, requests_per_minute: int = 60, burst: int = 10):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst = burst
        self.ip_buckets: dict = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        minute = int(now / 60)

        if len(self.ip_buckets) > 10000:
            self.ip_buckets = {
                k: v for k, v in self.ip_buckets.items()
                if v["minute"] >= minute - 2
            }

        bucket_key = f"{client_ip}:{minute}"
        bucket = self.ip_buckets.get(bucket_key, {"count": 0, "minute": minute})

        bucket["count"] += 1
        self.ip_buckets[bucket_key] = bucket

        if bucket["count"] > self.requests_per_minute + self.burst:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded", "error": "RATE_LIMITED"},
                headers={
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str((minute + 1) * 60),
                    "Retry-After": "60",
                },
            )

        response = await call_next(request)
        remaining = max(0, self.requests_per_minute + self.burst - bucket["count"])
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute + self.burst)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str((minute + 1) * 60)

        return response


class CORSMiddleware(BaseHTTPMiddleware):
    """CORS middleware with strict origin checking for local development."""

    def __init__(self, app, allowed_origins: Optional[list] = None):
        super().__init__(app)
        self.allowed_origins = allowed_origins or [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8000",
            "http://localhost:8188",
            "http://localhost:3002",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8000",
            "http://127.0.0.1:8188",
            "http://127.0.0.1:3002",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        origin = request.headers.get("Origin")

        if origin and origin not in self.allowed_origins:
            return JSONResponse(
                status_code=403,
                content={"detail": "Origin not allowed", "error": "CORS_FORBIDDEN"},
            )

        response = await call_next(request)

        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Request-ID, X-Tenant-ID"

        return response