"""Tests para Entity VerificationToken."""
from datetime import datetime, timedelta, timezone
import pytest

from app.v1.auth.domain.entities import VerificationToken
from app.v1.auth.domain.exceptions import InvalidVerificationTokenError


class TestVerificationToken:
    """Tests de la Entity VerificationToken."""

    def test_verification_token_creation(self):
        """Test 1: VerificationToken se crea exitosamente con datos válidos."""
        token_id = "vtoken-123"
        user_id = "user-456"
        token_value = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        token_type = "email_verification"
        expires_at = datetime.now() + timedelta(hours=24)

        verification_token = VerificationToken(
            id=token_id,
            user_id=user_id,
            token=token_value,
            token_type=token_type,
            expires_at=expires_at,
            created_at=datetime.now()
        )

        assert verification_token.id == token_id
        assert verification_token.user_id == user_id
        assert verification_token.token == token_value
        assert verification_token.token_type == token_type
        assert verification_token.expires_at == expires_at

    def test_verification_token_invalid_type(self):
        """Test 2: VerificationToken con token_type inválido lanza InvalidVerificationTokenError."""
        with pytest.raises(InvalidVerificationTokenError):
            VerificationToken(
                id="vtoken-123",
                user_id="user-456",
                token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                token_type="invalid_type",  # Solo acepta email_verification o password_reset
                expires_at=datetime.now() + timedelta(hours=24),
                created_at=datetime.now()
            )

    def test_verification_token_empty_token(self):
        """Test 3: VerificationToken con token vacío lanza InvalidVerificationTokenError."""
        with pytest.raises(InvalidVerificationTokenError):
            VerificationToken(
                id="vtoken-123",
                user_id="user-456",
                token="",  # token vacío
                token_type="email_verification",
                expires_at=datetime.now() + timedelta(hours=24),
                created_at=datetime.now()
            )

    def test_verification_token_empty_user_id(self):
        """Test 4: VerificationToken con user_id vacío lanza InvalidVerificationTokenError."""
        with pytest.raises(InvalidVerificationTokenError):
            VerificationToken(
                id="vtoken-123",
                user_id="",  # user_id vacío
                token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                token_type="email_verification",
                expires_at=datetime.now() + timedelta(hours=24),
                created_at=datetime.now()
            )

    def test_verification_token_mutable(self):
        """Test 5: VerificationToken es mutable (sin frozen=True)."""
        verification_token = VerificationToken(
            id="vtoken-123",
            user_id="user-456",
            token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            token_type="email_verification",
            expires_at=datetime.now() + timedelta(hours=24),
            created_at=datetime.now()
        )

        # Entities pueden mutar
        new_user_id = "user-999"
        verification_token.user_id = new_user_id
        assert verification_token.user_id == new_user_id

    def test_verification_token_equality(self):
        """Test 6: Dos VerificationTokens con mismo ID son iguales."""
        now = datetime.now()
        expires = now + timedelta(hours=24)

        vtoken1 = VerificationToken(
            id="vtoken-123",
            user_id="user-456",
            token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            token_type="email_verification",
            expires_at=expires,
            created_at=now
        )
        vtoken2 = VerificationToken(
            id="vtoken-123",
            user_id="user-456",
            token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            token_type="email_verification",
            expires_at=expires,
            created_at=now
        )

        assert vtoken1 == vtoken2

    def test_is_valid_for_email_verification_success(self):
        """Test 7: is_valid_for_email_verification retorna True para token válido."""
        vtoken = VerificationToken(
            id="vtoken-123",
            user_id="user-456",
            token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            token_type="email_verification",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            created_at=datetime.now(timezone.utc)
        )

        # El token es válido
        result = vtoken.is_valid_for_email_verification()
        assert result is True

    def test_is_valid_for_email_verification_wrong_type(self):
        """Test 8: is_valid_for_email_verification lanza error si token_type es incorrecto."""
        vtoken = VerificationToken(
            id="vtoken-123",
            user_id="user-456",
            token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            token_type="password_reset",  # Tipo incorrecto
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            created_at=datetime.now(timezone.utc)
        )

        # Debe lanzar excepción porque no es email_verification
        with pytest.raises(InvalidVerificationTokenError):
            vtoken.is_valid_for_email_verification()

    def test_is_valid_for_email_verification_expired(self):
        """Test 9: is_valid_for_email_verification lanza error si el token ha expirado."""
        vtoken = VerificationToken(
            id="vtoken-123",
            user_id="user-456",
            token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            token_type="email_verification",
            expires_at=datetime.now(timezone.utc) -
            timedelta(hours=1),  # Expiró hace 1 hora
            created_at=datetime.now(timezone.utc) - timedelta(hours=25)
        )

        # Debe lanzar excepción porque el token expiró
        with pytest.raises(InvalidVerificationTokenError):
            vtoken.is_valid_for_email_verification()
