from rest_framework import serializers
from .models import LedgerEntry, Payout


class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = ["id", "amount_paise", "entry_type", "description", "created_at"]


class PayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payout
        fields = [
            "id",
            "amount_paise",
            "bank_account_id",
            "status",
            "attempts",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "attempts", "created_at", "updated_at"]


class PayoutCreateSerializer(serializers.Serializer):
    amount_paise = serializers.IntegerField(min_value=1)
    bank_account_id = serializers.CharField(max_length=255)
