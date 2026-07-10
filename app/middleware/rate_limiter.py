import time
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as aioredis

class RedisRateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(
        self, 
        app, 
        redis_url: str = "redis://localhost:6379", 
        max_requests: int = 20, 
        window_seconds: int = 60
    ):
        super().__init__(app)
        # Initialize the asynchronous Redis client connection
        self.redis = aioredis.from_url(redis_url, decode_responses=True)
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Intercepts every incoming HTTP request packet before hitting the router layer.
        """
        # 🟢 1. Fast-Path Bypass: Skip checking rate limits entirely for chat short-polling
        exempt_paths = ["/api/v1/chat/history", "/static"]
        if any(request.url.path.startswith(path) for path in exempt_paths):
            return await call_next(request)

        # 2. Extract the unique identifier for the caller (Client IP address)
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        
        # Define a unique Redis key per user-endpoint pair
        redis_key = f"rate:{client_ip}:{path}"
        
        try:
            # 3. Increment the value in Redis atomically
            current_hits = await self.redis.incr(redis_key)
            
            # 4. If it's the very first hit in this window, set the TTL expiration
            if current_hits == 1:
                await self.redis.expire(redis_key, self.window_seconds)
                
            # 5. Check if the client has breached the threshold bounds
            if current_hits > self.max_requests:
                # Shield your backend by short-circuiting right here!
                return JSONResponse(
                    status_code=429,
                    content={
                        "status": "error",
                        "code": "rate_limited",
                        "message": "Too many requests. Slow down your talent search!"
                    }
                )
                
        except Exception as e:
            # Defensive Fallback: If Redis crashes/fails, log it and let traffic through
            # so your app doesn't break for real users due to a cache failure.
            print(f"Rate limiter tracking failure safeguard triggered: {e}")
            return await call_next(request)

        # Everything is clear! Pass the request along up the router chain.
        response = await call_next(request)
        return response