"""
Better Auth Middleware for FastAPI Backend

This module provides authentication middleware for validating Better Auth sessions.
Better Auth runs as a separate Node.js microservice and shares the Neon database
with this FastAPI backend.

Key Features:
- Cookie-based session validation (httpOnly cookies)
- Async database queries for session and user data
- FastAPI dependencies for protected and optional auth routes
- Timezone-aware datetime comparisons for session expiration

Architecture:
- Better Auth service handles authentication (sign in/up/out)
- FastAPI validates sessions by reading cookies + querying shared database
- All services share the same Neon PostgreSQL database

Usage:
    from modules.auth_middleware import get_current_user, get_optional_user, AuthUser

    @app.get("/api/me")
    async def get_me(user: AuthUser = Depends(get_current_user)):
        return {"user": user.model_dump()}

    @app.get("/api/dashboard")
    async def dashboard(user: Optional[AuthUser] = Depends(get_optional_user)):
        # user is None if not authenticated
        pass
"""

from fastapi import Request, HTTPException, Depends
from typing import Optional, Tuple
from datetime import datetime, timezone

from .database import get_connection
from .orch_database_models import AuthUser, AuthSession

# Cookie names used by Better Auth
# In production (HTTPS), Better Auth uses __Secure- prefix for enhanced security
# In development (HTTP), the prefix is not used
SESSION_COOKIE_NAME = "better-auth.session_token"
SESSION_COOKIE_NAME_SECURE = "__Secure-better-auth.session_token"


async def get_session_from_cookie(request: Request) -> Optional[str]:
    """
    Extract session token from Better Auth cookie.

    Better Auth stores tokens in format "tokenId.signature" in cookies,
    but only the tokenId is stored in the database. We extract the tokenId
    (part before the dot) for database lookup.

    In production (HTTPS), cookies are prefixed with __Secure- for security.
    We check both variants to support both environments.

    Args:
        request: FastAPI Request object

    Returns:
        Session token ID string if present, None otherwise

    Example:
        >>> token = await get_session_from_cookie(request)
        >>> if token:
        ...     print(f"Found session token: {token[:20]}...")
    """
    # Try secure cookie first (production), then fall back to non-secure (development)
    cookie_value = request.cookies.get(SESSION_COOKIE_NAME_SECURE)
    if not cookie_value:
        cookie_value = request.cookies.get(SESSION_COOKIE_NAME)
    if not cookie_value:
        return None

    # Better Auth format: "tokenId.signature" - extract just the tokenId
    # The signature part is used for cryptographic verification by Better Auth
    # but we only need the tokenId for database lookup
    if "." in cookie_value:
        return cookie_value.split(".")[0]
    return cookie_value


async def validate_session(token: str) -> Optional[Tuple[AuthSession, AuthUser]]:
    """
    Validate session token and return session + user if valid.

    Queries the shared database to:
    1. Find a session with the given token
    2. Check that the session hasn't expired
    3. Join with the user table to get user data

    Args:
        token: Session token from cookie

    Returns:
        Tuple of (AuthSession, AuthUser) if valid, None if invalid/expired

    Example:
        >>> result = await validate_session("abc123...")
        >>> if result:
        ...     session, user = result
        ...     print(f"Valid session for {user.email}")
        ... else:
        ...     print("Invalid or expired session")
    """
    async with get_connection() as conn:
        # Query session with user join
        # IMPORTANT: Use timezone-aware datetime for comparison
        # NOTE: Better Auth uses camelCase column names (expiresAt, userId, etc.)
        row = await conn.fetchrow(
            """
            SELECT
                s.id as session_id,
                s."userId" as user_id,
                s.token,
                s."expiresAt" as expires_at,
                s."ipAddress" as ip_address,
                s."userAgent" as user_agent,
                s."createdAt" as session_created_at,
                s."updatedAt" as session_updated_at,
                u.id as uid,
                u.name,
                u.email,
                u."emailVerified" as email_verified,
                u.image,
                u."createdAt" as user_created_at,
                u."updatedAt" as user_updated_at
            FROM session s
            JOIN "user" u ON s."userId" = u.id
            WHERE s.token = $1
              AND s."expiresAt" > $2
        """,
            token,
            datetime.now(timezone.utc),
        )

        if not row:
            return None

        # Parse session data
        session = AuthSession(
            id=row["session_id"],
            user_id=row["user_id"],
            token=row["token"],
            expires_at=row["expires_at"],
            ip_address=row["ip_address"],
            user_agent=row["user_agent"],
            created_at=row["session_created_at"],
            updated_at=row["session_updated_at"],
        )

        # Parse user data
        user = AuthUser(
            id=row["user_id"],
            name=row["name"],
            email=row["email"],
            email_verified=row["email_verified"],
            image=row["image"],
            created_at=row["user_created_at"],
            updated_at=row["user_updated_at"],
        )

        return session, user


async def get_current_user(request: Request) -> AuthUser:
    """
    FastAPI dependency to get current authenticated user.

    Use this as a dependency in protected routes that require authentication.
    Raises HTTP 401 if user is not authenticated or session is invalid/expired.

    Args:
        request: FastAPI Request object

    Returns:
        AuthUser: Authenticated user data

    Raises:
        HTTPException: 401 if not authenticated or session invalid

    Example:
        >>> @app.get("/api/me")
        ... async def get_me(user: AuthUser = Depends(get_current_user)):
        ...     return {"user": user.model_dump()}
    """
    token = await get_session_from_cookie(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await validate_session(token)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    _, user = result
    return user


async def get_optional_user(request: Request) -> Optional[AuthUser]:
    """
    FastAPI dependency to get current user if authenticated, None otherwise.

    Use this as a dependency in routes that have optional authentication.
    Does NOT raise exceptions - returns None if user is not authenticated.

    Args:
        request: FastAPI Request object

    Returns:
        AuthUser if authenticated, None otherwise

    Example:
        >>> @app.get("/api/dashboard")
        ... async def dashboard(user: Optional[AuthUser] = Depends(get_optional_user)):
        ...     if user:
        ...         return {"message": f"Welcome {user.name}"}
        ...     else:
        ...         return {"message": "Welcome guest"}
    """
    token = await get_session_from_cookie(request)
    if not token:
        return None

    result = await validate_session(token)
    if not result:
        return None

    _, user = result
    return user
