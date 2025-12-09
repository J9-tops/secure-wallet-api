from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.services.paystack_service import PaystackService


class TestPaystackService:
    """Test Paystack API Integration"""

    @pytest.fixture
    def paystack_service(self):
        service = PaystackService()
        service.secret_key = "test_secret_key"
        return service

    @pytest.mark.asyncio
    async def test_initialize_transaction_success(self, paystack_service):
        """Test successful Paystack transaction initialization"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": True,
            "data": {
                "authorization_url": "https://paystack.co/pay/abc",
                "access_code": "abc123",
            },
        }
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await paystack_service.initialize_transaction(
                email="test@example.com", amount=Decimal("5000.00"), reference="TXN_123"
            )

            assert "authorization_url" in result
            assert "paystack.co" in result["authorization_url"]

    @pytest.mark.asyncio
    async def test_verify_transaction_success(self, paystack_service):
        """Test successful transaction verification"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": True,
            "data": {"status": "success", "amount": 500000, "reference": "TXN_123"},
        }
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await paystack_service.verify_transaction("TXN_123")

            assert result["status"] == "success"
            assert result["reference"] == "TXN_123"
