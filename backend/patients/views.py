from django.db import transaction
from rest_framework import viewsets

from accounts.permissions import PatientPermission
from audit.services import audit_state_change

from .models import Patient
from .serializers import PatientSerializer


class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.select_related("user").all()
    serializer_class = PatientSerializer
    permission_classes = [PatientPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == "patient":
            return queryset.filter(user=self.request.user)
        return queryset

    def perform_create(self, serializer):
        with transaction.atomic():
            patient = serializer.save()
            audit_state_change(self.request, actor=self.request.user, action="patient.create", instance=patient)

    def perform_update(self, serializer):
        with transaction.atomic():
            patient = serializer.save()
            audit_state_change(self.request, actor=self.request.user, action="patient.update", instance=patient)

    def perform_destroy(self, instance):
        resource_id = str(instance.pk)
        with transaction.atomic():
            instance.delete()
            audit_state_change(self.request, actor=self.request.user, action="patient.delete", resource_type="Patient", resource_id=resource_id)
