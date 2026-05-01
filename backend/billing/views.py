from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import BillingPermission, BillingTransactionPermission
from audit.services import audit_state_change

from .models import BillingTransaction, Invoice
from .serializers import BillingTransactionSerializer, InvoiceSerializer
from .services import process_payment_stub


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.select_related("patient", "patient__user", "appointment", "created_by").all()
    serializer_class = InvoiceSerializer
    permission_classes = [BillingPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == "patient":
            return queryset.filter(patient__user=self.request.user)
        return queryset

    def perform_create(self, serializer):
        with transaction.atomic():
            invoice = serializer.save(created_by=self.request.user)
            audit_state_change(self.request, actor=self.request.user, action="invoice.create", instance=invoice)

    def perform_update(self, serializer):
        with transaction.atomic():
            invoice = serializer.save()
            audit_state_change(self.request, actor=self.request.user, action="invoice.update", instance=invoice)

    def perform_destroy(self, instance):
        resource_id = str(instance.pk)
        with transaction.atomic():
            instance.delete()
            audit_state_change(self.request, actor=self.request.user, action="invoice.delete", resource_type="Invoice", resource_id=resource_id)

    @action(detail=True, methods=["post"])
    def charge(self, request, pk=None):
        invoice = self.get_object()
        amount = invoice.amount_due
        with transaction.atomic():
            gateway_payload = process_payment_stub(invoice, amount)
            transaction_record = BillingTransaction.objects.create(
                invoice=invoice,
                initiated_by=request.user,
                amount=amount,
                status=BillingTransaction.Status.SUCCEEDED if gateway_payload["accepted"] else BillingTransaction.Status.FAILED,
                gateway_reference=gateway_payload["gateway_reference"],
                gateway_payload=gateway_payload,
            )
            invoice.status = Invoice.Status.PAID if gateway_payload["accepted"] else Invoice.Status.FAILED
            invoice.paid_at = timezone.now() if gateway_payload["accepted"] else None
            invoice.external_reference = gateway_payload["gateway_reference"]
            invoice.last_gateway_payload = gateway_payload
            invoice.save(update_fields=["status", "paid_at", "external_reference", "last_gateway_payload"])
            audit_state_change(request, actor=request.user, action="invoice.charge", instance=invoice, metadata={"transaction_id": transaction_record.pk})
        return Response(
            {
                "invoice": self.get_serializer(invoice).data,
                "transaction": BillingTransactionSerializer(transaction_record).data,
            },
            status=status.HTTP_200_OK,
        )


class BillingTransactionViewSet(viewsets.ModelViewSet):
    queryset = BillingTransaction.objects.select_related("invoice", "initiated_by").all()
    serializer_class = BillingTransactionSerializer
    permission_classes = [BillingTransactionPermission]
    http_method_names = ["get", "post", "head", "options"]

    def perform_create(self, serializer):
        with transaction.atomic():
            transaction_row = serializer.save(initiated_by=self.request.user)
            audit_state_change(self.request, actor=self.request.user, action="billing_transaction.create", instance=transaction_row)
