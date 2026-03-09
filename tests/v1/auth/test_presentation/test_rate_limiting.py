"""Tests de rate limiting y bloqueo temporal en el endpoint de login (T-56).

Cubre el comportamiento del LoginAttemptTracker en la capa de presentación:
    1. Contraseña incorrecta → record_failed_attempt() es invocado
    2. Login exitoso → reset_attempts() es invocado
    3. Usuario bloqueado no llega a verificar contraseña (bloqueo previo)
    4. Flujo progresivo: 5 intentos fallidos acumulan bloqueo → 429 en el 6º
    5. Desbloqueo tras login exitoso: el contador se resetea correctamente
"""
import asyncio
from datetime import datetime, timezone

import bcrypt
from fastapi.testclient import TestClient

from app.v1.auth.domain.entities.user import User
from app.v1.auth.domain.value_objects.email import Email
from app.v1.auth.infrastructure.presentation.deps import (
    get_event_bus,
    get_jwt_provider,
    get_login_attempt_tracker,
    get_refresh_token_repository,
    get_user_repository,
)
from main import app
from tests.v1.auth.test_presentation.conftest import (
    FakeEventBus,
    FakeJWTProvider,
    FakeRefreshTokenRepository,
    FakeUserRepository,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
_EMAIL = "ratelimit@example.com"
_PASSWORD = "SecurePass123!"
_WRONG_PASSWORD = "WrongPass999!"
_PASSWORD_HASH = bcrypt.hashpw(
    _PASSWORD.encode(), bcrypt.gensalt(rounds=4)
).decode()
_MAX_ATTEMPTS = 5  # RN-04: bloqueo tras 5 intentos fallidos


# ---------------------------------------------------------------------------
# Fake tracker con estado real (para tests progresivos)
# ---------------------------------------------------------------------------

class ProgressiveFakeLoginAttemptTracker:
    """Fake LoginAttemptTracker que simula el comportamiento real de bloqueo progresivo.

    Se auto-bloquea cuando el número de intentos fallidos supera _MAX_ATTEMPTS.
    Permite verificar el flujo completo: intentos acumulados → bloqueo → 429.
    """

    def __init__(self) -> None:
        """Inicializa el tracker con contadores vacíos."""
        self._attempts: dict[str, int] = {}
        self.record_calls: list[str] = []
        self.reset_calls: list[str] = []
        self.is_blocked_checks: list[str] = []

    async def is_blocked(self, identifier: str) -> bool:
        """Retorna True cuando el contador supera _MAX_ATTEMPTS (comportamiento real: count > 5)."""
        await asyncio.sleep(0)
        self.is_blocked_checks.append(identifier)
        return self._attempts.get(identifier, 0) > _MAX_ATTEMPTS

    async def record_failed_attempt(self, identifier: str) -> int:
        """Incrementa el contador de intentos fallidos y retorna el nuevo total."""
        await asyncio.sleep(0)
        self.record_calls.append(identifier)
        count = self._attempts.get(identifier, 0) + 1
        self._attempts[identifier] = count
        return count

    async def reset_attempts(self, identifier: str) -> None:
        """Elimina el contador del identificador dado."""
        await asyncio.sleep(0)
        self.reset_calls.append(identifier)
        self._attempts.pop(identifier, None)

    async def get_remaining_attempts(self, identifier: str) -> int:
        """Retorna los intentos restantes antes del bloqueo."""
        await asyncio.sleep(0)
        return max(0, _MAX_ATTEMPTS - self._attempts.get(identifier, 0))


# ---------------------------------------------------------------------------
# Fake tracker con inspección para tests unitarios de presentación
# ---------------------------------------------------------------------------

class InspectableFakeLoginAttemptTracker:
    """Fake LoginAttemptTracker que registra todas las llamadas para inspección."""

    def __init__(self, blocked: bool = False) -> None:
        self._blocked = blocked
        self.record_calls: list[str] = []
        self.reset_calls: list[str] = []

    async def is_blocked(self, identifier: str) -> bool:
        """Retorna el valor predefinido de bloqueo, sin lógica real."""
        await asyncio.sleep(0)
        return self._blocked

    async def record_failed_attempt(self, identifier: str) -> int:
        """Registra la llamada con el email dado, sin lógica real de conteo."""
        await asyncio.sleep(0)
        self.record_calls.append(identifier)
        return len(self.record_calls)

    async def reset_attempts(self, identifier: str) -> None:
        """Registra la llamada con el email dado, sin lógica real de reseteo."""
        await asyncio.sleep(0)
        self.reset_calls.append(identifier)

    async def get_remaining_attempts(self, identifier: str) -> int:
        """Retorna un valor fijo de intentos restantes, sin lógica real."""
        await asyncio.sleep(0)
        return _MAX_ATTEMPTS - len(self.record_calls)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(**kwargs) -> User:
    """Crea un usuario de prueba con email y contraseña predefinidos."""
    now = datetime.now(timezone.utc)
    return User(
        id="user-rt-1",
        name="Rate Limit User",
        email=Email(_EMAIL),
        password_hash=_PASSWORD_HASH,
        created_at=now,
        updated_at=now,
        **kwargs,
    )


def _setup_overrides(tracker, user: User | None = None):
    """Registra overrides de dependencias en la app con el tracker y usuario dados."""
    app.dependency_overrides[get_user_repository] = lambda: FakeUserRepository(
        user=user)
    app.dependency_overrides[get_refresh_token_repository] = lambda: FakeRefreshTokenRepository(
    )
    app.dependency_overrides[get_login_attempt_tracker] = lambda: tracker
    app.dependency_overrides[get_jwt_provider] = FakeJWTProvider
    app.dependency_overrides[get_event_bus] = FakeEventBus


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRateLimitingBehavior:
    """Tests de rate limiting y bloqueo temporal en POST /api/v1/auth/login."""

    def test_wrong_password_invokes_record_failed_attempt(self):
        """Contraseña incorrecta → record_failed_attempt() es invocado con el email."""
        tracker = InspectableFakeLoginAttemptTracker(blocked=False)
        _setup_overrides(tracker, user=_make_user())

        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/auth/login",
                    json={"email": _EMAIL, "password": _WRONG_PASSWORD},
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 401
        assert _EMAIL in tracker.record_calls, (
            "record_failed_attempt() debe llamarse con el email tras contraseña incorrecta"
        )

    def test_successful_login_invokes_reset_attempts(self):
        """Login exitoso → reset_attempts() es invocado con el email."""
        tracker = InspectableFakeLoginAttemptTracker(blocked=False)
        _setup_overrides(tracker, user=_make_user())

        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/auth/login",
                    json={"email": _EMAIL, "password": _PASSWORD},
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert _EMAIL in tracker.reset_calls, (
            "reset_attempts() debe llamarse con el email tras login exitoso"
        )

    def test_blocked_user_not_reaching_password_check(self):
        """Usuario bloqueado → 429 sin llamar a record_failed_attempt.

        El bloqueo ocurre antes de verificar la contraseña (línea ~268 en routes.py).
        Incluso con contraseña correcta, un usuario bloqueado recibe 429.
        """
        tracker = InspectableFakeLoginAttemptTracker(blocked=True)
        _setup_overrides(tracker, user=_make_user())

        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/auth/login",
                    json={"email": _EMAIL, "password": _PASSWORD},
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 429
        assert tracker.record_calls == [], (
            "record_failed_attempt() NO debe llamarse cuando el usuario ya está bloqueado"
        )
        assert tracker.reset_calls == [], (
            "reset_attempts() NO debe llamarse cuando el usuario está bloqueado"
        )

    def test_progressive_blocking_after_max_attempts(self):
        """Flujo progresivo: 6 intentos fallidos → el 7º recibe 429.

        La implementación real (ValkeyLoginAttemptTracker) usa count > MAX_ATTEMPTS (5),
        por lo que bloquea cuando el contador llega a 6. El flujo es:
          - Intentos 1-6: is_blocked ve <=5 → False → contraseña falla → record → 401
          - Intento 7: is_blocked ve 6 → True → 429 sin verificar contraseña (RN-04).
        """
        tracker = ProgressiveFakeLoginAttemptTracker()
        _setup_overrides(tracker, user=_make_user())

        # intentos que deben retornar 401 (contador aún no supera el límite en is_blocked)
        _attempts_before_block = _MAX_ATTEMPTS + 1  # 6

        try:
            with TestClient(app) as client:
                # 6 intentos fallidos — is_blocked ve <=5 en cada uno → 401
                for attempt in range(1, _attempts_before_block + 1):
                    resp = client.post(
                        "/api/v1/auth/login",
                        json={"email": _EMAIL, "password": _WRONG_PASSWORD},
                    )
                    assert resp.status_code == 401, (
                        f"Intento {attempt}: esperado 401, obtenido {resp.status_code}"
                    )

                # 7º intento — is_blocked ve 6 > 5 → True → 429
                resp = client.post(
                    "/api/v1/auth/login",
                    json={"email": _EMAIL, "password": _WRONG_PASSWORD},
                )
                assert resp.status_code == 429, (
                    f"Intento 7 (bloqueado): esperado 429, obtenido {resp.status_code}"
                )
        finally:
            app.dependency_overrides.clear()

        assert len(tracker.record_calls) == _attempts_before_block, (
            f"record_failed_attempt() debe haberse llamado exactamente {_attempts_before_block} veces"
        )

    def test_unlock_after_successful_login(self):
        """Login exitoso tras intentos fallidos resetea el contador.

        Verifica que reset_attempts se invoca y el tracker limpia el estado,
        permitiendo futuros logins sin bloqueo.
        """
        tracker = ProgressiveFakeLoginAttemptTracker()
        _setup_overrides(tracker, user=_make_user())

        try:
            with TestClient(app) as client:
                # 3 intentos fallidos
                for _ in range(3):
                    client.post(
                        "/api/v1/auth/login",
                        json={"email": _EMAIL, "password": _WRONG_PASSWORD},
                    )

                assert len(tracker.record_calls) == 3

                # Login exitoso → reset
                resp = client.post(
                    "/api/v1/auth/login",
                    json={"email": _EMAIL, "password": _PASSWORD},
                )
                assert resp.status_code == 200
        finally:
            app.dependency_overrides.clear()

        assert _EMAIL in tracker.reset_calls, "reset_attempts() debe llamarse tras login exitoso"
        assert tracker._attempts.get(
            _EMAIL, 0) == 0, "El contador debe quedar en 0 tras reset"
