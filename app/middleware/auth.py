"""Authentication and authorization middleware."""
import time
from typing import Optional

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.core.exceptions import AuthenticationError, AuthorizationError


security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Extract and validate JWT token from Authorization header."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        request.state.user = payload
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """Extract user from token if present, otherwise return None.

    Accepts either a JWT (validated against secret) or a shared dashboard token.
    """
    if not credentials:
        return None

    token = credentials.credentials
    # Shared dashboard token (auto-generated)
    try:
        from app.utils.auth import get_dashboard_token as _gdt
        if token == _gdt():
            payload = {"sub": "default", "name": "Scott", "scopes": ["admin", "dashboard"], "auth_mode": "shared_token"}
            request.state.user = payload
            return payload
    except Exception:
        pass

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        request.state.user = payload
        return payload
    except jwt.InvalidTokenError:
        return None


def create_access_token(data: dict, expires_delta: Optional[int] = None) -> str:
    """Create a new JWT access token."""
    to_encode = data.copy()
    expire_minutes = expires_delta or settings.access_token_expire_minutes
    expire = time.time() + (expire_minutes * 60)
    to_encode.update({"exp": int(expire), "type": "access"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(data: dict) -> str:
    """Create a new JWT refresh token."""
    to_encode = data.copy()
    expire = time.time() + (settings.refresh_token_expire_days * 24 * 60 * 60)
    to_encode.update({"exp": int(expire), "type": "refresh"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def verify_refresh_token(token: str) -> dict:
    """Verify a refresh token and return payload."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "refresh":
            raise AuthenticationError("Invalid token type")
        return payload
    except jwt.InvalidTokenError as e:
        raise AuthenticationError(f"Invalid refresh token: {e}")


async def require_permission(permission: str, user: dict = Depends(get_current_user)) -> dict:
    """Require a specific permission for the current user."""
    user_permissions = user.get("permissions", [])
    if permission not in user_permissions and "admin" not in user_permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission '{permission}' required",
        )
    return user


async def require_role(role: str, user: dict = Depends(get_current_user)) -> dict:
    """Require a specific role for the current user."""
    user_roles = user.get("roles", [])
    if role not in user_roles and "admin" not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{role}' required",
        )
    return user


def get_tenant_id(
    request: Request,
    user: Optional[dict] = Depends(get_current_user_optional),
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> str:
    """Get tenant ID from header or user claims."""
    if x_tenant_id:
        return x_tenant_id
    if user:
        return user.get("tenant_id", "default")
    return "default"