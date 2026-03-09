"""Fakes compartidos para tests de presentación (test_presentation/).

Las clases fake se definen aquí para evitar duplicación entre archivos de test.
Los fixtures con overrides concretos viven en cada archivo de test, ya que
dependen del estado específico de cada escenario.
"""
import asyncio

from app.v1.auth.domain.entities.refresh_token import RefreshToken
from app.v1.auth.domain.entities.user import User
from app.v1.auth.domain.entities.verification_token import VerificationToken


# ---------------------------------------------------------------------------
# FakeUserRepository
# ---------------------------------------------------------------------------

class FakeUserRepository:
    """Fake en memoria para UserRepository."""

    def __init__(self, user: User | None = None) -> None:
        """Inicializa el repositorio con un usuario opcional."""
        self._user = user
        self.updated: list[User] = []

    async def find_by_email(self, email: str) -> User | None:
        """Busca usuario por email."""
        await asyncio.sleep(0)
        if self._user and self._user.email.value == email:
            return self._user
        return None

    async def find_by_id(self, user_id: str) -> User | None:
        """Busca usuario por ID."""
        await asyncio.sleep(0)
        if self._user and self._user.id == user_id:
            return self._user
        return None

    async def save(self, user: User) -> User:
        """Guarda un usuario."""
        await asyncio.sleep(0)
        return user

    async def update(self, user: User) -> User:
        """Actualiza un usuario."""
        await asyncio.sleep(0)
        self.updated.append(user)
        return user

    async def delete(self, _user_id: str) -> None:
        """Elimina un usuario por ID."""
        await asyncio.sleep(0)


# ---------------------------------------------------------------------------
# FakeVerificationTokenRepository
# ---------------------------------------------------------------------------

class FakeVerificationTokenRepository:
    """Fake en memoria para VerificationTokenRepository."""

    def __init__(self, token: VerificationToken | None = None) -> None:
        """Inicializa el repositorio con un token opcional."""
        self._token = token
        self.saved: list[VerificationToken] = []
        self.deleted: list[str] = []

    async def save(self, token: VerificationToken) -> VerificationToken:
        """Guarda un token de verificación."""
        await asyncio.sleep(0)
        self.saved.append(token)
        return token

    async def find_by_token(self, token: str) -> VerificationToken | None:
        """Busca un token de verificación por su valor."""
        await asyncio.sleep(0)
        if self._token and self._token.token == token:
            return self._token
        return None

    async def delete(self, token_id: str) -> None:
        """Elimina un token de verificación por ID."""
        await asyncio.sleep(0)
        self.deleted.append(token_id)

    async def delete_by_user_id(self, _user_id: str) -> None:
        """Elimina tokens por user_id."""
        await asyncio.sleep(0)

    async def find_by_user_id(self, _user_id: str) -> list:
        """Busca tokens por user_id."""
        await asyncio.sleep(0)
        return []


# ---------------------------------------------------------------------------
# FakeRefreshTokenRepository
# ---------------------------------------------------------------------------

class FakeRefreshTokenRepository:
    """Fake en memoria para RefreshTokenRepository."""

    def __init__(self, token: RefreshToken | None = None) -> None:
        """Inicializa el repositorio con un refresh token opcional."""
        self._token = token
        self.saved: list[RefreshToken] = []
        self.deleted: list[str] = []

    async def save(self, token: RefreshToken) -> RefreshToken:
        """Guarda un refresh token."""
        await asyncio.sleep(0)
        self.saved.append(token)
        return token

    async def find_by_token(self, token: str) -> RefreshToken | None:
        """Busca un refresh token por su valor."""
        await asyncio.sleep(0)
        if self._token and self._token.token == token:
            return self._token
        return None

    async def delete(self, token_id: str) -> None:
        """Elimina un refresh token por ID."""
        await asyncio.sleep(0)
        self.deleted.append(token_id)

    async def delete_by_user_id(self, _user_id: str) -> None:
        """Elimina refresh tokens por user_id."""
        await asyncio.sleep(0)

    async def count_by_user_id(self, _user_id: str) -> int:
        """Cuenta refresh tokens por user_id."""
        await asyncio.sleep(0)
        return 0

    async def find_by_user_id(self, _user_id: str) -> list:
        """Busca refresh tokens por user_id."""
        await asyncio.sleep(0)
        return []


# ---------------------------------------------------------------------------
# FakeEmailService
# ---------------------------------------------------------------------------

class FakeEmailService:
    """Fake en memoria para EmailService."""

    def __init__(self) -> None:
        """Inicializa el servicio con lista de emails enviados vacía."""
        self.sent: list[dict] = []

    async def send_verification_email(self, email: str, token: str, user_name: str) -> None:
        """Registra envío de email de verificación."""
        await asyncio.sleep(0)
        self.sent.append({"type": "verification", "email": email,
                         "token": token, "user_name": user_name})

    async def send_password_reset_email(self, email: str, token: str, user_name: str) -> None:
        """Registra envío de email de reset de contraseña."""
        await asyncio.sleep(0)
        self.sent.append({"type": "password_reset", "email": email,
                         "token": token, "user_name": user_name})

    async def send_password_changed_notification(self, email: str, user_name: str) -> None:
        """Registra envío de notificación de contraseña cambiada."""
        await asyncio.sleep(0)
        self.sent.append({"type": "password_changed",
                         "email": email, "user_name": user_name})

    async def send_2fa_enabled_notification(self, email: str, user_name: str) -> None:
        """Registra envío de notificación de 2FA habilitado."""
        await asyncio.sleep(0)
        self.sent.append(
            {"type": "2fa_enabled", "email": email, "user_name": user_name})


# ---------------------------------------------------------------------------
# FakeLoginAttemptTracker
# ---------------------------------------------------------------------------

class FakeLoginAttemptTracker:
    """Fake en memoria para LoginAttemptTracker."""

    def __init__(self, blocked: bool = False) -> None:
        """Inicializa el tracker, opcionalmente bloqueado."""
        self._blocked = blocked
        self.failed_attempts: dict[str, int] = {}
        self.resets: list[str] = []

    async def is_blocked(self, identifier: str) -> bool:  # noqa: ARG002
        """Retorna el estado de bloqueo configurado."""
        await asyncio.sleep(0)
        return self._blocked

    async def record_failed_attempt(self, identifier: str) -> int:
        """Registra un intento fallido para el identificador."""
        await asyncio.sleep(0)
        count = self.failed_attempts.get(identifier, 0) + 1
        self.failed_attempts[identifier] = count
        return count

    async def reset_attempts(self, identifier: str) -> None:
        """Resetea los intentos fallidos del identificador."""
        await asyncio.sleep(0)
        self.resets.append(identifier)
        self.failed_attempts.pop(identifier, None)

    async def get_remaining_attempts(self, identifier: str) -> int:
        """Retorna los intentos restantes para el identificador."""
        await asyncio.sleep(0)
        return max(0, 5 - self.failed_attempts.get(identifier, 0))


# ---------------------------------------------------------------------------
# FakeJWTProvider
# ---------------------------------------------------------------------------

class FakeJWTProvider:
    """Fake en memoria para JWTProvider."""

    def create_access_token(self, user_id: str, **_kwargs) -> object:
        """Fake — retorna token con valor predecible."""
        class _Token:
            token = f"fake-access-token-{user_id}"
        return _Token()

    def create_refresh_token(self, user_id: str, **_kwargs) -> object:
        """Fake — retorna refresh token con valor predecible."""
        class _Token:
            token = f"fake-refresh-token-{user_id}"
        return _Token()

    def decode_token(self, token: str) -> dict:
        """Fake — retorna sub vacío por defecto (sobreescribir en tests específicos)."""
        return {"sub": ""}

    def verify_token(self, token: str) -> bool:
        """Fake — siempre retorna True."""
        return True


# ---------------------------------------------------------------------------
# FakePasswordHistoryRepository
# ---------------------------------------------------------------------------

class FakePasswordHistoryRepository:
    """Fake en memoria para PasswordHistoryRepository."""

    def __init__(self, history: list | None = None) -> None:
        """Inicializa el repositorio con historial opcional."""
        self._history = history or []
        self.saved: list[tuple[str, str]] = []

    async def save(self, user_id: str, password_hash: str) -> None:
        """Guarda un hash de contraseña en el historial."""
        await asyncio.sleep(0)
        self.saved.append((user_id, password_hash))

    async def find_last_n_by_user(self, _user_id: str, _n: int) -> list:
        """Retorna el historial configurado."""
        await asyncio.sleep(0)
        return self._history


# ---------------------------------------------------------------------------
# FakeEventBus
# ---------------------------------------------------------------------------

class FakeEventBus:
    """Fake en memoria para EventBus."""

    async def publish(self, _event: object) -> None:
        """Descarta el evento publicado."""
        await asyncio.sleep(0)

    def subscribe(self, _event_type: type, _handler: object) -> None:
        """No hace nada — fake sin suscriptores."""
        pass


# ---------------------------------------------------------------------------
# FakeTOTPProvider
# ---------------------------------------------------------------------------

class FakeTOTPProvider:
    """Fake en memoria para TOTPProvider."""

    FAKE_SECRET = "FAKESECRETBASE32"
    FAKE_QR = "data:image/png;base64,FAKEQR=="

    def generate_secret(self) -> str:
        """Retorna un secret TOTP fake predecible."""
        return self.FAKE_SECRET

    def generate_qr_code(self, secret: str, user_email: str, issuer: str = "ikctl") -> str:  # noqa: ARG002
        """Retorna un QR code URI fake."""
        return self.FAKE_QR

    def verify_code(self, secret: str, code: str) -> bool:  # noqa: ARG002
        """Retorna True solo si el código es '123456'."""
        return code == "123456"

    def get_provisioning_uri(self, secret: str, user_email: str, issuer: str = "ikctl") -> str:
        """Retorna una URI de provisionamiento TOTP fake."""
        return f"otpauth://totp/{issuer}:{user_email}?secret={secret}&issuer={issuer}"
