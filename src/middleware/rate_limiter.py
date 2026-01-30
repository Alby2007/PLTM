"""Rate limiting middleware using Redis"""

from typing import Optional, Callable
from datetime import datetime
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from loguru import logger

from src.storage.redis_cache import RedisCache, RedisConfig


class RateLimitTier:
    """Rate limit tier configuration"""
    
    FREE = {
        "name": "free",
        "requests_per_hour": 100,
        "requests_per_day": 1000,
        "burst_size": 10,
    }
    
    PRO = {
        "name": "pro",
        "requests_per_hour": 1000,
        "requests_per_day": 10000,
        "burst_size": 50,
    }
    
    ENTERPRISE = {
        "name": "enterprise",
        "requests_per_hour": None,  # Unlimited
        "requests_per_day": None,   # Unlimited
        "burst_size": 100,
    }


class RateLimiter:
    """
    Rate limiting middleware using Redis.
    
    Features:
    - Per-user rate limits
    - Per-API-key rate limits
    - Sliding window algorithm
    - Tiered limits (free, pro, enterprise)
    - Burst protection
    - Custom limits per endpoint
    """
    
    def __init__(self, redis_cache: Optional[RedisCache] = None):
        """
        Initialize rate limiter.
        
        Args:
            redis_cache: Redis cache instance (creates new if None)
        """
        self.redis_cache = redis_cache or RedisCache(RedisConfig())
        logger.info("Rate limiter initialized")
    
    async def check_rate_limit(
        self,
        identifier: str,
        tier: dict = RateLimitTier.FREE,
        tenant_id: str = "default",
        endpoint: Optional[str] = None
    ) -> tuple[bool, dict]:
        """
        Check rate limit for identifier.
        
        Args:
            identifier: User ID or API key
            tier: Rate limit tier configuration
            tenant_id: Tenant identifier
            endpoint: Optional endpoint-specific limit
            
        Returns:
            Tuple of (allowed, rate_limit_info)
        """
        # Check hourly limit
        hourly_allowed, hourly_remaining = await self._check_window(
            identifier=identifier,
            limit=tier["requests_per_hour"],
            window=3600,  # 1 hour
            tenant_id=tenant_id,
            window_name="hourly"
        )
        
        # Check daily limit
        daily_allowed, daily_remaining = await self._check_window(
            identifier=identifier,
            limit=tier["requests_per_day"],
            window=86400,  # 24 hours
            tenant_id=tenant_id,
            window_name="daily"
        )
        
        # Check burst limit
        burst_allowed, burst_remaining = await self._check_burst(
            identifier=identifier,
            burst_size=tier["burst_size"],
            tenant_id=tenant_id
        )
        
        # Overall decision
        allowed = hourly_allowed and daily_allowed and burst_allowed
        
        rate_limit_info = {
            "tier": tier["name"],
            "hourly_limit": tier["requests_per_hour"],
            "hourly_remaining": hourly_remaining,
            "daily_limit": tier["requests_per_day"],
            "daily_remaining": daily_remaining,
            "burst_remaining": burst_remaining,
            "reset_time": self._get_reset_time(3600),  # Next hour
        }
        
        if not allowed:
            logger.warning(
                f"Rate limit exceeded for {identifier}: "
                f"hourly={hourly_allowed}, daily={daily_allowed}, burst={burst_allowed}"
            )
        
        return allowed, rate_limit_info
    
    async def _check_window(
        self,
        identifier: str,
        limit: Optional[int],
        window: int,
        tenant_id: str,
        window_name: str
    ) -> tuple[bool, int]:
        """
        Check rate limit for time window.
        
        Args:
            identifier: User ID or API key
            limit: Maximum requests (None = unlimited)
            window: Time window in seconds
            tenant_id: Tenant identifier
            window_name: Window name for logging
            
        Returns:
            Tuple of (allowed, remaining_requests)
        """
        # Unlimited tier
        if limit is None:
            return True, -1
        
        # Check rate limit
        allowed, remaining = await self.redis_cache.check_rate_limit(
            identifier=f"{identifier}:{window_name}",
            limit=limit,
            window=window,
            tenant_id=tenant_id
        )
        
        return allowed, remaining
    
    async def _check_burst(
        self,
        identifier: str,
        burst_size: int,
        tenant_id: str
    ) -> tuple[bool, int]:
        """
        Check burst protection (requests in last minute).
        
        Args:
            identifier: User ID or API key
            burst_size: Maximum burst size
            tenant_id: Tenant identifier
            
        Returns:
            Tuple of (allowed, remaining_burst)
        """
        allowed, remaining = await self.redis_cache.check_rate_limit(
            identifier=f"{identifier}:burst",
            limit=burst_size,
            window=60,  # 1 minute
            tenant_id=tenant_id
        )
        
        return allowed, remaining
    
    def _get_reset_time(self, window: int) -> str:
        """
        Calculate when rate limit resets.
        
        Args:
            window: Time window in seconds
            
        Returns:
            ISO timestamp of reset time
        """
        from datetime import timedelta
        reset_time = datetime.utcnow() + timedelta(seconds=window)
        return reset_time.isoformat()
    
    async def get_tier_for_user(
        self,
        user_id: str,
        tenant_id: str = "default"
    ) -> dict:
        """
        Get rate limit tier for user.
        
        In production, this would query user's subscription tier from database.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            
        Returns:
            Rate limit tier configuration
        """
        # TODO: Query from database
        # For now, return FREE tier
        return RateLimitTier.FREE
    
    async def reset_rate_limit(
        self,
        identifier: str,
        tenant_id: str = "default"
    ) -> None:
        """
        Reset rate limit for identifier.
        
        Args:
            identifier: User ID or API key
            tenant_id: Tenant identifier
        """
        await self.redis_cache.reset_rate_limit(identifier, tenant_id)
        logger.info(f"Reset rate limit for {identifier}")


class RateLimitMiddleware:
    """
    FastAPI middleware for rate limiting.
    
    Usage:
        app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)
    """
    
    def __init__(self, app, rate_limiter: RateLimiter):
        """
        Initialize middleware.
        
        Args:
            app: FastAPI application
            rate_limiter: Rate limiter instance
        """
        self.app = app
        self.rate_limiter = rate_limiter
    
    async def __call__(self, request: Request, call_next: Callable):
        """
        Process request with rate limiting.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
            
        Returns:
            Response
        """
        # Extract identifier (user_id or API key)
        identifier = await self._get_identifier(request)
        
        if not identifier:
            # No authentication, skip rate limiting
            return await call_next(request)
        
        # Get user's tier
        tier = await self.rate_limiter.get_tier_for_user(identifier)
        
        # Check rate limit
        allowed, rate_limit_info = await self.rate_limiter.check_rate_limit(
            identifier=identifier,
            tier=tier,
            endpoint=request.url.path
        )
        
        # Add rate limit headers to response
        response = await call_next(request) if allowed else None
        
        if not allowed:
            # Rate limit exceeded
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please try again later.",
                    "rate_limit": rate_limit_info
                },
                headers={
                    "X-RateLimit-Limit": str(rate_limit_info["hourly_limit"]),
                    "X-RateLimit-Remaining": str(rate_limit_info["hourly_remaining"]),
                    "X-RateLimit-Reset": rate_limit_info["reset_time"],
                    "Retry-After": "3600",
                }
            )
        
        # Add rate limit headers to successful response
        response.headers["X-RateLimit-Limit"] = str(rate_limit_info["hourly_limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_info["hourly_remaining"])
        response.headers["X-RateLimit-Reset"] = rate_limit_info["reset_time"]
        
        return response
    
    async def _get_identifier(self, request: Request) -> Optional[str]:
        """
        Extract user identifier from request.
        
        Args:
            request: FastAPI request
            
        Returns:
            User ID or API key
        """
        # Try to get from JWT token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            # TODO: Decode JWT and extract user_id
            return "user_from_jwt"
        
        # Try to get from API key header
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return api_key
        
        # No authentication
        return None


def create_rate_limit_dependency(
    rate_limiter: RateLimiter,
    tier: dict = RateLimitTier.FREE
):
    """
    Create FastAPI dependency for rate limiting.
    
    Usage:
        @app.get("/endpoint", dependencies=[Depends(rate_limit_dependency)])
        async def endpoint():
            return {"message": "success"}
    
    Args:
        rate_limiter: Rate limiter instance
        tier: Rate limit tier
        
    Returns:
        FastAPI dependency function
    """
    async def rate_limit_dependency(request: Request):
        """Check rate limit for request"""
        # Extract identifier
        identifier = request.state.user_id if hasattr(request.state, "user_id") else None
        
        if not identifier:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # Check rate limit
        allowed, rate_limit_info = await rate_limiter.check_rate_limit(
            identifier=identifier,
            tier=tier
        )
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(rate_limit_info["hourly_limit"]),
                    "X-RateLimit-Remaining": str(rate_limit_info["hourly_remaining"]),
                    "X-RateLimit-Reset": rate_limit_info["reset_time"],
                    "Retry-After": "3600",
                }
            )
        
        # Store rate limit info in request state
        request.state.rate_limit_info = rate_limit_info
    
    return rate_limit_dependency


# Global rate limiter instance
rate_limiter = RateLimiter()
