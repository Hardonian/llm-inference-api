"""Shared pytest fixtures.

The big problem: the running app binds an async Redis client at import time,
then ``fastapi.testclient.TestClient`` opens a fresh event loop per request.
That makes ``redis.asyncio`` raise ``RuntimeError: Event loop is closed`` on
the second request through the RateLimitMiddleware.

We solve it by patching the rate limiter to be a no-op for the duration of
the test session. The middleware logic itself stays exercised in production.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make repo root importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

# IMPORTANT: must come AFTER sys.path tweak so the app package resolves.
import app.middleware.rate_limit as _rl  # noqa: E402


async def _fake_check_rate_limit(self, key: str, limit: int, window: int, burst: int = 0):
    """No-op rate-limit check used during tests."""
    return True, {
        "X-RateLimit-Limit": str(limit + burst),
        "X-RateLimit-Remaining": "999",
        "X-RateLimit-Reset": "0",
    }


@pytest.fixture(autouse=True, scope="session")
def _disable_rate_limit():
    """Patch the bound limiter so tests don't reach Redis."""
    orig = _rl.RateLimiter.check_rate_limit
    _rl.RateLimiter.check_rate_limit = _fake_check_rate_limit
    yield
    _rl.RateLimiter.check_rate_limit = orig


@pytest.fixture(scope="session")
def auth_token():
    """Dashboard token used by auth-required contract tests."""
    from app.utils.auth import get_dashboard_token
    return get_dashboard_token()


@pytest.fixture
def auth_header(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}