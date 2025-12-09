from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user_model import User
from src.models.wallet_model import Wallet
from src.services.wallet_service import WalletService


class TestWalletService:
    """Test Wallet Operations - Objectives: deposits, transfers, balance"""

    @pytest.fixture
    def wallet_service(self):
        return WalletService()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = "user123"
        user.email = "test@example.com"
        return user

    @pytest.mark.asyncio
    async def test_initiate_deposit_success(self, wallet_service, mock_user):
        """Test initiating a Paystack deposit"""
        db = AsyncMock(spec=AsyncSession)

        with patch(
            "src.services.wallet_service.paystack_service.initialize_transaction"
        ) as mock_paystack:
            mock_paystack.return_value = {
                "authorization_url": "https://paystack.co/pay/abc123",
                "access_code": "abc123",
            }

            result = await wallet_service.initiate_deposit(
                db=db, user=mock_user, amount=Decimal("5000.00")
            )

            assert result.reference.startswith("TXN_")
            assert "paystack.co" in result.authorization_url
            assert db.add.called
            assert db.commit.called

    @pytest.mark.asyncio
    async def test_initiate_deposit_invalid_amount(self, wallet_service, mock_user):
        """Test deposit fails with invalid amount"""
        db = AsyncMock(spec=AsyncSession)

        with pytest.raises(ValueError, match="greater than zero"):
            await wallet_service.initiate_deposit(
                db=db, user=mock_user, amount=Decimal("0")
            )

    @pytest.mark.asyncio
    async def test_transfer_funds_success(self, wallet_service, mock_user):
        """Test successful wallet-to-wallet transfer"""
        db = AsyncMock(spec=AsyncSession)

        # Mock sender wallet
        sender_wallet = Mock(spec=Wallet)
        sender_wallet.id = "wallet1"
        sender_wallet.user_id = "user123"
        sender_wallet.balance = Decimal("10000.00")

        # Mock recipient wallet
        recipient_wallet = Mock(spec=Wallet)
        recipient_wallet.id = "wallet2"
        recipient_wallet.user_id = "user456"
        recipient_wallet.wallet_number = "4566678954356"
        recipient_wallet.balance = Decimal("5000.00")

        # Mock execute calls
        sender_result = Mock()
        sender_result.scalar_one_or_none.return_value = sender_wallet

        recipient_result = Mock()
        recipient_result.scalar_one_or_none.return_value = recipient_wallet

        db.execute.side_effect = [sender_result, recipient_result]

        result = await wallet_service.transfer_funds(
            db=db,
            sender=mock_user,
            recipient_wallet_number="4566678954356",
            amount=Decimal("3000.00"),
        )

        assert result.status == "success"
        assert sender_wallet.balance == Decimal("7000.00")
        assert recipient_wallet.balance == Decimal("8000.00")
        assert db.commit.called

    @pytest.mark.asyncio
    async def test_transfer_insufficient_balance(self, wallet_service, mock_user):
        """Test transfer fails with insufficient balance"""
        db = AsyncMock(spec=AsyncSession)

        sender_wallet = Mock(spec=Wallet)
        sender_wallet.balance = Decimal("1000.00")

        sender_result = Mock()
        sender_result.scalar_one_or_none.return_value = sender_wallet
        db.execute.return_value = sender_result

        with pytest.raises(ValueError, match="Insufficient balance"):
            await wallet_service.transfer_funds(
                db=db,
                sender=mock_user,
                recipient_wallet_number="4566678954356",
                amount=Decimal("5000.00"),
            )

    @pytest.mark.asyncio
    async def test_transfer_to_self_fails(self, wallet_service, mock_user):
        """Test transfer to own wallet is rejected"""
        db = AsyncMock(spec=AsyncSession)

        sender_wallet = Mock(spec=Wallet)
        sender_wallet.id = "wallet1"
        sender_wallet.balance = Decimal("10000.00")

        recipient_wallet = Mock(spec=Wallet)
        recipient_wallet.id = "wallet1"  # Same wallet
        recipient_wallet.wallet_number = "1234567890"

        sender_result = Mock()
        sender_result.scalar_one_or_none.return_value = sender_wallet

        recipient_result = Mock()
        recipient_result.scalar_one_or_none.return_value = recipient_wallet

        db.execute.side_effect = [sender_result, recipient_result]

        with pytest.raises(ValueError, match="Cannot transfer to your own wallet"):
            await wallet_service.transfer_funds(
                db=db,
                sender=mock_user,
                recipient_wallet_number="1234567890",
                amount=Decimal("1000.00"),
            )

    @pytest.mark.asyncio
    async def test_get_balance(self, wallet_service, mock_user):
        """Test retrieving wallet balance"""
        db = AsyncMock(spec=AsyncSession)

        wallet = Mock(spec=Wallet)
        wallet.balance = Decimal("15000.00")

        with patch.object(wallet_service, "get_or_create_wallet", return_value=wallet):
            balance = await wallet_service.get_balance(db, mock_user)

            assert balance == Decimal("15000.00")
