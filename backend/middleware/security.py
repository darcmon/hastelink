from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeaderMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to every response.

    BaseHTTPMiddleware wraps your entire app. Every request passes through
    here — public routes, admin routes, even 404s. The flow is:

    Request comes in → this middleware runs → your route handles it →
    response comes back through here → headers get added → sent to client
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response
