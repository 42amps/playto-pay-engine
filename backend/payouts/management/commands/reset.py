from django.core.management.base import BaseCommand
from payouts.models import Merchant, LedgerEntry, Payout, IdempotencyKey


class Command(BaseCommand):
    help = "Reset all transaction data and restore initial merchant balances"

    def handle(self, *args, **options):
        # Delete all transaction history
        IdempotencyKey.objects.all().delete()
        Payout.objects.all().delete()
        LedgerEntry.objects.all().delete()

        # Re-create initial credits for each merchant
        merchants_data = [
            {
                "email": "acme@example.com",
                "balance_paise": 1_000_000,
            },
            {
                "email": "fiaz@example.com",
                "balance_paise": 500_000,
            },
            {
                "email": "tiny@example.com",
                "balance_paise": 10_000,
            },
        ]

        for data in merchants_data:
            merchant = Merchant.objects.get(email=data["email"])
            LedgerEntry.objects.create(
                merchant=merchant,
                amount_paise=data["balance_paise"],
                entry_type=LedgerEntry.CREDIT,
                description="Initial seed credit",
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Reset {merchant.name} to ₹{data['balance_paise'] / 100:.2f}"
                )
            )
