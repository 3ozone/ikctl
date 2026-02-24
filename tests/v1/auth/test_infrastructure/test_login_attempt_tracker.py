"""Tests para ValkeyLoginAttemptTracker service."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.v1.auth.infrastructure.services.login_attempt_tracker import ValkeyLoginAttemptTracker
from app.v1.auth.infrastructure.exceptions import InfrastructureException


@pytest.fixture
def mock_valkey():
    """Mock de cliente Valkey."""
    mock = AsyncMock()
    return mock


@pytest.fixture
def attempt_tracker(mock_valkey):
    """Fixture para ValkeyLoginAttemptTracker con mock de Valkey."""
    return ValkeyLoginAttemptTracker(valkey_client=mock_valkey)


@pytest.mark.asyncio
async def test_record_failed_attempt_increments_counter(attempt_tracker, mock_valkey):
    """Test 1: Registrar intento fallido incrementa el contador."""
    mock_valkey.incr.return_value = 1
    mock_valkey.ttl.return_value = -1  # Sin TTL

    count = await attempt_tracker.record_failed_attempt("user@example.com")

    assert count == 1
    mock_valkey.incr.assert_called_once_with("login_attempts:user@example.com")
    mock_valkey.expire.assert_called_once_with(
        "login_attempts:user@example.com", 900)  # 15 min = 900s


@pytest.mark.asyncio
async def test_is_blocked_under_limit(attempt_tracker, mock_valkey):
    """Test 2: No está bloqueado con menos de 5 intentos."""
    mock_valkey.get.return_value = "3"

    is_blocked = await attempt_tracker.is_blocked("user@example.com")

    assert is_blocked is False
    mock_valkey.get.assert_called_once_with("login_attempts:user@example.com")


@pytest.mark.asyncio
async def test_is_blocked_at_limit(attempt_tracker, mock_valkey):
    """Test 3: No está bloqueado exactamente con 5 intentos."""
    mock_valkey.get.return_value = "5"

    is_blocked = await attempt_tracker.is_blocked("user@example.com")

    assert is_blocked is False


@pytest.mark.asyncio
async def test_is_blocked_over_limit(attempt_tracker, mock_valkey):
    """Test 4: Está bloqueado con más de 5 intentos."""
    mock_valkey.get.return_value = "6"

    is_blocked = await attempt_tracker.is_blocked("user@example.com")

    assert is_blocked is True


@pytest.mark.asyncio
async def test_is_blocked_no_attempts(attempt_tracker, mock_valkey):
    """Test 5: No está bloqueado si no hay intentos registrados."""
    mock_valkey.get.return_value = None

    is_blocked = await attempt_tracker.is_blocked("user@example.com")

    assert is_blocked is False


@pytest.mark.asyncio
async def test_reset_attempts_after_successful_login(attempt_tracker, mock_valkey):
    """Test 6: Resetear intentos después de login exitoso."""
    await attempt_tracker.reset_attempts("user@example.com")

    mock_valkey.delete.assert_called_once_with(
        "login_attempts:user@example.com")


@pytest.mark.asyncio
async def test_get_remaining_attempts_no_failures(attempt_tracker, mock_valkey):
    """Test 7: Obtener intentos restantes sin fallos previos."""
    mock_valkey.get.return_value = None

    remaining = await attempt_tracker.get_remaining_attempts("user@example.com")

    assert remaining == 5


@pytest.mark.asyncio
async def test_get_remaining_attempts_with_failures(attempt_tracker, mock_valkey):
    """Test 8: Obtener intentos restantes con algunos fallos."""
    mock_valkey.get.return_value = "2"

    remaining = await attempt_tracker.get_remaining_attempts("user@example.com")

    assert remaining == 3  # 5 - 2 = 3


@pytest.mark.asyncio
async def test_get_remaining_attempts_blocked(attempt_tracker, mock_valkey):
    """Test 9: Obtener intentos restantes cuando está bloqueado."""
    mock_valkey.get.return_value = "7"

    remaining = await attempt_tracker.get_remaining_attempts("user@example.com")

    assert remaining == 0


@pytest.mark.asyncio
async def test_multiple_users_independent(attempt_tracker, mock_valkey):
    """Test 10: Múltiples usuarios tienen contadores independientes."""
    def get_side_effect(key):
        if key == "login_attempts:user1@example.com":
            return "6"
        elif key == "login_attempts:user2@example.com":
            return "2"
        return None

    mock_valkey.get.side_effect = get_side_effect

    # Usuario 1 bloqueado
    blocked1 = await attempt_tracker.is_blocked("user1@example.com")
    assert blocked1 is True

    # Usuario 2 no bloqueado
    blocked2 = await attempt_tracker.is_blocked("user2@example.com")
    assert blocked2 is False


@pytest.mark.asyncio
async def test_record_failed_attempt_valkey_error(attempt_tracker, mock_valkey):
    """Test 11: Maneja error de Valkey al registrar intento."""
    mock_valkey.incr.side_effect = Exception("Connection refused")

    with pytest.raises(InfrastructureException) as exc_info:
        await attempt_tracker.record_failed_attempt("user@example.com")

    assert "Failed to record login attempt" in str(exc_info.value)


@pytest.mark.asyncio
async def test_is_blocked_valkey_error(attempt_tracker, mock_valkey):
    """Test 12: Maneja error de Valkey al verificar bloqueo."""
    mock_valkey.get.side_effect = Exception("Connection timeout")

    with pytest.raises(InfrastructureException) as exc_info:
        await attempt_tracker.is_blocked("user@example.com")

    assert "Failed to check login block status" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ttl_set_only_on_first_attempt(attempt_tracker, mock_valkey):
    """Test 13: TTL se establece solo en el primer intento."""
    # Primer intento - sin TTL
    mock_valkey.incr.return_value = 1
    mock_valkey.ttl.return_value = -1

    await attempt_tracker.record_failed_attempt("user@example.com")

    mock_valkey.expire.assert_called_once()

    # Segundo intento - ya tiene TTL
    mock_valkey.reset_mock()
    mock_valkey.incr.return_value = 2
    mock_valkey.ttl.return_value = 850  # TTL existente

    await attempt_tracker.record_failed_attempt("user@example.com")

    mock_valkey.expire.assert_not_called()
