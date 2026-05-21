# PayRail - Real-Time Payout Engine Technical Explainer

![PayRail payout correctness flow](docs/assets/payrail-flow.svg)

## 1. The Ledger

**Balance calculation query (`payouts/models.py`):**

```python
@classmethod
def get_balance(cls, merchant_id):
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
```

**Why this model?**

I chose an append-only ledger over a mutable `balance` column because:

1. **Auditability:** Every rupee movement is a permanent, immutable row. If a bug ever corrupts a balance, the ledger is the source of truth we can reconcile against.
2. **Database-level correctness:** The `SUM(CASE ...))` runs entirely in PostgreSQL. No Python arithmetic on fetched rows means no race conditions on aggregation.
3. **Held funds are explicit:** When a payout is requested, we immediately write a `debit` ledger entry. The merchant's "available" balance drops instantly. If the payout later fails, we write a reversing `credit`. This is clearer than a separate `held_balance` column that drifts.

## 2. The Lock

**Exact concurrency prevention code (`payouts/views.py`):**

```python
with transaction.atomic():
    # Lock merchant row to serialize concurrent requests
    locked_merchant = (
        Merchant.objects.select_for_update().get(pk=merchant.pk)
    )

    # Check balance using DB-level aggregation
    available_balance = Merchant.get_balance(locked_merchant.id)
    if available_balance < amount_paise:
        ...  # reject

    # Create payout and hold funds atomically
    payout = Payout.objects.create(...)
    LedgerEntry.objects.create(...)
```

**What database primitive does it rely on?**

`SELECT FOR UPDATE` on the `Merchant` row. This acquires a row-level lock in PostgreSQL and holds it for the duration of the transaction. The critical section — balance check, payout creation, and ledger insert — all happen inside this single transaction. If two requests for the same merchant arrive simultaneously, the second blocks until the first commits and releases the lock. Only then does the second request read the updated balance (which already includes the first payout's debit) and reject the overdraft.

**Why not optimistic locking?** Because pessimistic locking is simpler and correct for this workload. We expect payout creation to be fast; holding the lock for a single INSERT is acceptable.

## 3. The Idempotency

**How the system knows it has seen a key before:**

The `IdempotencyKey` table has a unique database constraint on `(merchant, key)`. Before processing a request, we query this table under the merchant lock:

```python
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
```

**What if the first request is in flight when the second arrives?**

The second request blocks on the same `SELECT FOR UPDATE` lock on the merchant row. This ordering is crucial: the idempotency check happens **after** acquiring the lock, not before. The second request cannot proceed to check the `IdempotencyKey` table until the first request commits. Once the first request commits, it has already inserted the `IdempotencyKey` row. The second request then reads that row and returns the stored response. No duplicate payout is ever created.

Keys expire after 24 hours via a cleanup query that runs under the same lock:

```python
cutoff = timezone.now() - timedelta(hours=IDEMPOTENCY_KEY_EXPIRY_HOURS)
IdempotencyKey.objects.filter(
    merchant=locked_merchant, created_at__lt=cutoff
).delete()
```

## 4. The State Machine

**Where `failed → completed` is blocked (`payouts/models.py`):**

```python
VALID_TRANSITIONS = {
    PENDING: [PROCESSING],
    PROCESSING: [COMPLETED, FAILED],
    COMPLETED: [],
    FAILED: [],
}

def transition_to(self, new_status):
    if new_status not in self.VALID_TRANSITIONS.get(self.status, []):
        raise ValueError(
            f"Invalid transition: {self.status} -> {new_status}"
        )
    self.status = new_status
    self.save(update_fields=["status", "updated_at"])
```

Because `FAILED` maps to an empty list `[]`, any attempt to call `transition_to(Payout.COMPLETED)` on a failed payout raises `ValueError`. `transition_to` is the only code path in the entire codebase that modifies `payout.status`, so there is no way to bypass this check.

**Fund return atomicity:** When a payout fails, `_fail_payout_and_refund` runs inside the same `transaction.atomic()` block as the state transition. The state change and the reversing credit are committed together or not at all.

## 5. The AI Audit

**What AI gave me (subtly wrong):**

AI initially suggested calculating the merchant balance like this:

```python
# AI-generated (WRONG)
credits = LedgerEntry.objects.filter(
    merchant=merchant, entry_type="credit"
).aggregate(total=Sum("amount_paise"))["total"] or 0

debits = LedgerEntry.objects.filter(
    merchant=merchant, entry_type="debit"
).aggregate(total=Sum("amount_paise"))["total"] or 0

balance = credits - debits
```

**What I caught:**

This runs **two separate aggregation queries** and then does Python subtraction. Between the two queries, another transaction could insert a new debit. The result would be a transiently incorrect (too high) balance, allowing an overdraft.

**What I replaced it with:**

```python
# Correct: single atomic aggregation
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
```

This computes the balance in **one SQL statement** using `SUM(CASE WHEN ...)`. PostgreSQL guarantees this is atomic and reads a consistent snapshot of the ledger. No Python arithmetic, no check-then-deduct race.
