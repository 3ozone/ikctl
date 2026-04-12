"""Tests para Entity User."""
from datetime import datetime
import pytest

from app.v1.auth.domain.entities import User
from app.v1.auth.domain.value_objects import Email
from app.v1.auth.domain.exceptions import InvalidUserError


class TestUser:
    """Tests de la Entity User."""

    def test_user_creation(self):
        """Test 1: User se crea exitosamente con datos válidos."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        name = "John Doe"
        email = Email("john@example.com")
        password_hash = "hashed_password_here"
        now = datetime.now()

        user = User(
            id=user_id,
            name=name,
            email=email,
            password_hash=password_hash,
            created_at=now,
            updated_at=now
        )

        assert user.id == user_id
        assert user.name == name
        assert user.email == email
        assert user.password_hash == password_hash
        assert user.created_at == now
        assert user.updated_at == now
        assert user.totp_secret is None  # type: ignore
        assert user.is_2fa_enabled is False

    def test_user_creation_with_2fa(self):
        """Test 5: User se crea con campos 2FA."""
        user = User(
            id="123e4567-e89b-12d3-a456-426614174000",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="hashed_password_here",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            totp_secret="BASE32SECRET",
            is_2fa_enabled=True
        )

        assert user.totp_secret == "BASE32SECRET"  # type: ignore
        assert user.is_2fa_enabled is True

    def test_user_empty_name(self):
        """Test 2: User con name vacío lanza InvalidUserError."""
        with pytest.raises(InvalidUserError):
            User(
                id="123e4567-e89b-12d3-a456-426614174000",
                name="",  # name vacío
                email=Email("john@example.com"),
                password_hash="hashed_password_here",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

    def test_user_empty_id(self):
        """Test 3: User con ID vacío lanza InvalidUserError."""
        with pytest.raises(InvalidUserError):
            User(
                id="",  # id vacío
                name="John Doe",
                email=Email("john@example.com"),
                password_hash="hashed_password_here",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

    def test_user_mutable(self):
        """Test 4: User es mutable (sin frozen=True)."""
        user = User(
            id="123e4567-e89b-12d3-a456-426614174000",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="hashed_password_here",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # Entities pueden mutar (a diferencia de Value Objects)
        new_name = "Jane Doe"
        user.name = new_name
        assert user.name == new_name

    # --- __eq__ por identidad ---

    def test_user_equality_same_id(self):
        """Test 6: Dos User con el mismo id son iguales aunque difieran en otros campos."""
        now = datetime.now()
        user1 = User(
            id="same-id",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="hash1",
            created_at=now,
            updated_at=now
        )
        user2 = User(
            id="same-id",
            name="Jane Doe",
            email=Email("jane@example.com"),
            password_hash="hash2",
            created_at=now,
            updated_at=now
        )

        assert user1 == user2

    def test_user_inequality_different_id(self):
        """Test 7: Dos User con distinto id no son iguales."""
        now = datetime.now()
        user1 = User(
            id="id-one",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="hash1",
            created_at=now,
            updated_at=now
        )
        user2 = User(
            id="id-two",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="hash1",
            created_at=now,
            updated_at=now
        )

        assert user1 != user2

    # --- Comandos ---

    def test_enable_2fa_sets_secret_and_flag(self):
        """Test 8: enable_2fa() activa 2FA y guarda el secreto TOTP."""
        user = User(
            id="u-1",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="hash",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        assert user.is_2fa_enabled is False

        user.enable_2fa("TOTP_SECRET_BASE32")

        assert user.is_2fa_enabled is True
        assert user.totp_secret == "TOTP_SECRET_BASE32"

    def test_disable_2fa_clears_secret_and_flag(self):
        """Test 9: disable_2fa() desactiva 2FA y borra el secreto TOTP."""
        user = User(
            id="u-1",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="hash",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            totp_secret="TOTP_SECRET_BASE32",
            is_2fa_enabled=True
        )

        user.disable_2fa()

        assert user.is_2fa_enabled is False
        assert user.totp_secret is None

    def test_verify_email_sets_verified_flag(self):
        """Test 10: verify_email() marca is_email_verified como True."""
        user = User(
            id="u-1",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="hash",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        assert user.is_email_verified is False

        user.verify_email()

        assert user.is_email_verified is True

    def test_update_name_changes_name(self):
        """Test 11: update_name() actualiza el nombre del usuario."""
        user = User(
            id="u-1",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="hash",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        user.update_name("Jane Doe")

        assert user.name == "Jane Doe"

    def test_update_password_changes_hash(self):
        """Test 12: update_password() actualiza el hash de contraseña."""
        user = User(
            id="u-1",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="old_hash",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        user.update_password("new_hash")

        assert user.password_hash == "new_hash"

    # --- Queries ---

    def test_is_verified_returns_true_when_email_verified(self):
        """Test 13: is_verified() devuelve True cuando is_email_verified es True."""
        user = User(
            id="u-1",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="hash",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            is_email_verified=True
        )

        assert user.is_verified() is True

    def test_is_verified_returns_false_when_not_verified(self):
        """Test 14: is_verified() devuelve False cuando is_email_verified es False."""
        user = User(
            id="u-1",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="hash",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        assert user.is_verified() is False

    def test_is_2fa_required_returns_true_when_enabled(self):
        """Test 15: is_2fa_required() devuelve True cuando is_2fa_enabled es True."""
        user = User(
            id="u-1",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="hash",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            is_2fa_enabled=True,
            totp_secret="SECRET"
        )

        assert user.is_2fa_required() is True

    def test_is_2fa_required_returns_false_when_disabled(self):
        """Test 16: is_2fa_required() devuelve False cuando is_2fa_enabled es False."""
        user = User(
            id="u-1",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="hash",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        assert user.is_2fa_required() is False

    def test_has_oauth_password_returns_true_for_oauth_sentinel(self):
        """Test 17: has_oauth_password() devuelve True para el sentinel OAUTH_NO_PASSWORD."""
        user = User(
            id="u-1",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="OAUTH_NO_PASSWORD",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        assert user.has_oauth_password() is True

    def test_has_oauth_password_returns_false_for_real_hash(self):
        """Test 18: has_oauth_password() devuelve False para un hash real."""
        user = User(
            id="u-1",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="$2b$12$realhashhere",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        assert user.has_oauth_password() is False

    # --- Role ---

    def test_user_default_role_is_user(self):
        """Test 19: User se crea con role='user' por defecto."""
        user = User(
            id="u-1",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="hash",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert user.role == "user"

    def test_user_creation_with_admin_role(self):
        """Test 20: User se crea con role='admin' explícito."""
        user = User(
            id="u-1",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="hash",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            role="admin",
        )

        assert user.role == "admin"

    def test_user_invalid_role_raises_error(self):
        """Test 21: User con role inválido lanza InvalidUserError."""
        with pytest.raises(InvalidUserError):
            User(
                id="u-1",
                name="John Doe",
                email=Email("john@example.com"),
                password_hash="hash",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                role="superuser",
            )

    def test_is_admin_returns_true_for_admin_role(self):
        """Test 22: is_admin() devuelve True cuando role es 'admin'."""
        user = User(
            id="u-1",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="hash",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            role="admin",
        )

        assert user.is_admin() is True

    def test_is_admin_returns_false_for_user_role(self):
        """Test 23: is_admin() devuelve False cuando role es 'user'."""
        user = User(
            id="u-1",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash="hash",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert user.is_admin() is False
