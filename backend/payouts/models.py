import uuid
import json
from decimal import Decimal

from django.db import models, transaction
from django.db.models import Sum, Case, When, Value, F, Q
from django.utils import timezone


class Merchant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    api_key = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Authentication interface for DRF
    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_staff(self):
        return False

    @property
    def is_superuser(self):
        return False

    def __str__(self):
        return self.name

    @classmethod
    def get_balance(cls, merchant_id):
        """Database-level balance calculation."""
        result = LedgerEntry.objects.filter(merchant_id=merchant_id).aggregate(
            balance=Sum(
                Case(
                    When(entry_type=LedgerEntry.CREDIT, then=F("amount_paise")),
                    When(entry_type=LedgerEntry.DEBIT, then=-F("amount_paise")),
                    default=Value(0),
                    output_field=models.BigIntegerField(),
                )
            )
        )
        return result["balance"] or 0

    @classmethod
    def get_held_balance(cls, merchant_id):
        """Sum of payouts in pending or processing state."""
        result = Payout.objects.filter(
            merchant_id=merchant_id,
            status__in=[Payout.PENDING, Payout.PROCESSING],
        ).aggregate(total=Sum("amount_paise"))
        return result["total"] or 0


class LedgerEntry(models.Model):
    CREDIT = "credit"
    DEBIT = "debit"
    ENTRY_TYPES = [(CREDIT, "Credit"), (DEBIT, "Debit")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        Merchant, on_delete=models.CASCADE, related_name="ledger_entries"
    )
    amount_paise = models.BigIntegerField()
    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPES)
    payout = models.ForeignKey(
        "Payout",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_entries",
    )
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]


class Payout(models.Model):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (PROCESSING, "Processing"),
        (COMPLETED, "Completed"),
        (FAILED, "Failed"),
    ]

    VALID_TRANSITIONS = {
        PENDING: [PROCESSING],
        PROCESSING: [COMPLETED, FAILED],
        COMPLETED: [],
        FAILED: [],
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        Merchant, on_delete=models.CASCADE, related_name="payouts"
    )
    amount_paise = models.BigIntegerField()
    bank_account_id = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=PENDING, db_index=True
    )
    attempts = models.PositiveIntegerField(default=0)
    last_processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def transition_to(self, new_status):
        """Atomically validate and transition state."""
        if new_status not in self.VALID_TRANSITIONS.get(self.status, []):
            raise ValueError(
                f"Invalid transition: {self.status} -> {new_status}"
            )
        self.status = new_status
        self.save(update_fields=["status", "updated_at"])


class IdempotencyKey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        Merchant, on_delete=models.CASCADE, related_name="idempotency_keys"
    )
    key = models.UUIDField()
    response_status = models.PositiveIntegerField()
    response_body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("merchant", "key")]
        indexes = [
            models.Index(fields=["merchant", "key"]),
            models.Index(fields=["created_at"]),
        ]
