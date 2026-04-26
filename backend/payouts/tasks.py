import random
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django_q.tasks import async_task

from .models import Payout, LedgerEntry, Merchant

MAX_ATTEMPTS = 3
PROCESSING_TIMEOUT_SECONDS = 30


def process_payout(payout_id):
    """Main entry point called when a payout is created."""
    _process_payout_task(payout_id)


def _process_payout_task(payout_id):
    with transaction.atomic():
        try:
            payout = Payout.objects.select_for_update().get(
                id=payout_id, status=Payout.PENDING
            )
        except Payout.DoesNotExist:
            return

        payout.transition_to(Payout.PROCESSING)
        payout.attempts += 1
        payout.last_processed_at = timezone.now()
        payout.save(update_fields=["attempts", "last_processed_at"])

    # Simulate bank call (outside lock to not hold it)
    result = _simulate_bank_settlement()

    with transaction.atomic():
        payout = Payout.objects.select_for_update().get(id=payout_id)

        if payout.status != Payout.PROCESSING:
            return

        if result == "success":
            payout.transition_to(Payout.COMPLETED)
        elif result == "fail":
            _fail_payout_and_refund(payout)
        elif result == "hang":
            # Schedule retry if under max attempts
            if payout.attempts < MAX_ATTEMPTS:
                delay = PROCESSING_TIMEOUT_SECONDS * (2 ** (payout.attempts - 1))
                async_task(
                    "payouts.tasks._retry_payout",
                    payout_id,
                    schedule_type="O",
                    next_run=timezone.now() + timedelta(seconds=delay),
                )
            else:
                _fail_payout_and_refund(payout)


def _retry_payout(payout_id):
    """Retry a hung payout."""
    with transaction.atomic():
        try:
            payout = Payout.objects.select_for_update().get(
                id=payout_id, status=Payout.PROCESSING
            )
        except Payout.DoesNotExist:
            return

        # Check if stuck long enough
        if payout.last_processed_at:
            elapsed = (timezone.now() - payout.last_processed_at).total_seconds()
            expected_timeout = PROCESSING_TIMEOUT_SECONDS * (
                2 ** (payout.attempts - 1)
            )
            if elapsed < expected_timeout:
                return

        payout.attempts += 1
        payout.last_processed_at = timezone.now()
        payout.save(update_fields=["attempts", "last_processed_at"])

    # Retry bank call
    result = _simulate_bank_settlement()

    with transaction.atomic():
        payout = Payout.objects.select_for_update().get(id=payout_id)

        if payout.status != Payout.PROCESSING:
            return

        if result == "success":
            payout.transition_to(Payout.COMPLETED)
        elif result == "fail":
            _fail_payout_and_refund(payout)
        elif result == "hang":
            if payout.attempts < MAX_ATTEMPTS:
                delay = PROCESSING_TIMEOUT_SECONDS * (2 ** (payout.attempts - 1))
                async_task(
                    "payouts.tasks._retry_payout",
                    payout_id,
                    schedule_type="O",
                    next_run=timezone.now() + timedelta(seconds=delay),
                )
            else:
                _fail_payout_and_refund(payout)


def _fail_payout_and_refund(payout):
    """Atomically fail payout and return funds."""
    payout.transition_to(Payout.FAILED)
    LedgerEntry.objects.create(
        merchant=payout.merchant,
        amount_paise=payout.amount_paise,
        entry_type=LedgerEntry.CREDIT,
        payout=payout,
        description=f"Refund for failed payout to {payout.bank_account_id}",
    )


def _simulate_bank_settlement():
    """Simulate bank: 70% success, 20% fail, 10% hang."""
    roll = random.random()
    if roll < 0.7:
        return "success"
    elif roll < 0.9:
        return "fail"
    return "hang"
