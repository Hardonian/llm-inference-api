"""Rate limiting middleware using Redis."""
import time
from typing import Optional

import redis.asyncio as redis
from fastapi import Depends, Header, HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


class RateLimiter:
    """Token bucket rate limiter using Redis."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window: int,
        burst: int = 0,
    ) -> tuple[bool, dict]:
        """
        Check if request is within rate limit.

        Returns (allowed, headers_dict)
        """
        current_time = int(time.time())
        window_start = current_time - window

        # Clean old entries
        await self.redis.zremrangebyscore(key, 0, window_start)

        # Get current count
        current_count = await self.redis.zcard(key)

        # Calculate effective limit (burst allows temporary exceed)
        effective_limit = limit + burst

        if current_count >= effective_limit:
            # Get oldest entry to calculate retry-after
            oldest = await self.redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                retry_after = int(oldest[0][1]) + window - current_time
            else:
                retry_after = window
            return False, {
                "X-RateLimit-Limit": str(effective_limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(current_time + retry_after),
                "Retry-After": str(retry_after),
            }

        # Add current request
        await self.redis.zadd(key, {str(current_time): current_time})
        await self.redis.expire(key, window + 1)

        remaining = max(0, effective_limit - current_count - 1)
        return True, {
            "X-RateLimit-Limit": str(effective_limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(current_time + window),
        }


async def get_redis_client() -> redis.Redis:
    """Get Redis client for rate limiting."""
    return redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )


async def rate_limit_dependency(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    redis_client: redis.Redis = Depends(get_redis_client),
) -> dict:
    """Dependency to check rate limits per API key or IP."""
    limiter = RateLimiter(redis_client)

    # Use API key if provided, otherwise IP
    if x_api_key:
        key = f"ratelimit:apikey:{x_api_key}"
    else:
        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:ip:{client_ip}"

    allowed, headers = await limiter.check_rate_limit(
        key=key,
        limit=settings.rate_limit_requests_per_minute,
        window=60,
        burst=settings.rate_limit_burst,
    )

    # Add headers to response
    request.state.rate_limit_headers = headers

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers=headers,
        )

    return {"key": key, "headers": headers}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Global rate limiting middleware."""

    def __init__(self, app, redis_client: Optional[redis.Redis] = None):
        super().__init__(app)
        self.redis_client = redis_client
        self.limiter = RateLimiter(redis_client) if redis_client else None

    async def dispatch(self, request: Request, call_next):
        if not self.limiter:
            # Initialize if not provided
            if not self.redis_client:
                self.redis_client = redis.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                self.limiter = RateLimiter(self.redis_client)

        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/healthz", "/metrics"]:
            return await call_next(request)

        # Use API key or IP
        api_key = request.headers.get("X-API-Key")
        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{'apikey' if api_key else 'ip'}:{api_key or client_ip}"

        allowed, headers = await self.limiter.check_rate_limit(
            key=key,
            limit=settings.rate_limit_requests_per_minute,
            window=60,
            burst=settings.rate_limit_burst,
        )

        if not allowed:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded", "error_code": "RATE_LIMIT_EXCEEDED"},
                headers=headers,
            )

        response = await call_next(request)
        # Add rate limit headers to response
        for k, v in headers.items():
            response.headers[k] = v
        return response