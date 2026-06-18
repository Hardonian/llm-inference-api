"""Usage tracking for LLM API requests."""
import time
from typing import Optional
import redis.asyncio as redis
from structlog import get_logger

from app.config import settings

logger = get_logger(__name__)


class UsageTracker:
    """Track API usage with Redis."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.enabled = settings.usage_tracking_enabled

    async def record_request(
        self,
        user_id: Optional[str],
        api_key: Optional[str],
        model: str,
        instance: str,
        prompt_tokens: int,
        completion_tokens: int,
        duration_ms: float,
        status: str = "success",
    ) -> None:
        if not self.enabled:
            return

        timestamp = int(time.time())
        day = time.strftime("%Y-%m-%d", time.gmtime(timestamp))

        key_user = f"usage:user:{user_id or 'anon'}:{day}"
        key_model = f"usage:model:{model}:{day}"
        key_instance = f"usage:instance:{instance}:{day}"
        key_global = f"usage:global:{day}"

        pipeline = self.redis.pipeline()

        # User usage
        pipeline.hincrby(key_user, "requests", 1)
        pipeline.hincrby(key_user, "prompt_tokens", prompt_tokens)
        pipeline.hincrby(key_user, "completion_tokens", completion_tokens)
        pipeline.hincrby(key_user, f"status:{status}", 1)

        # Model usage
        pipeline.hincrby(key_model, "requests", 1)
        pipeline.hincrby(key_model, "prompt_tokens", prompt_tokens)
        pipeline.hincrby(key_model, "completion_tokens", completion_tokens)

        # Instance usage
        pipeline.hincrby(key_instance, "requests", 1)
        pipeline.hincrby(key_instance, "duration_ms", int(duration_ms))

        # Global usage
        pipeline.hincrby(key_global, "requests", 1)
        pipeline.hincrby(key_global, "prompt_tokens", prompt_tokens)
        pipeline.hincrby(key_global, "completion_tokens", completion_tokens)

        # Expire after retention period
        retention = settings.usage_retention_days + 1
        for key in [key_user, key_model, key_instance, key_global]:
            pipeline.expire(key, retention * 86400)

        await pipeline.execute()

    async def get_usage_summary(self, user_id: Optional[str] = None, days: int = 7) -> dict:
        if not self.enabled:
            return {"enabled": False}
        result = {"enabled": True}
        # In production, this would aggregate across days
        # Here we return the current day's stats as a sample
        today = time.strftime("%Y-%m-%d")
        prefix = f"usage:user:{user_id or 'anon'}:{today}"
        data = await self.redis.hgetall(prefix)
        if data:
            result["today"] = {k: int(v) for k, v in data.items()}
        return result