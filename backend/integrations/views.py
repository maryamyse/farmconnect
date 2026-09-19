import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import PayoutAttempt

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])  # Daraja can't authenticate like a normal user — see note below
def daraja_b2c_callback(request):
    """
    Receives the async result of a B2C payout from Daraja.

    NOTE ON SECURITY: Daraja does not sign or authenticate its callbacks in
    a way Django can easily verify out of the box. In production, consider
    restricting this endpoint by IP allowlist (Safaricom publishes their
    callback IP ranges) rather than leaving it fully open. For sandbox
    testing this is acceptable as-is.
    """
    payload = request.data
    logger.info("Received Daraja B2C callback: %s", payload)

    result = payload.get("Result", {})
    conversation_id = result.get("ConversationID")
    result_code = result.get("ResultCode")

    if not conversation_id:
        logger.warning("Daraja callback missing ConversationID: %s", payload)
        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

    try:
        attempt = PayoutAttempt.objects.get(conversation_id=conversation_id)
    except PayoutAttempt.DoesNotExist:
        logger.error("No PayoutAttempt found for ConversationID %s", conversation_id)
        # Still return success to Daraja — they don't need to know about our data issue.
        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

    attempt.callback_payload = payload
    attempt.status = (
        PayoutAttempt.STATUS_SUCCESS if result_code == 0 else PayoutAttempt.STATUS_FAILED
    )
    attempt.save()

    logger.info("PayoutAttempt %s updated to %s", attempt.reference, attempt.status)

    # Daraja expects this exact acknowledgement shape.
    return Response({"ResultCode": 0, "ResultDesc": "Accepted"})


@api_view(['POST'])
@permission_classes([AllowAny])
def daraja_b2c_timeout(request):
    """Receives timeout notifications if Daraja couldn't complete the request in time."""
    payload = request.data
    logger.warning("Received Daraja B2C timeout callback: %s", payload)
    return Response({"ResultCode": 0, "ResultDesc": "Accepted"})


@api_view(['POST'])
@permission_classes([AllowAny])
def daraja_transaction_status_callback(request):
    """
    Receives the async result of a Transaction Status Query.

    Matched to the original PayoutAttempt via OriginatorConversationID
    (the query reuses the same one as the original B2C request), since
    ConversationID differs between the original request and the status
    query itself.
    """
    payload = request.data
    logger.info("Received Daraja transaction status callback: %s", payload)

    result = payload.get("Result", {})
    originator_conversation_id = result.get("OriginatorConversationID")
    result_code = result.get("ResultCode")

    if not originator_conversation_id:
        logger.warning("Status callback missing OriginatorConversationID: %s", payload)
        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

    try:
        attempt = PayoutAttempt.objects.get(
            originator_conversation_id=originator_conversation_id
        )
    except PayoutAttempt.DoesNotExist:
        logger.error(
            "No PayoutAttempt found for OriginatorConversationID %s",
            originator_conversation_id
        )
        return Response({"ResultCode": 0, "ResultDesc": "Accepted"})

    attempt.callback_payload = payload
    attempt.status = (
        PayoutAttempt.STATUS_SUCCESS if result_code == 0 else PayoutAttempt.STATUS_FAILED
    )
    attempt.save()

    logger.info(
        "PayoutAttempt %s updated to %s via status query", attempt.reference, attempt.status
    )

    return Response({"ResultCode": 0, "ResultDesc": "Accepted"})