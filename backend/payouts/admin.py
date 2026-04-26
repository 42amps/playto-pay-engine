from django.contrib import admin
from .models import Merchant, LedgerEntry, Payout, IdempotencyKey


@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "created_at"]
    search_fields = ["name", "email"]


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ["merchant", "amount_paise", "entry_type", "created_at"]
    list_filter = ["entry_type", "created_at"]


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ["merchant", "amount_paise", "status", "attempts", "created_at"]
    list_filter = ["status", "created_at"]


@admin.register(IdempotencyKey)
class IdempotencyKeyAdmin(admin.ModelAdmin):
    list_display = ["merchant", "key", "response_status", "created_at"]
