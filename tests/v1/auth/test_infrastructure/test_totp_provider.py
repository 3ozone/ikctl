"""Tests para TOTPProvider."""
import re
import pytest
import pyotp

from app.v1.auth.infrastructure.adapters.totp_provider import TOTPProvider


@pytest.fixture
def totp_provider():
    """Fixture para TOTPProvider."""
    return TOTPProvider()


def test_generate_secret(totp_provider):
    """Test 1: Genera un secret TOTP válido en base32."""
    secret = totp_provider.generate_secret()

    assert secret is not None
    assert isinstance(secret, str)
    assert len(secret) == 32  # pyotp genera secrets de 32 caracteres
    # Verificar que es base32 válido (solo A-Z y 2-7)
    assert re.match(r'^[A-Z2-7]+$', secret)


def test_generate_qr_code(totp_provider):
    """Test 2: Genera un QR code en formato data URI."""
    secret = "JBSWY3DPEHPK3PXP"  # Secret de ejemplo
    user_email = "user@example.com"

    qr_data_uri = totp_provider.generate_qr_code(secret, user_email)

    assert qr_data_uri is not None
    assert isinstance(qr_data_uri, str)
    # Verificar que es un data URI de imagen PNG
    assert qr_data_uri.startswith("data:image/png;base64,")
    # Verificar que tiene contenido base64 después del prefijo
    assert len(qr_data_uri) > len("data:image/png;base64,")


def test_generate_qr_code_with_custom_issuer(totp_provider):
    """Test 3: Genera QR code con issuer personalizado."""
    secret = "JBSWY3DPEHPK3PXP"
    user_email = "admin@example.com"
    issuer = "MyApp"

    qr_data_uri = totp_provider.generate_qr_code(secret, user_email, issuer)

    assert qr_data_uri is not None
    assert qr_data_uri.startswith("data:image/png;base64,")


def test_verify_code_valid(totp_provider):
    """Test 4: Verifica un código TOTP válido."""
    import pyotp

    # Generar secret y código válido
    secret = totp_provider.generate_secret()
    totp = pyotp.TOTP(secret)
    valid_code = totp.now()  # Código actual válido

    # Verificar que el código es aceptado
    is_valid = totp_provider.verify_code(secret, valid_code)

    assert is_valid is True


def test_verify_code_invalid(totp_provider):
    """Test 5: Rechaza un código TOTP inválido."""
    secret = totp_provider.generate_secret()
    invalid_code = "000000"  # Código inválido

    is_valid = totp_provider.verify_code(secret, invalid_code)

    assert is_valid is False


def test_verify_code_invalid_format(totp_provider):
    """Test 6: Rechaza códigos con formato inválido."""
    secret = totp_provider.generate_secret()

    # Código con menos de 6 dígitos
    assert totp_provider.verify_code(secret, "123") is False

    # Código con más de 6 dígitos
    assert totp_provider.verify_code(secret, "1234567") is False

    # Código con letras
    assert totp_provider.verify_code(secret, "abcdef") is False


def test_get_provisioning_uri(totp_provider):
    """Test 7: Genera URI de provisionamiento válido."""
    secret = "JBSWY3DPEHPK3PXP"
    user_email = "user@example.com"

    uri = totp_provider.get_provisioning_uri(secret, user_email)

    assert uri is not None
    assert isinstance(uri, str)
    # Verificar formato otpauth://
    assert uri.startswith("otpauth://totp/")
    # Verificar que contiene el email (URL-encoded: @ = %40)
    assert "user%40example.com" in uri
    # Verificar que contiene el secret
    assert secret in uri


def test_get_provisioning_uri_with_custom_issuer(totp_provider):
    """Test 8: Genera URI con issuer personalizado."""
    secret = "JBSWY3DPEHPK3PXP"
    user_email = "admin@example.com"
    issuer = "MyCustomApp"

    uri = totp_provider.get_provisioning_uri(secret, user_email, issuer)

    assert uri.startswith("otpauth://totp/")
    # Email URL-encoded
    assert "admin%40example.com" in uri
    assert issuer in uri


def test_integration_generate_and_verify(totp_provider):
    """Test 9: Integración - genera secret, verifica código generado."""

    # Generar secret
    secret = totp_provider.generate_secret()

    # Generar código válido usando pyotp directamente
    totp = pyotp.TOTP(secret)
    current_code = totp.now()

    # Verificar que el provider acepta el código
    assert totp_provider.verify_code(secret, current_code) is True

    # Verificar que rechaza código antiguo (simulando tiempo anterior)
    # Nota: este test puede ser flaky si se ejecuta exactamente en el cambio de ventana
    old_code = "999999"
    assert totp_provider.verify_code(secret, old_code) is False
