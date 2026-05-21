import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest import skipIf

from django.db import connection
from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from .models import Merchant, LedgerEntry, Payout, IdempotencyKey


class ConcurrencyTest(TransactionTestCase):
    """Test that two simultaneous payouts cannot overdraw a balance.
    
    NOTE: This test requires PostgreSQL to verify select_for_update behavior.
    On SQLite, concurrent writes may result in database lock errors instead of
    clean 400 responses. The production system uses PostgreSQL where this works correctly.
    """

    def setUp(self):
        self.merchant = Merchant.objects.create(
            name="Test Merchant",
            email="test@example.com",
            api_key="test-api-key-concurrency",
        )
        # Seed with exactly 100 rupees (10000 paise)
        LedgerEntry.objects.create(
            merchant=self.merchant,
            amount_paise=10000,
            entry_type=LedgerEntry.CREDIT,
            description="Initial credit",
        )
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION="Api-Key test-api-key-concurrency")

    @skipIf(
        connection.vendor == "sqlite",
        "SQLite does not provide the row-level locking semantics required for this concurrency regression.",
    )
    def test_concurrent_payouts_prevent_overdraft(self):
        """Two simultaneous 60-rupee payouts against 100-rupee balance:
        exactly one succeeds, the other is rejected cleanly."""
        url = reverse("payout-list-create")
        payload = {
            "amount_paise": 6000,
            "bank_account_id": "acc-123",
        }

        responses = []
        errors = []

        def make_request():
            try:
                key = str(uuid.uuid4())
                resp = self.client.post(
                    url,
                    payload,
                    format="json",
                    HTTP_IDEMPOTENCY_KEY=key,
                )
                return resp.status_code
            except Exception as e:
                errors.append(str(e))
                return None

        # Fire two concurrent requests
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(make_request) for _ in range(2)]
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    responses.append(result)

        # PostgreSQL: exactly one 201 and one 400
        self.assertEqual(sorted(responses), [201, 400], f"Got responses: {responses}, errors: {errors}")

        # Assert at most one payout was created (never overdraw)
        self.assertLessEqual(
            Payout.objects.filter(merchant=self.merchant).count(),
            1,
        )

        # Assert exactly one debit ledger entry (plus the initial credit)
        self.assertEqual(
            LedgerEntry.objects.filter(merchant=self.merchant, entry_type=LedgerEntry.DEBIT).count(),
            1,
        )

        # Assert balance invariant: credits - debits = displayed balance
        balance = Merchant.get_balance(self.merchant.id)
        self.assertEqual(balance, 4000)  # 10000 - 6000 = 4000


class IdempotencyTest(TransactionTestCase):
    """Test that duplicate requests with the same idempotency key return the same response."""

    def setUp(self):
        self.merchant = Merchant.objects.create(
            name="Test Merchant",
            email="test2@example.com",
            api_key="test-api-key-idempotency",
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            amount_paise=50000,
            entry_type=LedgerEntry.CREDIT,
            description="Initial credit",
        )
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION="Api-Key test-api-key-idempotency")
        self.idempotency_key = str(uuid.uuid4())

    def test_duplicate_idempotency_key_returns_same_response(self):
        """Two requests with the same key must return identical responses and create only one payout."""
        url = reverse("payout-list-create")
        payload = {
            "amount_paise": 10000,
            "bank_account_id": "acc-456",
        }

        # First request
        resp1 = self.client.post(
            url,
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY=self.idempotency_key,
        )
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)
        payout_id_1 = resp1.data["id"]

        # Second request with same key
        resp2 = self.client.post(
            url,
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY=self.idempotency_key,
        )
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        payout_id_2 = resp2.data["id"]

        # Same payout ID returned
        self.assertEqual(payout_id_1, payout_id_2)

        # Exactly one payout in DB
        self.assertEqual(Payout.objects.filter(merchant=self.merchant).count(), 1)

        # Exactly one idempotency key record
        self.assertEqual(
            IdempotencyKey.objects.filter(
                merchant=self.merchant, key=self.idempotency_key
            ).count(),
            1,
        )
