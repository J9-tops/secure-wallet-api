from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from httpx import Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user_model import User


@pytest.fixture
def client():
    """Create a test client with dependency overrides"""
    from src.db.session import get_db
    from src.main import app
    from src.utils.auth import get_current_user

    # Mock database dependency
    async def override_get_db():
        mock_db = AsyncMock(spec=AsyncSession)
        yield mock_db

    # Mock auth dependency
    async def override_get_current_user():
        return User(
            id="test_user_id",
            email="test@example.com",
            google_id="google_123",
            is_active=True,
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def mock_db_session():
    """Create a properly configured mock database session"""
    session = AsyncMock(spec=AsyncSession)

    # Configure execute to return a mock result
    mock_result = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)

    # Make scalar and scalar_one_or_none async-aware
    async def async_scalar():
        return mock_result.scalar.return_value

    async def async_scalar_one_or_none():
        return mock_result.scalar_one_or_none.return_value

    mock_result.scalar = AsyncMock(side_effect=async_scalar)
    mock_result.scalar_one_or_none = AsyncMock(side_effect=async_scalar_one_or_none)

    # Configure other session methods
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()

    # Mock begin context manager
    session.begin = MagicMock()
    session.begin.return_value.__aenter__ = AsyncMock(return_value=session)
    session.begin.return_value.__aexit__ = AsyncMock(return_value=None)

    return session


@pytest.fixture
def mock_user():
    """Create a mock user with all required attributes"""
    return User(
        id="test_user_id",
        email="test@example.com",
        google_id="google_123",
        name="Test User",
        is_active=True,
    )


@pytest.fixture
def mock_httpx_response():
    """Helper to create properly mocked httpx Response objects"""

    def _create_response(status_code, json_data=None):
        from httpx import Response

        response = Response(status_code, json=json_data)
        # Set the request attribute to avoid raise_for_status error
        response._request = Request("GET", "https://example.com")
        return response

    return _create_response
