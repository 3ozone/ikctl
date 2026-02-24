"""Tests para ValkeyRateLimiter service."""
import pytest
from unittest.mock import AsyncMock, MagicMock
import asyncio

from app.v1.auth.infrastructure.services.rate_limiter import ValkeyRateLimiter
from app.v1.auth.infrastructure.exceptions import InfrastructureException


@pytest.fixture
def mock_valkey():
    """Mock de cliente Valkey."""
    mock = AsyncMock()
    return mock


@pytest.fixture
def rate_limiter(mock_valkey):
    """Fixture para ValkeyRateLimiter con mock de Valkey."""
    return ValkeyRateLimiter(valkey_client=mock_valkey)


@pytest.mark.asyncio
async def test_is_allowed_under_limit(rate_limiter, mock_valkey):
    """Test 1: Permite request cuando está bajo el límite."""
    # Simular 5 requests ya realizadas (límite es 10)
    mock_valkey.get.return_value = "5"

    allowed = await rate_limiter.is_allowed(
        key="login:192.168.1.1",
        max_requests=10,
        window_seconds=60
    )

    assert allowed is True
    mock_valkey.get.assert_called_once_with("ratelimit:login:192.168.1.1")


@pytest.mark.asyncio
async def test_is_allowed_at_limit(rate_limiter, mock_valkey):
    """Test 2: Permite request cuando está exactamente en el límite."""
    # Simular 10 requests (límite es 10)
    mock_valkey.get.return_value = "10"

    allowed = await rate_limiter.is_allowed(
        key="login:192.168.1.1",
        max_requests=10,
        window_seconds=60
    )

    assert allowed is True


@pytest.mark.asyncio
async def test_is_allowed_over_limit(rate_limiter, mock_valkey):
    """Test 3: Bloquea request cuando supera el límite."""
    # Simular 11 requests (límite es 10)
    mock_valkey.get.return_value = "11"

    allowed = await rate_limiter.is_allowed(
        key="login:192.168.1.1",
        max_requests=10,
        window_seconds=60
    )

    assert allowed is False


@pytest.mark.asyncio
async def test_is_allowed_first_request(rate_limiter, mock_valkey):
    """Test 4: Permite primer request (key no existe en Valkey)."""
    # Key no existe, Valkey retorna None
    mock_valkey.get.return_value = None

    allowed = await rate_limiter.is_allowed(
        key="login:10.0.0.1",
        max_requests=10,
        window_seconds=60
    )

    assert allowed is True


@pytest.mark.asyncio
async def test_increment_creates_key_with_ttl(rate_limiter, mock_valkey):
    """Test 5: Increment crea key nueva con TTL correcto."""
    # Primera request, key no existe
    mock_valkey.incr.return_value = 1
    mock_valkey.ttl.return_value = -1  # Key sin TTL

    count = await rate_limiter.increment(
        key="login:192.168.1.100",
        window_seconds=60
    )

    assert count == 1
    mock_valkey.incr.assert_called_once_with("ratelimit:login:192.168.1.100")
    mock_valkey.expire.assert_called_once_with(
        "ratelimit:login:192.168.1.100", 60)


@pytest.mark.asyncio
async def test_increment_existing_key(rate_limiter, mock_valkey):
    """Test 6: Increment incrementa key existente sin modificar TTL."""
    # Key existe con TTL
    mock_valkey.incr.return_value = 5
    mock_valkey.ttl.return_value = 45  # TTL existente

    count = await rate_limiter.increment(
        key="login:192.168.1.1",
        window_seconds=60
    )

    assert count == 5
    mock_valkey.incr.assert_called_once()
    # No debe llamar a expire si ya tiene TTL
    mock_valkey.expire.assert_not_called()


@pytest.mark.asyncio
async def test_multiple_keys_independent(rate_limiter, mock_valkey):
    """Test 7: Múltiples keys son independientes."""
    # Configurar respuestas diferentes para cada key
    def get_side_effect(key):
        if key == "ratelimit:login:192.168.1.1":
            return "10"
        elif key == "ratelimit:login:10.0.0.1":
            return "2"
        return None

    mock_valkey.get.side_effect = get_side_effect

    # Primera IP en el límite
    allowed1 = await rate_limiter.is_allowed("login:192.168.1.1", 10, 60)
    assert allowed1 is True

    # Segunda IP bajo el límite
    allowed2 = await rate_limiter.is_allowed("login:10.0.0.1", 10, 60)
    assert allowed2 is True


@pytest.mark.asyncio
async def test_increment_valkey_error(rate_limiter, mock_valkey):
    """Test 8: Maneja error de conexión a Valkey en increment."""
    mock_valkey.incr.side_effect = Exception("Connection refused")

    with pytest.raises(InfrastructureException) as exc_info:
        await rate_limiter.increment("login:192.168.1.1", 60)

    assert "Rate limiter increment failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_is_allowed_valkey_error(rate_limiter, mock_valkey):
    """Test 9: Maneja error de conexión a Valkey en is_allowed."""
    mock_valkey.get.side_effect = Exception("Connection timeout")

    with pytest.raises(InfrastructureException) as exc_info:
        await rate_limiter.is_allowed("login:192.168.1.1", 10, 60)

    assert "Rate limiter check failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_window_expiration_resets_counter(rate_limiter, mock_valkey):
    """Test 10: Después de expirar el window, el contador está en 0."""
    # Simular que la key no existe (expiró)
    mock_valkey.get.return_value = None

    allowed = await rate_limiter.is_allowed("login:192.168.1.1", 10, 60)

    assert allowed is True
