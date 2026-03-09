"""AuthenticationMiddleware — verifica Bearer token en endpoints protegidos.

Endpoints públicos (no requieren token):
- /docs, /redoc, /openapi.json  (Swagger UI)
- /, /healthz, /readyz           (health checks)
- POST /api/v1/auth/register
- POST /api/v1/auth/login
- POST /api/v1/auth/refresh
- POST /api/v1/auth/password-reset/request
- POST /api/v1/auth/password-reset/confirm
- GET  /api/v1/auth/github/callback

Para rutas protegidas, inyecta `request.state.user_id` y `request.state.token_payload`
para que los endpoints puedan obtenerlos sin re-verificar el token.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.v1.auth.infrastructure.adapters.jwt_provider import PyJWTProvider

# Rutas que no requieren autenticación
_PUBLIC_PATHS: frozenset[str] = frozenset(
    [
        "/",
        "/healthz",
        "/readyz",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/auth/register",
        "/api/v1/auth/verify-email",
        "/api/v1/auth/resend-verification",
        "/api/v1/auth/login",
        "/api/v1/auth/login/2fa",
        "/api/v1/auth/login/github",
        "/api/v1/auth/login/github/callback",
        "/api/v1/auth/refresh",
        "/api/v1/auth/logout",
        "/api/v1/auth/password/forgot",
        "/api/v1/auth/password/reset",
    ]
)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware Starlette que verifica el Bearer token en rutas protegidas.

    Inyecta en `request.state`:
        - user_id (str): ID del usuario autenticado.
        - token_payload (dict): Payload completo del JWT decodificado.

    Retorna HTTP 401 si el token falta o es inválido en rutas protegidas.
    """

    def __init__(self, app, jwt_provider: PyJWTProvider) -> None:
        """Inicializa el middleware con el proveedor JWT.

        Args:
            app:          Aplicación ASGI.
            jwt_provider: Singleton PyJWTProvider inyectado desde el Composition Root.
        """
        super().__init__(app)
        self._jwt_provider = jwt_provider

    async def dispatch(self, request: Request, call_next):
        """Intercepta cada request y verifica autenticación si la ruta es protegida.

        Args:
            request:   Request entrante.
            call_next: Siguiente middleware o handler.

        Returns:
            Response con 401 si la autenticación falla, o la response normal.
        """
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        # Extraer Bearer token del header Authorization
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Token de autenticación requerido."},
            )

        token = auth_header.removeprefix("Bearer ").strip()
        if not token:
            return JSONResponse(
                status_code=401,
                content={"detail": "Token de autenticación requerido."},
            )

        try:
            payload = self._jwt_provider.decode_token(token)
            request.state.user_id = payload.get("sub")
            request.state.token_payload = payload
        except Exception:
            return JSONResponse(
                status_code=401,
                content={"detail": "Token inválido o expirado."},
            )

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware que añade headers de seguridad HTTP a todas las respuestas.

    Headers incluidos:
        X-Content-Type-Options: nosniff
        X-Frame-Options: DENY
        Strict-Transport-Security: max-age=63072000; includeSubDomains
    """

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        """Procesa la request y añade headers de seguridad a la response.

        Args:
            request: Request entrante de Starlette.
            call_next: Callable para invocar al siguiente middleware o endpoint.

        Returns:
            Response con los headers de seguridad añadidos.
        """
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains"
        )
        return response
