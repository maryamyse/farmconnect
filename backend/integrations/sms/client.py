"""
Africa's Talking SMS client - sends delivery/payout confirmation SMS to farmers.

Uses the stdlib http.client instead of requests/urllib3 or the africastalking
SDK. Both of the latter fail with SSL: WRONG_VERSION_NUMBER on this network -
traced to urllib3's connection-pooling layer specifically (confirmed via raw
socket/ssl tests succeeding while identical urllib3-based calls failed).
http.client uses the same working code path as those raw tests.

Africa's Talking docs: https://developers.africastalking.com/
"""
import http.client
import json
import logging
import ssl
from urllib.parse import urlencode

from django.conf import settings

logger = logging.getLogger(__name__)


class ATConfigError(Exception):
    """Raised when required Africa's Talking settings are missing."""
    pass


class ATRequestError(Exception):
    """Raised when Africa's Talking returns a non-success response."""
    pass


def _at_host():
    return "api.sandbox.africastalking.com" if getattr(settings, "AT_USERNAME", "sandbox") == "sandbox" \
        else "api.africastalking.com"


def _ensure_configured():
    if not settings.AT_API_KEY:
        raise ATConfigError(
            "Missing AT_API_KEY. Add it to your .env file."
        )


def send_sms(phone_number: str, message: str, sender_id: str | None = None) -> dict:
    """
    Send an SMS to a single recipient.

    Args:
        phone_number: Recipient's phone number in format +2547XXXXXXXX.
        message: The SMS body text.
        sender_id: Optional registered short/alphanumeric sender ID.

    Returns:
        The parsed JSON response dict from Africa's Talking, including
        per-recipient delivery status. Inspect
        response['SMSMessageData']['Recipients'] for status per number.

    Raises:
        ATConfigError: if AT_API_KEY is not configured.
        ATRequestError: if Africa's Talking returns a non-2xx response.
    """
    _ensure_configured()

    payload = {
        "username": settings.AT_USERNAME,
        "to": phone_number,
        "message": message,
    }
    if sender_id:
        payload["from"] = sender_id

    headers = {
        "apiKey": settings.AT_API_KEY,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }

    ctx = ssl.create_default_context()
    conn = http.client.HTTPSConnection(_at_host(), 443, context=ctx, timeout=15)
    try:
        conn.request("POST", "/version1/messaging", body=urlencode(payload), headers=headers)
        resp = conn.getresponse()
        raw = resp.read()
    finally:
        conn.close()

    try:
        data = json.loads(raw.decode()) if raw else {}
    except json.JSONDecodeError:
        data = {"raw": raw.decode(errors="replace")}

    logger.info("AT SMS response for %s: %s %s %s", phone_number, resp.status, resp.reason, data)

    if resp.status >= 400:
        raise ATRequestError(f"Africa's Talking returned {resp.status} {resp.reason}: {data}")

    return data