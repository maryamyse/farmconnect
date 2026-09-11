"""
Daraja API client — handles OAuth token retrieval and B2C bulk payout requests.

Safaricom Daraja docs: https://developer.safaricom.co.ke/
"""
import base64
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class DarajaConfigError(Exception):
    """Raised when required Daraja settings are missing."""
    pass


class DarajaAPIError(Exception):
    """Raised when a Daraja API call fails."""
    pass


def _require_credentials():
    missing = []
    if not settings.DARAJA_CONSUMER_KEY:
        missing.append('DARAJA_CONSUMER_KEY')
    if not settings.DARAJA_CONSUMER_SECRET:
        missing.append('DARAJA_CONSUMER_SECRET')
    if missing:
        raise DarajaConfigError(
            f"Missing required Daraja settings: {', '.join(missing)}. "
            f"Add these to your .env file."
        )


def get_access_token() -> str:
    """
    Fetch an OAuth access token from Daraja using Consumer Key/Secret.
    Tokens are short-lived (typically 1 hour) — callers should not cache
    this beyond a single task execution without checking expiry.
    """
    _require_credentials()

    url = f"{settings.DARAJA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
    credentials = f"{settings.DARAJA_CONSUMER_KEY}:{settings.DARAJA_CONSUMER_SECRET}"
    encoded = base64.b64encode(credentials.encode()).decode()

    headers = {"Authorization": f"Basic {encoded}"}

    response = requests.get(url, headers=headers, timeout=30)

    if response.status_code != 200:
        logger.error("Daraja auth failed: %s - %s", response.status_code, response.text)
        raise DarajaAPIError(f"Failed to get access token: {response.status_code} - {response.text}")

    data = response.json()
    token = data.get("access_token")
    if not token:
        raise DarajaAPIError(f"No access_token in Daraja response: {data}")

    return token


def send_b2c_payout(
    *,
    amount: int,
    phone_number: str,
    remarks: str,
    occasion: str = "",
    command_id: str = "BusinessPayment",
) -> dict:
    """
    Trigger a B2C bulk payout via Daraja.

    Args:
        amount: Amount in KES (whole number, as required by Daraja).
        phone_number: Recipient's phone number in format 2547XXXXXXXX.
        remarks: Short description of the payment (shown to Safaricom, not the farmer).
        occasion: Optional additional context string.
        command_id: One of "SalaryPayment", "BusinessPayment", "PromotionPayment".
            BusinessPayment is the standard choice for cooperative payouts.

    Returns:
        The parsed JSON response from Daraja (contains ConversationID etc.)
        Note: this is just the *request acknowledgement* — the actual payout
        result arrives later via the callback URL, which must be handled
        separately (see integrations/views.py).
    """
    _require_credentials()

    required_settings = {
        'DARAJA_SHORTCODE': settings.DARAJA_SHORTCODE,
        'DARAJA_INITIATOR_NAME': settings.DARAJA_INITIATOR_NAME,
        'DARAJA_SECURITY_CREDENTIAL': settings.DARAJA_SECURITY_CREDENTIAL,
        'DARAJA_B2C_CALLBACK_URL': settings.DARAJA_B2C_CALLBACK_URL,
        'DARAJA_B2C_TIMEOUT_URL': settings.DARAJA_B2C_TIMEOUT_URL,
    }
    missing = [name for name, value in required_settings.items() if not value]
    if missing:
        raise DarajaConfigError(
            f"Missing required Daraja B2C settings: {', '.join(missing)}. "
            f"Add these to your .env file."
        )

    token = get_access_token()
    url = f"{settings.DARAJA_BASE_URL}/mpesa/b2c/v1/paymentrequest"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    payload = {
        "InitiatorName": settings.DARAJA_INITIATOR_NAME,
        "SecurityCredential": settings.DARAJA_SECURITY_CREDENTIAL,
        "CommandID": command_id,
        "Amount": amount,
        "PartyA": settings.DARAJA_SHORTCODE,
        "PartyB": phone_number,
        "Remarks": remarks,
        "QueueTimeOutURL": settings.DARAJA_B2C_TIMEOUT_URL,
        "ResultURL": settings.DARAJA_B2C_CALLBACK_URL,
        "Occasion": occasion,
    }

    response = requests.post(url, json=payload, headers=headers, timeout=30)

    if response.status_code != 200:
        logger.error("Daraja B2C request failed: %s - %s", response.status_code, response.text)
        raise DarajaAPIError(f"B2C request failed: {response.status_code} - {response.text}")

    return response.json()