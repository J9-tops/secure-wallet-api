import logging

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.models.user_model import User
from src.schemas.wallet_schemas import (
    DepositRequest,
    TransactionResponse,
    TransferRequest,
)
from src.services.wallet_service import wallet_service
from src.services.webhook_service import webhook_service
from src.utils.auth import require_permission
from src.utils.responses import error_response, success_response

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/deposit")
async def initiate_deposit(
    request: DepositRequest,
    current_user: User = Depends(require_permission("deposit")),
    db: AsyncSession = Depends(get_db),
):
    """
    Initiate a Paystack deposit
    Requires: JWT or API key with 'deposit' permission
    """
    try:
        result = await wallet_service.initiate_deposit(
            db=db, user=current_user, amount=request.amount
        )

        return success_response(
            status_code=status.HTTP_200_OK,
            message="Deposit initiated successfully",
            data=result,
        )

    except ValueError as e:
        logger.warning(f"Invalid deposit request from user {current_user.id}: {str(e)}")
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid deposit amount",
            error="INVALID_AMOUNT",
            errors={"amount": [str(e)]},
        )
    except Exception as e:
        logger.error(
            f"Deposit initiation failed for user {current_user.id}: {str(e)}",
            exc_info=True,
        )
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Unable to process deposit. Please try again",
            error="SERVER_ERROR",
        )


@router.post("/paystack/webhook")
async def paystack_webhook(
    request: Request,
    x_paystack_signature: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Paystack webhook events
    This is the ONLY endpoint that credits wallets
    """
    try:
        body = await request.body()

        await webhook_service.process_paystack_webhook(
            db=db, body=body, signature=x_paystack_signature
        )

        return ({"status": True},)

    except ValueError as e:
        logger.warning(f"Invalid webhook signature or data: {str(e)}")
        return error_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message="Invalid webhook signature",
            error="UNAUTHORIZED",
        )
    except LookupError as e:
        logger.warning(f"Webhook processing - transaction not found: {str(e)}")
        return success_response(
            status_code=status.HTTP_200_OK,
            message="Transaction not found, but webhook acknowledged",
            data={"status": True, "note": "Transaction ignored"},
        )
    except Exception as e:
        logger.error(f"Webhook processing failed: {str(e)}", exc_info=True)
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Webhook processing failed",
            error="SERVER_ERROR",
        )


@router.get("/deposit/{reference}/status")
async def get_deposit_status(
    reference: str,
    current_user: User = Depends(require_permission("read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Get deposit status (read-only)
    Does NOT credit wallet - only webhooks credit wallets
    Requires: JWT or API key with 'read' permission
    """
    try:
        result = await wallet_service.get_deposit_status(
            db=db, reference=reference, user=current_user
        )
        return (result,)

    except LookupError:
        logger.info(f"Transaction not found for user {current_user.id}: {reference}")
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Transaction not found",
            error="NOT_FOUND",
            errors={"reference": ["Reference does not exist"]},
        )
    except Exception as e:
        logger.error(
            f"Failed to get deposit status for user {current_user.id}: {str(e)}",
            exc_info=True,
        )
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Unable to retrieve transaction status",
            error="SERVER_ERROR",
        )


@router.get("/balance")
async def get_balance(
    current_user: User = Depends(require_permission("read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Get wallet balance
    Requires: JWT or API key with 'read' permission
    """
    try:
        balance = await wallet_service.get_balance(db=db, user=current_user)
        return ({"balance": balance},)

    except Exception as e:
        logger.error(
            f"Failed to get balance for user {current_user.id}: {str(e)}", exc_info=True
        )
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Unable to retrieve balance",
            error="SERVER_ERROR",
        )


@router.post("/transfer")
async def transfer_funds(
    request: TransferRequest,
    current_user: User = Depends(require_permission("transfer")),
    db: AsyncSession = Depends(get_db),
):
    """
    Transfer funds to another wallet
    Requires: JWT or API key with 'transfer' permission
    """
    try:
        result = await wallet_service.transfer_funds(
            db=db,
            sender=current_user,
            recipient_wallet_number=request.wallet_number,
            amount=request.amount,
        )
        return result

    except ValueError as e:
        logger.warning(f"Invalid transfer from user {current_user.id}: {str(e)}")
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid transfer request",
            error="INVALID_REQUEST",
            errors={"details": [str(e)]},
        )
    except LookupError as e:
        logger.warning(
            f"Transfer target not found for user {current_user.id}: {str(e)}"
        )
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Recipient wallet not found",
            error="NOT_FOUND",
        )
    except Exception as e:
        logger.error(
            f"Transfer failed for user {current_user.id}: {str(e)}", exc_info=True
        )
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Transfer failed. Please try again",
            error="SERVER_ERROR",
        )


@router.get("/transactions")
async def get_transactions(
    current_user: User = Depends(require_permission("read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Get transaction history
    Requires: JWT or API key with 'read' permission
    """
    try:
        transactions = await wallet_service.get_transactions(db=db, user=current_user)
        data_list = [TransactionResponse.from_orm(t) for t in transactions]

        return ({"transactions": data_list, "count": len(data_list)},)

    except Exception as e:
        logger.error(
            f"Failed to get transactions for user {current_user.id}: {str(e)}",
            exc_info=True,
        )
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Unable to retrieve transaction history",
            error="SERVER_ERROR",
        )
