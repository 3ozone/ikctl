"""Benchmark tests para endpoints de auth (T-57.1).

Valida los SLO de latencia con bcrypt real (rounds=4) como baseline de regresiones:
    - POST /api/v1/auth/register  → p99 < 500ms (incluye bcrypt hash rounds=4)
    - POST /api/v1/auth/login     → p99 < 500ms (incluye bcrypt verify rounds=4)
    - POST /api/v1/auth/refresh   → p99 < 50ms  (sin bcrypt, solo token lookup)

Propósito — detección de regresiones en CI:
    Estos tests no validan la latencia de producción (que incluye bcrypt rounds=12
    ~300ms adicionales, DB real ~10-20ms y red). Su objetivo es detectar regresiones
    en el código: si hoy /login tarda 200ms p99 y mañana tarda 2000ms, hay una
    regresión en routing, validación Pydantic o use cases.

Metodología:
    - N=50 iteraciones por endpoint (suficiente para calcular p99 estable)
    - bcrypt rounds=4 incluido (no mockeado) para baseline honesto con hashing real
    - Los tiempos se miden con time.perf_counter() (alta resolución)
    - p99 = percentil 99 de los tiempos de respuesta
    - Fakes en memoria para DB y servicios externos (sin latencia de red)

SLOs de producción (monitoreo APM, fuera del scope de estos tests):
    El monitoreo real de producción se hace con Prometheus/Grafana/Datadog,
    donde se definen alertas sobre métricas reales (bcrypt rounds=12, DB, red).
"""
import statistics
import time
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import pytest
from fastapi.testclient import TestClient

from app.v1.auth.domain.entities.refresh_token import RefreshToken
from app.v1.auth.domain.entities.user import User
from app.v1.auth.domain.value_objects.email import Email
from app.v1.auth.infrastructure.presentation.deps import (
    get_email_service,
    get_event_bus,
    get_jwt_provider,
    get_login_attempt_tracker,
    get_refresh_token_repository,
    get_user_repository,
    get_verification_token_repository,
)
from main import app
from tests.v1.auth.test_presentation.conftest import (
    FakeEmailService,
    FakeEventBus,
    FakeJWTProvider,
    FakeLoginAttemptTracker,
    FakeRefreshTokenRepository,
    FakeUserRepository,
    FakeVerificationTokenRepository,
)

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
_ITERATIONS = 50           # iteraciones por benchmark
_EMAIL = "bench@example.com"
_PASSWORD = "BenchPass123!"
# rounds=4 para tests — en producción se usa rounds=12 (~300ms adicionales intencionales)
_PASSWORD_HASH = bcrypt.hashpw(
    _PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode()

# SLOs en segundos — baseline de regresión con bcrypt real (rounds=4) y fakes en memoria
_SLO_REGISTER_P99 = 0.500   # 500ms (incluye bcrypt hash)
_SLO_LOGIN_P99 = 0.500      # 500ms (incluye bcrypt verify)
_SLO_REFRESH_P99 = 0.050    # 50ms  (sin bcrypt)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user() -> User:
    """Crea un usuario de prueba con email y contraseña predefinidos."""
    now = datetime.now(timezone.utc)
    return User(
        id="bench-user-1",
        name="Bench User",
        email=Email(_EMAIL),
        password_hash=_PASSWORD_HASH,
        created_at=now,
        updated_at=now,
    )


def _make_refresh_token() -> RefreshToken:
    """Crea un refresh token de prueba válido (no expirado)."""
    now = datetime.now(timezone.utc)
    return RefreshToken(
        id="bench-rt-1",
        user_id="bench-user-1",
        token="fake-refresh-token-bench-user-1",
        expires_at=now + timedelta(days=7),
        created_at=now,
    )


def _percentile(data: list[float], p: int) -> float:
    """Calcula el percentil p de una lista de tiempos (en segundos)."""
    sorted_data = sorted(data)
    index = int(len(sorted_data) * p / 100)
    index = min(index, len(sorted_data) - 1)
    return sorted_data[index]


def _measure(client: TestClient, method: str, url: str, **kwargs) -> list[float]:
    """Ejecuta N iteraciones de una request y retorna los tiempos en segundos."""
    times = []
    for _ in range(_ITERATIONS):
        start = time.perf_counter()
        getattr(client, method)(url, **kwargs)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    return times


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(name="bench_client_register")
def fixture_bench_client_register():
    """Cliente con fakes para benchmark de /register."""
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
        user=None)
    app.dependency_overrides[get_verification_token_repository] = lambda: FakeVerificationTokenRepository()
    app.dependency_overrides[get_email_service] = lambda: FakeEmailService()
    app.dependency_overrides[get_event_bus] = FakeEventBus

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(name="bench_client_login")
def fixture_bench_client_login():
    """Cliente con fakes para benchmark de /login."""
    user = _make_user()
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
        user=user)
    app.dependency_overrides[get_refresh_token_repository] = lambda: FakeRefreshTokenRepository(
    )
    app.dependency_overrides[get_login_attempt_tracker] = lambda: FakeLoginAttemptTracker(
        blocked=False)
    app.dependency_overrides[get_jwt_provider] = FakeJWTProvider
    app.dependency_overrides[get_event_bus] = FakeEventBus

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(name="bench_client_refresh")
def fixture_bench_client_refresh():
    """Cliente con fakes para benchmark de /refresh."""
    rt = _make_refresh_token()
    user = _make_user()
    app.dependency_overrides[get_refresh_token_repository] = lambda: FakeRefreshTokenRepository(
        token=rt)
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
        user=user)
    app.dependency_overrides[get_jwt_provider] = FakeJWTProvider
    app.dependency_overrides[get_event_bus] = FakeEventBus

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Benchmark Tests
# ---------------------------------------------------------------------------

class TestBenchmarks:
    """Benchmark tests de latencia para endpoints de auth (SLO T-57.1)."""

    def test_register_p99_under_100ms(self, bench_client_register: TestClient):
        """POST /register — p99 debe ser < 500ms con bcrypt real (rounds=4) y fakes en memoria.

        Detecta regresiones en routing, validación Pydantic y use case RegisterUser.
        bcrypt rounds=4 incluido: no se mockea para que el baseline sea honesto.
        En producción se usa rounds=12 (~300ms adicionales) más latencia de DB real.
        """
        times = []
        for i in range(_ITERATIONS):
            # Email único por iteración para evitar conflictos de email duplicado
            start = time.perf_counter()
            bench_client_register.post(
                "/api/v1/auth/register",
                json={
                    "name": f"Bench User {i}",
                    "email": f"bench{i}_{uuid.uuid4().hex[:6]}@example.com",
                    "password": _PASSWORD,
                },
            )
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        p99 = _percentile(times, 99)
        p50 = statistics.median(times)

        print(
            f"\n  /register — p50={p50*1000:.1f}ms  p99={p99*1000:.1f}ms  SLO={_SLO_REGISTER_P99*1000:.0f}ms")

        assert p99 < _SLO_REGISTER_P99, (
            f"SLO VIOLADO: /register p99={p99*1000:.1f}ms >= {_SLO_REGISTER_P99*1000:.0f}ms"
        )

    def test_login_p99_under_100ms(self, bench_client_login: TestClient):
        """POST /login — p99 debe ser < 500ms con bcrypt real (rounds=4) y fakes en memoria.

        Detecta regresiones en routing, validación Pydantic y use case AuthenticateUser.
        Incluye verificación bcrypt (rounds=4) y generación de tokens fake.
        """
        times = _measure(
            bench_client_login,
            "post",
            "/api/v1/auth/login",
            json={"email": _EMAIL, "password": _PASSWORD},
        )

        p99 = _percentile(times, 99)
        p50 = statistics.median(times)

        print(
            f"\n  /login — p50={p50*1000:.1f}ms  p99={p99*1000:.1f}ms  SLO={_SLO_LOGIN_P99*1000:.0f}ms")

        assert p99 < _SLO_LOGIN_P99, (
            f"SLO VIOLADO: /login p99={p99*1000:.1f}ms >= {_SLO_LOGIN_P99*1000:.0f}ms"
        )

    def test_refresh_p99_under_50ms(self, bench_client_refresh: TestClient):
        """POST /refresh — p99 debe ser < 50ms con fakes en memoria.

        No incluye bcrypt. Detecta regresiones en routing y use case RefreshAccessToken.
        Es el endpoint más estricto: sin hashing, la latencia debe ser mínima.
        """
        times = _measure(
            bench_client_refresh,
            "post",
            "/api/v1/auth/refresh",
            json={"refresh_token": "fake-refresh-token-bench-user-1"},
        )

        p99 = _percentile(times, 99)
        p50 = statistics.median(times)

        print(
            f"\n  /refresh — p50={p50*1000:.1f}ms  p99={p99*1000:.1f}ms  SLO={_SLO_REFRESH_P99*1000:.0f}ms")

        assert p99 < _SLO_REFRESH_P99, (
            f"SLO VIOLADO: /refresh p99={p99*1000:.1f}ms >= {_SLO_REFRESH_P99*1000:.0f}ms"
        )
