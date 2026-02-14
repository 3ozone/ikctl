"""Entry point y configuración de la aplicación ikctl."""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app() -> FastAPI:
    """Factory para crear la aplicación FastAPI."""
    app = FastAPI(
        title="ikctl API",
        description="API REST para gestión de instalaciones remotas de aplicaciones",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS Configuration
    origins = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:8080"
    ).split(",")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health Check Endpoints
    @app.get("/")
    def read_root():
        """Health check endpoint."""
        return {
            "message": "ikctl API is running",
            "version": "1.0.0",
            "docs": "/docs",
        }

    @app.get("/health")
    def health_check():
        """General health check endpoint."""
        return {
            "status": "ok",
            "service": "ikctl-api",
            "version": "1.0.0",
        }

    @app.get("/healthz")
    def healthz():
        """Kubernetes liveness probe - verifica que el pod esté vivo.

        Si este endpoint falla, Kubernetes reiniciará el pod.
        Debe ser muy simple y no depender de recursos externos.
        """
        return {
            "status": "alive",
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }

    @app.get("/readyz")
    def readyz():
        """Kubernetes readiness probe - verifica que el pod esté listo para tráfico.

        Si este endpoint falla, Kubernetes removerá el pod del load balancer
        pero no lo reiniciará.
        """
        # TODO: Agregar chequeos aquí
        # - Conexión a base de datos
        # - Disponibilidad de servicios externos críticos
        return {
            "status": "ready",
            "checks": {
                "database": "ok",  # TODO: chequear actual db connection
                "api": "ok",
            },
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }

    # TODO: Aquí irán los routers de auth, users, servers, operations
    # from app.v1.auth.presentation.routes import router as auth_router
    # app.include_router(auth_router, prefix="/api/v1", tags=["auth"])

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
