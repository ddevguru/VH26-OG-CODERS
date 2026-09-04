import time
from collections import defaultdict
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from packages.saas.config import settings


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = None):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute or settings.rate_limit_requests_per_minute
        self.client_requests = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Exclude docs and open health check routes
        if request.url.path in ["/docs", "/openapi.json", "/redoc", "/", "/health"]:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        auth_header = request.headers.get("Authorization", "")
        identifier = f"{client_ip}:{auth_header[:20]}"

        now = time.time()
        window_start = now - 60.0

        # Clean old timestamps
        timestamps = [ts for ts in self.client_requests[identifier] if ts > window_start]
        self.client_requests[identifier] = timestamps

        if len(timestamps) >= self.requests_per_minute:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded. Please try again later."},
                headers={
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(now + 60)),
                },
            )

        self.client_requests[identifier].append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            self.requests_per_minute - len(self.client_requests[identifier])
        )
        return response
