"""Shared fixtures for all tests."""
from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_repository():
    """Mock repository for testing."""
    return Mock()
