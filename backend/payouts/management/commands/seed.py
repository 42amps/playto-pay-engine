from django.core.management.base import BaseCommand
from payouts.models import Merchant, LedgerEntry


class Command(BaseCommand):
    help = "Seed the database with test merchants and credit history"

    def handle(self, *args, **options):
        merchants_data = [
            {
                "name": "Acme Agency",
                "email": "acme@example.com",
                "api_key": "api-key-acme-agency",
                "balance_paise": 1_000_000,  # ₹10,000
            },
            {
                "name": "Freelancer Fiaz",
                "email": "fiaz@example.com",
                "api_key": "api-key-freelancer-fiaz",
                "balance_paise": 500_000,  # ₹5,000
            },
            {
                "name": "Tiny Studio",
                "email": "tiny@example.com",
                "api_key": "api-key-tiny-studio",
                "balance_paise": 10_000,  # ₹100
            },
        ]

        for data in merchants_data:
            merchant, created = Merchant.objects.get_or_create(
                email=data["email"],
                defaults={
                    "name": data["name"],
                    "api_key": data["api_key"],
                },
            )
            if created:
                LedgerEntry.objects.create(
                    merchant=merchant,
                    amount_paise=data["balance_paise"],
                    entry_type=LedgerEntry.CREDIT,
                    description="Initial seed credit",
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created merchant {merchant.name} with balance ₹{data['balance_paise'] / 100:.2f}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"Merchant {merchant.name} already exists, skipping")
                )
