from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from accounts.permissions import AppointmentPermission
from audit.services import audit_state_change

from .models import Appointment
from .serializers import AppointmentSerializer


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.select_related("patient", "patient__user", "clinician", "created_by", "last_updated_by").all()
    serializer_class = AppointmentSerializer
    permission_classes = [AppointmentPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == "patient":
            return queryset.filter(patient__user=self.request.user)
        return queryset

    def perform_create(self, serializer):
        patient = serializer.validated_data["patient"]
        if self.request.user.role == "patient" and patient.user_id != self.request.user.id:
            raise PermissionDenied("Patients can only create their own appointments.")
        with transaction.atomic():
            appointment = serializer.save(created_by=self.request.user, last_updated_by=self.request.user)
            audit_state_change(self.request, actor=self.request.user, action="appointment.create", instance=appointment)

    def perform_update(self, serializer):
        with transaction.atomic():
            appointment = serializer.save(last_updated_by=self.request.user)
            audit_state_change(self.request, actor=self.request.user, action="appointment.update", instance=appointment)

    def perform_destroy(self, instance):
        resource_id = str(instance.pk)
        with transaction.atomic():
            instance.delete()
            audit_state_change(self.request, actor=self.request.user, action="appointment.delete", resource_type="Appointment", resource_id=resource_id)

    @action(detail=True, methods=["post"])
    def set_status(self, request, pk=None):
        appointment = self.get_object()
        new_status = request.data.get("status")
        if new_status not in Appointment.Status.values:
            return Response({"detail": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST)
        appointment.status = new_status
        appointment.last_updated_by = request.user
        appointment.save(update_fields=["status", "last_updated_by", "updated_at"])
        audit_state_change(request, actor=request.user, action="appointment.set_status", instance=appointment)
        return Response(self.get_serializer(appointment).data)
