"""
Paystack Payment Service
"""

import logging
import os
from decimal import Decimal
from typing import Any, Dict

import httpx
from dotenv import load_dotenv

load_dotenv()

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")
PAYSTACK_BASE_URL = "https://api.paystack.co"

logger = logging.getLogger(__name__)


class PaystackService:
    """Service for interacting with Paystack API"""

    def __init__(self):
        self.secret_key = PAYSTACK_SECRET_KEY
        self.base_url = PAYSTACK_BASE_URL

        if not self.secret_key:
            logger.warning("PAYSTACK_SECRET_KEY not configured")

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    def initialize_transaction(
        self, email: str, amount: Decimal, reference: str, callback_url: str = None
    ) -> Dict[str, Any]:
        if not self.secret_key:
            raise Exception("Paystack secret key not configured")

        amount_in_kobo = int(amount * 100)

        payload = {
            "email": email,
            "amount": amount_in_kobo,
            "reference": reference,
        }

        if callback_url:
            payload["callback_url"] = callback_url

        try:
            response = httpx.post(
                f"{self.base_url}/transaction/initialize",
                json=payload,
                headers=self._get_headers(),
                timeout=30.0,
            )

            response.raise_for_status()
            data = response.json()

            if not data.get("status"):
                error_msg = data.get("message", "Unknown error")
                logger.error(f"Paystack initialization failed: {error_msg}")
                raise Exception(f"Payment initialization failed: {error_msg}")

            return data["data"]
        except httpx.HTTPError as e:
            logger.error(f"Paystack HTTP error: {str(e)}", exc_info=True)
            raise Exception("Payment service temporarily unavailable")
        except Exception as e:
            logger.error(f"Paystack error: {str(e)}", exc_info=True)
            raise Exception("Failed to initialize payment")

    def verify_transaction(self, reference: str) -> Dict[str, Any]:
        if not self.secret_key:
            raise Exception("Paystack secret key not configured")

        try:
            response = httpx.get(
                f"{self.base_url}/transaction/verify/{reference}",
                headers=self._get_headers(),
                timeout=30.0,
            )

            response.raise_for_status()
            data = response.json()

            if not data.get("status"):
                error_msg = data.get("message", "Unknown error")
                logger.error(f"Paystack verification failed: {error_msg}")
                raise Exception(f"Payment verification failed: {error_msg}")

            return data["data"]
        except httpx.HTTPError as e:
            logger.error(f"Paystack HTTP error: {str(e)}", exc_info=True)
            raise Exception("Payment verification service temporarily unavailable")
        except Exception as e:
            logger.error(f"Paystack error: {str(e)}", exc_info=True)
            raise Exception("Failed to verify payment")


paystack_service = PaystackService()
