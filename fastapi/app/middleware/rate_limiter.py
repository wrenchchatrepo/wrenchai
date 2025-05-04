"""
Rate limiting middleware for FastAPI using Redis and token bucket algorithm.
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Callable, Dict, Optional
import time
import redis
from datetime import datetime
import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class RateLimitConfig(BaseModel):
    """Configuration for rate limiting."""
    requests_per_minute: int = 60
    burst_size: int = 100
    key_prefix: str = "ratelimit:"

class RateLimiter:
    """Rate limiter implementation using token bucket algorithm."""
    
    def __init__(
        self,
        redis_url: str,
        config: Optional[RateLimitConfig] = None
    ):
        """Initialize rate limiter.
        
        Args:
            redis_url: Redis connection URL
            config: Rate limiting configuration
        """
        self.redis = redis.from_url(redis_url)
        self.config = config or RateLimitConfig()
        
        # Convert requests per minute to requests per second
        self.rate = self.config.requests_per_minute / 60.0
        self.burst = self.config.burst_size
        self.key_prefix = self.config.key_prefix
    
    def _get_tokens(self, key: str) -> Dict[str, float]:
        """Get current token count and last update time.
        
        Args:
            key: Rate limit key
            
        Returns:
            Dict containing tokens and last update time
        """
        data = self.redis.hgetall(key)
        if not data:
            return {"tokens": float(self.burst), "last_update": time.time()}
        return {
            "tokens": float(data[b"tokens"]),
            "last_update": float(data[b"last_update"])
        }
    
    def _update_tokens(
        self,
        key: str,
        tokens: float,
        last_update: float
    ) -> None:
        """Update token count and last update time.
        
        Args:
            key: Rate limit key
            tokens: New token count
            last_update: New last update time
        """
        self.redis.hmset(key, {
            "tokens": tokens,
            "last_update": last_update
        })
        # Set expiry to clean up old entries
        self.redis.expire(key, 300)  # 5 minutes
    
    async def is_allowed(
        self,
        key: str,
        tokens_needed: int = 1
    ) -> tuple[bool, Dict[str, float]]:
        """Check if request is allowed under rate limit.
        
        Args:
            key: Rate limit key
            tokens_needed: Number of tokens needed for request
            
        Returns:
            Tuple of (allowed, rate limit info)
        """
        key = f"{self.key_prefix}{key}"
        current = self._get_tokens(key)
        
        # Calculate token replenishment
        now = time.time()
        time_passed = now - current["last_update"]
        new_tokens = current["tokens"] + time_passed * self.rate
        
        # Cap tokens at burst size
        tokens = min(new_tokens, self.burst)
        
        # Check if enough tokens and update
        allowed = tokens >= tokens_needed
        if allowed:
            tokens -= tokens_needed
        
        self._update_tokens(key, tokens, now)
        
        return allowed, {
            "remaining": int(tokens),
            "reset": int(now + (self.burst - tokens) / self.rate),
            "limit": self.config.requests_per_minute
        }

class RateLimitMiddleware:
    """Middleware for rate limiting FastAPI requests."""
    
    def __init__(
        self,
        app: FastAPI,
        redis_url: str,
        config: Optional[RateLimitConfig] = None
    ):
        """Initialize middleware.
        
        Args:
            app: FastAPI application
            redis_url: Redis connection URL
            config: Rate limiting configuration
        """
        self.app = app
        self.limiter = RateLimiter(redis_url, config)
    
    async def get_key(self, request: Request) -> str:
        """Get rate limit key for request.
        
        Args:
            request: FastAPI request
            
        Returns:
            Rate limit key
        """
        # Default to IP-based limiting
        key = request.client.host
        
        # If authenticated, use user ID
        if hasattr(request.state, "user_id"):
            key = f"user:{request.state.user_id}"
        
        return key
    
    async def __call__(
        self,
        request: Request,
        call_next: Callable
    ) -> JSONResponse:
        """Process request with rate limiting.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
            
        Returns:
            Response
        """
        key = await self.get_key(request)
        allowed, info = await self.limiter.is_allowed(key)
        
        # Set rate limit headers
        headers = {
            "X-RateLimit-Limit": str(info["limit"]),
            "X-RateLimit-Remaining": str(info["remaining"]),
            "X-RateLimit-Reset": str(info["reset"])
        }
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for {key}")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests",
                    "retry_after": info["reset"] - int(time.time())
                },
                headers=headers
            )
        
        response = await call_next(request)
        
        # Add headers to response
        for name, value in headers.items():
            response.headers[name] = value
        
        return response

def setup_rate_limiting(
    app: FastAPI,
    redis_url: str,
    config: Optional[RateLimitConfig] = None
) -> None:
    """Set up rate limiting for FastAPI application.
    
    Args:
        app: FastAPI application
        redis_url: Redis connection URL
        config: Rate limiting configuration
    """
    middleware = RateLimitMiddleware(app, redis_url, config)
    app.middleware("http")(middleware.__call__) 