from rest_framework import serializers

from .models import BillingTransaction, Invoice


class InvoiceSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        appointment = validated_data.get("appointment")
        if appointment is None:
            raise serializers.ValidationError({"appointment": "This field is required."})
        validated_data["amount_due"] = appointment.billable_amount
        return super().create(validated_data)

    class Meta:
        model = Invoice
        fields = "__all__"
        read_only_fields = ("amount_due", "issued_at", "paid_at", "created_by")


class BillingTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingTransaction
        fields = "__all__"
        read_only_fields = ("initiated_by", "created_at")
