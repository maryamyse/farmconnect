import logging

from celery import shared_task

from .daraja.client import send_b2c_payout, DarajaAPIError, DarajaConfigError
from .sms.client import send_sms, ATConfigError
from .models import PayoutAttempt, SMSLog

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_payout(self, payout_attempt_id: int):
    """
    Trigger a Daraja B2C payout for an existing PayoutAttempt record.

    Idempotency: if this PayoutAttempt is already SENT/SUCCESS, we don't
    fire another Daraja request — this protects against duplicate payouts
    if the task gets retried or run twice for any reason.
    """
    try:
        attempt = PayoutAttempt.objects.get(id=payout_attempt_id)
    except PayoutAttempt.DoesNotExist:
        logger.error("PayoutAttempt %s not found", payout_attempt_id)
        return

    if attempt.status in (PayoutAttempt.STATUS_SENT, PayoutAttempt.STATUS_SUCCESS):
        logger.info(
            "PayoutAttempt %s already %s — skipping duplicate send",
            attempt.reference, attempt.status
        )
        return

    try:
        response = send_b2c_payout(
            amount=attempt.amount,
            phone_number=attempt.phone_number,
            remarks=attempt.remarks or f"Payout {attempt.reference}",
        )
        attempt.daraja_response = response
        attempt.conversation_id = response.get("ConversationID")
        attempt.originator_conversation_id = response.get("OriginatorConversationID")
        attempt.status = PayoutAttempt.STATUS_SENT
        attempt.save()
        logger.info("Payout %s sent to Daraja: %s", attempt.reference, response)

    except DarajaConfigError as exc:
        # Config errors won't fix themselves on retry — fail loudly, don't retry.
        logger.error("Daraja config error for payout %s: %s", attempt.reference, exc)
        attempt.status = PayoutAttempt.STATUS_FAILED
        attempt.save()
        raise

    except DarajaAPIError as exc:
        logger.warning("Daraja API error for payout %s: %s — will retry", attempt.reference, exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_sms_notification(self, sms_log_id: int):
    """
    Send an SMS for an existing SMSLog record.

    Idempotency: if this SMSLog is already SENT, skip — protects against
    a farmer receiving the same confirmation SMS multiple times on retry.
    """
    try:
        sms_log = SMSLog.objects.get(id=sms_log_id)
    except SMSLog.DoesNotExist:
        logger.error("SMSLog %s not found", sms_log_id)
        return

    if sms_log.status == SMSLog.STATUS_SENT:
        logger.info("SMSLog %s already sent — skipping duplicate send", sms_log.reference)
        return

    try:
        response = send_sms(sms_log.phone_number, sms_log.message)
        sms_log.provider_response = response
        sms_log.status = SMSLog.STATUS_SENT
        sms_log.save()
        logger.info("SMS %s sent: %s", sms_log.reference, response)

    except ATConfigError as exc:
        logger.error("Africa's Talking config error for SMS %s: %s", sms_log.reference, exc)
        sms_log.status = SMSLog.STATUS_FAILED
        sms_log.save()
        raise

    except Exception as exc:
        logger.warning("SMS send failed for %s: %s — will retry", sms_log.reference, exc)
        sms_log.status = SMSLog.STATUS_FAILED
        sms_log.save()
        raise self.retry(exc=exc)