"""RateLimitMiddleware — rate limiting InMemory para endpoints del módulo servers.

Reglas (RNF-07):
- Health check  (/servers/{id}/health): máx 10 req/min  por (user_id, server_id)
- Ad-hoc exec   (/servers/{id}/exec):   máx 30 req/hora por user_id

Implementación InMemory v1. Migrar a Valkey Streams en v2.
Devuelve 429 Too Many Requests con header Retry-After (segundos) al superar el límite.
"""
import re
import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# Patrones de rutas sujetas a rate limit
_HEALTH_RE = re.compile(r"^/api/v1/servers/([^/]+)/health$")
_EXEC_RE = re.compile(r"^/api/v1/servers/([^/]+)/exec$")

# Configuración de límites
_HEALTH_LIMIT = 10
_HEALTH_WINDOW = 60        # segundos (1 minuto)
_EXEC_LIMIT = 30
_EXEC_WINDOW = 3600        # segundos (1 hora)


class _InMemoryCounter:
    """Contador de solicitudes con ventana deslizante simple."""

    def __init__(self) -> None:
        # key → (count, window_start)
        self._store: dict[str, tuple[int, float]] = defaultdict(lambda: (0, 0.0))

    def check_and_increment(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        """Comprueba si la clave supera el límite y, si no, incrementa.

        Returns:
            (allowed, retry_after_seconds)
        """
        now = time.monotonic()
        count, window_start = self._store[key]

        if now - window_start >= window:
            # Ventana expirada: reiniciar
            count = 0
            window_start = now

        if count >= limit:
            retry_after = int(window - (now - window_start)) + 1
            return False, retry_after

        self._store[key] = (count + 1, window_start)
        return True, 0


_counter = _InMemoryCounter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware Starlette que aplica rate limiting a endpoints del módulo servers."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Evalúa la solicitud contra las reglas de rate limiting.

        Rutas no sujetas a rate limit pasan directamente al siguiente handler.
        """
        path = request.url.path
        user_id = request.headers.get("X-User-Id", "anonymous")

        health_match = _HEALTH_RE.match(path)
        exec_match = _EXEC_RE.match(path)

        if health_match and request.method == "GET":
            server_id = health_match.group(1)
            key = f"health:{user_id}:{server_id}"
            allowed, retry_after = _counter.check_and_increment(key, _HEALTH_LIMIT, _HEALTH_WINDOW)
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Try again later."},
                    headers={"Retry-After": str(retry_after)},
                )

        elif exec_match and request.method == "POST":
            key = f"exec:{user_id}"
            allowed, retry_after = _counter.check_and_increment(key, _EXEC_LIMIT, _EXEC_WINDOW)
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Try again later."},
                    headers={"Retry-After": str(retry_after)},
                )

        return await call_next(request)
