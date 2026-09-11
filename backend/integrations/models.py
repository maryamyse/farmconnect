import uuid

from django.db import models


class PayoutAttempt(models.Model):
    """
    Tracks every attempted B2C payout for idempotency and reconciliation.

    A unique reference is generated per attempt so retries (e.g. from a
    Celery task retry) can check whether a payout already succeeded before
    firing another Daraja request — critical since double-paying a farmer
    is far worse than a delayed payment.
    """

    STATUS_PENDING = 'pending'
    STATUS_SENT = 'sent'          # Daraja acknowledged the request
    STATUS_SUCCESS = 'success'    # Confirmed via callback
    STATUS_FAILED = 'failed'      # Confirmed failure via callback
    STATUS_TIMEOUT = 'timeout'    # Daraja never called back

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_SENT, 'Sent to Daraja'),
        (STATUS_SUCCESS, 'Success'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_TIMEOUT, 'Timeout'),
    ]

    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    phone_number = models.CharField(max_length=20)
    amount = models.PositiveIntegerField()
    remarks = models.CharField(max_length=255, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    conversation_id = models.CharField(max_length=100, blank=True, null=True)
    originator_conversation_id = models.CharField(max_length=100, blank=True, null=True)

    daraja_response = models.JSONField(blank=True, null=True)
    callback_payload = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PayoutAttempt({self.reference}, {self.phone_number}, {self.amount}, {self.status})"


class SMSLog(models.Model):
    """Tracks every SMS sent, so retries can check whether one already went out."""

    STATUS_PENDING = 'pending'
    STATUS_SENT = 'sent'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_SENT, 'Sent'),
        (STATUS_FAILED, 'Failed'),
    ]

    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    phone_number = models.CharField(max_length=20)
    message = models.TextField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    provider_response = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"SMSLog({self.reference}, {self.phone_number}, {self.status})"