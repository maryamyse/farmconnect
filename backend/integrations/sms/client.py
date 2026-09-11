"""
Africa's Talking SMS client — sends delivery/payout confirmation SMS to farmers.

Africa's Talking docs: https://developers.africastalking.com/
"""
import logging

import africastalking
from django.conf import settings

logger = logging.getLogger(__name__)

_initialized = False


class ATConfigError(Exception):
    """Raised when required Africa's Talking settings are missing."""
    pass


def _ensure_initialized():
    global _initialized
    if _initialized:
        return

    if not settings.AT_API_KEY:
        raise ATConfigError(
            "Missing AT_API_KEY. Add it to your .env file."
        )

    africastalking.initialize(settings.AT_USERNAME, settings.AT_API_KEY)
    _initialized = True


def send_sms(phone_number: str, message: str) -> dict:
    """
    Send an SMS to a single recipient.

    Args:
        phone_number: Recipient's phone number in format +2547XXXXXXXX.
        message: The SMS body text.

    Returns:
        The raw response dict from Africa's Talking, including per-recipient
        delivery status. Inspect response['SMSMessageData']['Recipients']
        for status per number.
    """
    _ensure_initialized()

    sms = africastalking.SMS
    response = sms.send(message, [phone_number])

    logger.info("AT SMS response for %s: %s", phone_number, response)
    return response