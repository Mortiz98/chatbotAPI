import time
from collections import defaultdict
from typing import Dict, List, Tuple
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from core.config import settings
from core.logging_config import logger


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.
    Tracks requests per client IP within a time window.
    """

    def __init__(self, app):
        super().__init__(app)
        # Store: {client_ip: [(timestamp1), (timestamp2), ...]}
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self.max_requests = settings.RATE_LIMIT_REQUESTS
        self.window = settings.RATE_LIMIT_WINDOW

    def _clean_old_requests(self, client_ip: str):
        """Remove requests outside the time window."""
        current_time = time.time()
        self.requests[client_ip] = [
            req_time
            for req_time in self.requests[client_ip]
            if current_time - req_time < self.window
        ]

    def _is_rate_limited(self, client_ip: str) -> bool:
        """Check if client has exceeded rate limit."""
        self._clean_old_requests(client_ip)
        return len(self.requests[client_ip]) >= self.max_requests

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and documentation
        path = request.url.path
        if path in ["/", "/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Get client IP
        client_ip = request.headers.get("X-Forwarded-For", request.client.host)
        if client_ip and "," in client_ip:
            client_ip = client_ip.split(",")[0].strip()

        # Check rate limit
        if self._is_rate_limited(client_ip):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.max_requests} requests per {self.window} seconds.",
            )

        # Record request
        self.requests[client_ip].append(time.time())

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining = max(0, self.max_requests - len(self.requests[client_ip]))
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(self.window)

        return response
