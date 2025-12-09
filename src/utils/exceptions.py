"""
Custom Error Classes for Better Error Handling
"""


class WalletServiceError(Exception):
    """Base exception for wallet service"""

    pass


class AuthenticationError(WalletServiceError):
    """Authentication related errors"""

    pass


class InsufficientBalanceError(WalletServiceError):
    """Raised when wallet has insufficient balance"""

    pass


class InvalidAmountError(WalletServiceError):
    """Raised when amount is invalid"""

    pass


class WalletNotFoundError(WalletServiceError):
    """Raised when wallet is not found"""

    pass


class TransactionNotFoundError(WalletServiceError):
    """Raised when transaction is not found"""

    pass


class PaymentGatewayError(WalletServiceError):
    """Payment gateway related errors"""

    pass


class APIKeyLimitExceededError(WalletServiceError):
    """Raised when API key limit is exceeded"""

    pass


class APIKeyExpiredError(WalletServiceError):
    """Raised when API key is expired"""

    pass


class WebhookVerificationError(WalletServiceError):
    """Raised when webhook signature verification fails"""

    pass


class DuplicateTransactionError(WalletServiceError):
    """Raised when attempting to process duplicate transaction"""

    pass
