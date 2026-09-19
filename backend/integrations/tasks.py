import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .daraja.client import (
    send_b2c_payout,
    query_transaction_status,
    DarajaAPIError,
    DarajaConfigError,
)
from .sms.client import send_sms, ATConfigError
from .models import PayoutAttempt, SMSLog

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_payout(self, payout_attempt_id: int):
    """
    Trigger a Daraja B2C payout for an existing PayoutAttempt record.

    Idempotency: if this PayoutAttempt is already SENT/SUCCESS, we don't
    fire another Daraja request — protects against duplicate payouts if
    the task gets retried or run twice for any reason.
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
        logger.error("Daraja config error for payout %s: %s", attempt.reference, exc)
        attempt.status = PayoutAttempt.STATUS_FAILED
        attempt.save()
        raise

    except DarajaAPIError as exc:
        logger.warning("Daraja API error for payout %s: %s — will retry", attempt.reference, exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def check_payout_status(self, payout_attempt_id: int):
    """
    Actively query Daraja for the status of a single PayoutAttempt that is
    still stuck in SENT status — a fallback for when the original B2C
    ResultURL callback was never received (a known sandbox issue).
    """
    try:
        attempt = PayoutAttempt.objects.get(id=payout_attempt_id)
    except PayoutAttempt.DoesNotExist:
        logger.error("PayoutAttempt %s not found", payout_attempt_id)
        return

    if attempt.status != PayoutAttempt.STATUS_SENT:
        logger.info(
            "PayoutAttempt %s is %s, not SENT — skipping status check",
            attempt.reference, attempt.status
        )
        return

    if not attempt.originator_conversation_id:
        logger.warning(
            "PayoutAttempt %s has no OriginatorConversationID — cannot query status",
            attempt.reference
        )
        return

    try:
        response = query_transaction_status(
            originator_conversation_id=attempt.originator_conversation_id,
            remarks=f"Status check for payout {attempt.reference}",
        )
        logger.info(
            "Transaction status query acknowledged for payout %s: %s",
            attempt.reference, response
        )
    except (DarajaAPIError, DarajaConfigError) as exc:
        logger.warning(
            "Transaction status query failed for payout %s: %s", attempt.reference, exc
        )
        raise self.retry(exc=exc)


@shared_task
def check_stale_payouts(older_than_minutes: int = 10):
    """
    Periodic task: finds all PayoutAttempts still stuck in SENT status
    older than the given threshold, and queues a status check for each —
    staggered several seconds apart rather than all at once, since firing
    many Daraja API calls (each needing a token) in a tight burst can
    trigger Safaricom's WAF (Incapsula) to start blocking requests.
    """
    cutoff = timezone.now() - timedelta(minutes=older_than_minutes)
    stale = PayoutAttempt.objects.filter(
        status=PayoutAttempt.STATUS_SENT,
        created_at__lt=cutoff,
    )

    count = 0
    for i, attempt in enumerate(stale):
        # Space checks 20 seconds apart so we don't burst Daraja's auth
        # endpoint with many simultaneous requests.
        check_payout_status.apply_async(args=[attempt.id], countdown=i * 20)
        count += 1

    logger.info("Queued %d staggered status check(s)", count)
    return count


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_sms_notification(self, sms_log_id: int):
    """
    Send an SMS for an existing SMSLog record.

    Idempotency: if already SENT, skip — protects against a farmer
    receiving the same confirmation SMS multiple times on retry.
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