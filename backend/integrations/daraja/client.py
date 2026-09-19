"""
Daraja API client — handles OAuth token retrieval, B2C bulk payout requests,
and transaction status queries.

Safaricom Daraja docs: https://developer.safaricom.co.ke/
"""
import base64
import logging
import uuid

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

_TOKEN_CACHE_KEY = "daraja_access_token"
# Daraja tokens last ~3600s; cache for slightly less to avoid using an
# about-to-expire token, and to stay well clear of Safaricom's rate limits
# by not requesting a fresh token on every single API call.
_TOKEN_CACHE_TTL = 3500


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


def get_access_token(force_refresh: bool = False) -> str:
    """
    Fetch an OAuth access token from Daraja using Consumer Key/Secret.

    Cached for ~58 minutes to avoid hammering Daraja's auth endpoint on
    every call — Safaricom's sandbox (and likely production) rate-limits
    or blocks (via Incapsula WAF) clients that request tokens too
    frequently in a short window, which happens easily if many tasks
    each independently call this without caching.

    Args:
        force_refresh: bypass the cache and fetch a new token anyway
            (e.g. if a call failed with an auth error, the cached token
            might have been revoked or is otherwise bad).
    """
    if not force_refresh:
        cached = cache.get(_TOKEN_CACHE_KEY)
        if cached:
            return cached

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

    cache.set(_TOKEN_CACHE_KEY, token, _TOKEN_CACHE_TTL)
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

    Returns:
        The parsed JSON acknowledgement response from Daraja (contains
        ConversationID etc.) — the actual payout result arrives later via
        the callback URL, handled separately (see integrations/views.py).
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
    url = f"{settings.DARAJA_BASE_URL}/mpesa/b2c/v3/paymentrequest"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    originator_conversation_id = f"farmconnect_{uuid.uuid4()}"

    payload = {
        "OriginatorConversationID": originator_conversation_id,
        "InitiatorName": settings.DARAJA_INITIATOR_NAME,
        "SecurityCredential": settings.DARAJA_SECURITY_CREDENTIAL,
        "CommandID": command_id,
        "Amount": amount,
        "PartyA": settings.DARAJA_SHORTCODE,
        "PartyB": phone_number,
        "Remarks": remarks,
        "QueueTimeOutURL": settings.DARAJA_B2C_TIMEOUT_URL,
        "ResultURL": settings.DARAJA_B2C_CALLBACK_URL,
        "Occassion": occasion,  # Safaricom's v3 docs misspell this "Occassion" — must match exactly.
    }

    response = requests.post(url, json=payload, headers=headers, timeout=30)

    if response.status_code != 200:
        logger.error("Daraja B2C request failed: %s - %s", response.status_code, response.text)
        raise DarajaAPIError(f"B2C request failed: {response.status_code} - {response.text}")

    return response.json()


def query_transaction_status(
    *,
    transaction_id: str = "",
    originator_conversation_id: str = "",
    remarks: str = "Transaction status query",
    occasion: str = "",
) -> dict:
    """
    Query Daraja for the status of a previously-submitted transaction.

    Fallback/reconciliation mechanism for when a B2C ResultURL callback
    was not received. Also asynchronous — Daraja acknowledges immediately,
    then sends the actual status via ResultURL (see integrations/views.py).
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
            f"Missing required Daraja settings: {', '.join(missing)}. "
            f"Add these to your .env file."
        )

    if not transaction_id and not originator_conversation_id:
        raise ValueError(
            "Must provide either transaction_id or originator_conversation_id."
        )

    token = get_access_token()
    url = f"{settings.DARAJA_BASE_URL}/mpesa/transactionstatus/v1/query"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    payload = {
        "Initiator": settings.DARAJA_INITIATOR_NAME,
        "SecurityCredential": settings.DARAJA_SECURITY_CREDENTIAL,
        "CommandID": "TransactionStatusQuery",
        "TransactionID": transaction_id,
        "OriginatorConversationID": originator_conversation_id,
        "PartyA": settings.DARAJA_SHORTCODE,
        "IdentifierType": "4",
        "ResultURL": settings.DARAJA_B2C_CALLBACK_URL,
        "QueueTimeOutURL": settings.DARAJA_B2C_TIMEOUT_URL,
        "Remarks": remarks,
        "Occasion": occasion,
    }

    response = requests.post(url, json=payload, headers=headers, timeout=30)

    if response.status_code != 200:
        logger.error("Transaction status query failed: %s - %s", response.status_code, response.text)
        raise DarajaAPIError(f"Transaction status query failed: {response.status_code} - {response.text}")

    return response.json()