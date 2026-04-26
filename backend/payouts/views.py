import uuid
import json
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django_q.tasks import async_task
from .models import Merchant, LedgerEntry, Payout, IdempotencyKey
from .serializers import (
    LedgerEntrySerializer,
    PayoutSerializer,
    PayoutCreateSerializer,
)

IDEMPOTENCY_KEY_EXPIRY_HOURS = 24


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    merchant = request.user
    available_balance = Merchant.get_balance(merchant.id)
    held_balance = Merchant.get_held_balance(merchant.id)
    return Response(
        {
            "id": str(merchant.id),
            "name": merchant.name,
            "email": merchant.email,
            "available_balance_paise": available_balance,
            "held_balance_paise": held_balance,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def ledger_list(request):
    merchant = request.user
    entries = LedgerEntry.objects.filter(merchant=merchant)[:50]
    serializer = LedgerEntrySerializer(entries, many=True)
    return Response(serializer.data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def payout_list_create(request):
    merchant = request.user

    if request.method == "GET":
        payouts = Payout.objects.filter(merchant=merchant)[:50]
        serializer = PayoutSerializer(payouts, many=True)
        return Response(serializer.data)

    # POST - create payout
    idempotency_key_str = request.headers.get("Idempotency-Key")
    if not idempotency_key_str:
        return Response(
            {"error": "Idempotency-Key header is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        idempotency_key_uuid = uuid.UUID(idempotency_key_str)
    except ValueError:
        return Response(
            {"error": "Idempotency-Key must be a valid UUID"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = PayoutCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    amount_paise = serializer.validated_data["amount_paise"]
    bank_account_id = serializer.validated_data["bank_account_id"]

    with transaction.atomic():
        # Lock merchant row to serialize concurrent requests
        locked_merchant = (
            Merchant.objects.select_for_update().get(pk=merchant.pk)
        )

        # Clean expired keys
        cutoff = timezone.now() - timedelta(hours=IDEMPOTENCY_KEY_EXPIRY_HOURS)
        IdempotencyKey.objects.filter(
            merchant=locked_merchant, created_at__lt=cutoff
        ).delete()

        # Check idempotency
        try:
            existing = IdempotencyKey.objects.get(
                merchant=locked_merchant, key=idempotency_key_uuid
            )
            return Response(
                json.loads(existing.response_body),
                status=existing.response_status,
            )
        except IdempotencyKey.DoesNotExist:
            pass

        # Check balance using DB-level aggregation
        available_balance = Merchant.get_balance(locked_merchant.id)
        if available_balance < amount_paise:
            error_response = {
                "error": "Insufficient balance",
                "available_balance_paise": available_balance,
            }
            IdempotencyKey.objects.create(
                merchant=locked_merchant,
                key=idempotency_key_uuid,
                response_status=status.HTTP_400_BAD_REQUEST,
                response_body=json.dumps(error_response),
            )
            return Response(error_response, status=status.HTTP_400_BAD_REQUEST)

        # Create payout and hold funds atomically
        payout = Payout.objects.create(
            merchant=locked_merchant,
            amount_paise=amount_paise,
            bank_account_id=bank_account_id,
            status=Payout.PENDING,
        )
        LedgerEntry.objects.create(
            merchant=locked_merchant,
            amount_paise=amount_paise,
            entry_type=LedgerEntry.DEBIT,
            payout=payout,
            description=f"Payout hold for {bank_account_id}",
        )

        response_data = PayoutSerializer(payout).data
        IdempotencyKey.objects.create(
            merchant=locked_merchant,
            key=idempotency_key_uuid,
            response_status=status.HTTP_201_CREATED,
            response_body=json.dumps(response_data),
        )

    # Queue background task outside transaction
    async_task("payouts.tasks.process_payout", payout.id)

    return Response(response_data, status=status.HTTP_201_CREATED)
