from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import EHRPermission
from audit.services import audit_state_change

from .models import EHRRecord
from .serializers import EHRRecordSerializer
from .services import sync_ehr_record_stub


class EHRRecordViewSet(viewsets.ModelViewSet):
    queryset = EHRRecord.objects.select_related("patient", "patient__user", "appointment", "author").all()
    serializer_class = EHRRecordSerializer
    permission_classes = [EHRPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == "patient":
            return queryset.filter(patient__user=self.request.user)
        return queryset

    def perform_create(self, serializer):
        with transaction.atomic():
            record = serializer.save(author=self.request.user)
            audit_state_change(self.request, actor=self.request.user, action="ehr_record.create", instance=record)

    def perform_update(self, serializer):
        with transaction.atomic():
            record = serializer.save()
            audit_state_change(self.request, actor=self.request.user, action="ehr_record.update", instance=record)

    def perform_destroy(self, instance):
        resource_id = str(instance.pk)
        with transaction.atomic():
            instance.delete()
            audit_state_change(self.request, actor=self.request.user, action="ehr_record.delete", resource_type="EHRRecord", resource_id=resource_id)

    @action(detail=True, methods=["post"])
    def sync_record(self, request, pk=None):
        record = self.get_object()
        with transaction.atomic():
            payload = sync_ehr_record_stub(record)
            record.sync_status = EHRRecord.SyncStatus.SYNCED if payload["accepted"] else EHRRecord.SyncStatus.FAILED
            record.external_id = payload["external_id"]
            record.last_synced_at = timezone.now()
            record.payload = {**record.payload, "sync_result": payload}
            record.save(update_fields=["sync_status", "external_id", "last_synced_at", "payload", "updated_at"])
            audit_state_change(request, actor=request.user, action="ehr_record.sync", instance=record)
        return Response(self.get_serializer(record).data, status=status.HTTP_200_OK)
