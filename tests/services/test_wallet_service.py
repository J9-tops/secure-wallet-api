from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.transaction_model import Transaction, TransactionStatus, TransactionType
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

        sender_wallet = Mock(spec=Wallet)
        sender_wallet.id = "wallet1"
        sender_wallet.user_id = "user123"
        sender_wallet.balance = Decimal("10000.00")

        recipient_wallet = Mock(spec=Wallet)
        recipient_wallet.id = "wallet2"
        recipient_wallet.user_id = "user456"
        recipient_wallet.wallet_number = "4566678954356"
        recipient_wallet.balance = Decimal("5000.00")

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
        recipient_wallet.id = "wallet1"
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


class TestWalletCreation:
    """Test wallet creation and retrieval"""

    @pytest.fixture
    def wallet_service(self):
        return WalletService()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = "user123"
        user.email = "test@example.com"
        return user

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        return db

    @pytest.mark.asyncio
    async def test_get_or_create_wallet_existing(
        self, wallet_service, mock_user, mock_db
    ):
        """Test getting an existing wallet"""
        existing_wallet = Mock(spec=Wallet)
        existing_wallet.id = "wallet123"
        existing_wallet.user_id = "user123"
        existing_wallet.balance = Decimal("5000.00")

        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = existing_wallet
        mock_db.execute.return_value = result_mock

        wallet = await wallet_service.get_or_create_wallet(mock_db, mock_user)

        assert wallet.id == "wallet123"
        assert wallet.balance == Decimal("5000.00")
        assert not mock_db.add.called

    @pytest.mark.asyncio
    async def test_get_or_create_wallet_new(self, wallet_service, mock_user, mock_db):
        """Test creating a new wallet when none exists"""
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        await wallet_service.get_or_create_wallet(mock_db, mock_user)

        assert mock_db.add.called
        assert mock_db.flush.called

    @pytest.mark.asyncio
    async def test_get_balance(self, wallet_service, mock_user, mock_db):
        """Test getting wallet balance"""
        mock_wallet = Mock(spec=Wallet)
        mock_wallet.balance = Decimal("15000.50")

        with patch.object(
            wallet_service, "get_or_create_wallet", return_value=mock_wallet
        ):
            balance = await wallet_service.get_balance(mock_db, mock_user)

            assert balance == Decimal("15000.50")


class TestTransactionHistory:
    """Test transaction history retrieval"""

    @pytest.fixture
    def wallet_service(self):
        return WalletService()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = "user123"
        user.email = "test@example.com"
        return user

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        return db

    @pytest.mark.asyncio
    async def test_get_transactions_multiple(self, wallet_service, mock_user, mock_db):
        """Test getting multiple transactions"""
        txn1 = Mock(spec=Transaction)
        txn1.type = TransactionType.DEPOSIT
        txn1.amount = Decimal("5000.00")
        txn1.status = TransactionStatus.SUCCESS
        txn1.created_at = datetime.now(timezone.utc)

        txn2 = Mock(spec=Transaction)
        txn2.type = TransactionType.TRANSFER
        txn2.amount = Decimal("2000.00")
        txn2.status = TransactionStatus.SUCCESS
        txn2.created_at = datetime.now(timezone.utc)

        result_mock = Mock()
        scalars_mock = Mock()
        scalars_mock.all.return_value = [txn1, txn2]
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        transactions = await wallet_service.get_transactions(mock_db, mock_user)

        assert len(transactions) == 2
        assert transactions[0].type == TransactionType.DEPOSIT
        assert transactions[1].type == TransactionType.TRANSFER

    @pytest.mark.asyncio
    async def test_get_transactions_empty(self, wallet_service, mock_user, mock_db):
        """Test getting transactions when none exist"""
        result_mock = Mock()
        scalars_mock = Mock()
        scalars_mock.all.return_value = []
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        transactions = await wallet_service.get_transactions(mock_db, mock_user)

        assert len(transactions) == 0

    @pytest.mark.asyncio
    async def test_get_transactions_ordered_by_date(
        self, wallet_service, mock_user, mock_db
    ):
        """Test transactions are ordered by creation date (newest first)"""
        result_mock = Mock()
        scalars_mock = Mock()
        scalars_mock.all.return_value = []
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        await wallet_service.get_transactions(mock_db, mock_user)

        assert mock_db.execute.called


class TestDepositStatus:
    """Test deposit status retrieval"""

    @pytest.fixture
    def wallet_service(self):
        return WalletService()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = "user123"
        user.email = "test@example.com"
        return user

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        return db

    @pytest.mark.asyncio
    async def test_get_deposit_status_success(self, wallet_service, mock_user, mock_db):
        """Test getting deposit status for successful transaction"""
        transaction = Mock(spec=Transaction)
        transaction.reference = "TXN_123"
        transaction.status = TransactionStatus.SUCCESS
        transaction.amount = Decimal("5000.00")

        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = transaction
        mock_db.execute.return_value = result_mock

        status = await wallet_service.get_deposit_status(mock_db, "TXN_123", mock_user)

        assert status.reference == "TXN_123"
        assert status.status == "success"
        assert status.amount == Decimal("5000.00")

    @pytest.mark.asyncio
    async def test_get_deposit_status_pending(self, wallet_service, mock_user, mock_db):
        """Test getting deposit status for pending transaction"""
        transaction = Mock(spec=Transaction)
        transaction.reference = "TXN_456"
        transaction.status = TransactionStatus.PENDING
        transaction.amount = Decimal("3000.00")

        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = transaction
        mock_db.execute.return_value = result_mock

        status = await wallet_service.get_deposit_status(mock_db, "TXN_456", mock_user)

        assert status.status == "pending"

    @pytest.mark.asyncio
    async def test_get_deposit_status_not_found(
        self, wallet_service, mock_user, mock_db
    ):
        """Test getting deposit status for non-existent transaction"""
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        with pytest.raises(LookupError, match="Transaction not found"):
            await wallet_service.get_deposit_status(
                mock_db, "TXN_NONEXISTENT", mock_user
            )


class TestTransferEdgeCases:
    """Test edge cases for wallet transfers"""

    @pytest.fixture
    def wallet_service(self):
        return WalletService()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = "user123"
        user.email = "test@example.com"
        return user

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        return db

    @pytest.mark.asyncio
    async def test_transfer_to_nonexistent_wallet(
        self, wallet_service, mock_user, mock_db
    ):
        """Test transfer to non-existent wallet fails"""
        sender_wallet = Mock(spec=Wallet)
        sender_wallet.balance = Decimal("10000.00")

        sender_result = Mock()
        sender_result.scalar_one_or_none.return_value = sender_wallet

        recipient_result = Mock()
        recipient_result.scalar_one_or_none.return_value = None

        mock_db.execute.side_effect = [sender_result, recipient_result]

        with pytest.raises(LookupError, match="Recipient wallet not found"):
            await wallet_service.transfer_funds(
                db=mock_db,
                sender=mock_user,
                recipient_wallet_number="9999999999",
                amount=Decimal("1000.00"),
            )

    @pytest.mark.asyncio
    async def test_transfer_zero_amount(self, wallet_service, mock_user, mock_db):
        """Test transfer with zero amount fails"""
        with pytest.raises(ValueError, match="greater than zero"):
            await wallet_service.transfer_funds(
                db=mock_db,
                sender=mock_user,
                recipient_wallet_number="1234567890",
                amount=Decimal("0"),
            )

    @pytest.mark.asyncio
    async def test_transfer_negative_amount(self, wallet_service, mock_user, mock_db):
        """Test transfer with negative amount fails"""
        with pytest.raises(ValueError, match="greater than zero"):
            await wallet_service.transfer_funds(
                db=mock_db,
                sender=mock_user,
                recipient_wallet_number="1234567890",
                amount=Decimal("-100.00"),
            )

    @pytest.mark.asyncio
    async def test_transfer_sender_wallet_not_found(
        self, wallet_service, mock_user, mock_db
    ):
        """Test transfer fails when sender has no wallet"""
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        with pytest.raises(ValueError, match="Sender wallet not found"):
            await wallet_service.transfer_funds(
                db=mock_db,
                sender=mock_user,
                recipient_wallet_number="1234567890",
                amount=Decimal("1000.00"),
            )

    @pytest.mark.asyncio
    async def test_transfer_exact_balance(self, wallet_service, mock_user, mock_db):
        """Test transfer with exact wallet balance"""
        sender_wallet = Mock(spec=Wallet)
        sender_wallet.id = "wallet1"
        sender_wallet.user_id = "user123"
        sender_wallet.balance = Decimal("5000.00")

        recipient_wallet = Mock(spec=Wallet)
        recipient_wallet.id = "wallet2"
        recipient_wallet.user_id = "user456"
        recipient_wallet.wallet_number = "1234567890"
        recipient_wallet.balance = Decimal("0.00")

        sender_result = Mock()
        sender_result.scalar_one_or_none.return_value = sender_wallet

        recipient_result = Mock()
        recipient_result.scalar_one_or_none.return_value = recipient_wallet

        mock_db.execute.side_effect = [sender_result, recipient_result]

        result = await wallet_service.transfer_funds(
            db=mock_db,
            sender=mock_user,
            recipient_wallet_number="1234567890",
            amount=Decimal("5000.00"),
        )

        assert result.status == "success"
        assert sender_wallet.balance == Decimal("0.00")
        assert recipient_wallet.balance == Decimal("5000.00")


class TestDepositEdgeCases:
    """Test edge cases for deposits"""

    @pytest.fixture
    def wallet_service(self):
        return WalletService()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = "user123"
        user.email = "test@example.com"
        return user

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        return db

    @pytest.mark.asyncio
    async def test_deposit_negative_amount(self, wallet_service, mock_user, mock_db):
        """Test deposit with negative amount fails"""
        with pytest.raises(ValueError, match="greater than zero"):
            await wallet_service.initiate_deposit(
                db=mock_db, user=mock_user, amount=Decimal("-1000.00")
            )

    @pytest.mark.asyncio
    async def test_deposit_large_amount(self, wallet_service, mock_user, mock_db):
        """Test deposit with very large amount"""
        with patch(
            "src.services.wallet_service.paystack_service.initialize_transaction"
        ) as mock_paystack:
            mock_paystack.return_value = {
                "authorization_url": "https://paystack.co/pay/abc123",
                "access_code": "abc123",
            }

            result = await wallet_service.initiate_deposit(
                db=mock_db, user=mock_user, amount=Decimal("1000000.00")
            )

            assert result.reference.startswith("TXN_")
            assert "paystack.co" in result.authorization_url


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
