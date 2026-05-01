from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets

from accounts.permissions import ClinicalPermission
from audit.services import audit_state_change

from .models import ClinicalNote
from .serializers import ClinicalNoteSerializer


class ClinicalNoteViewSet(viewsets.ModelViewSet):
    queryset = ClinicalNote.objects.select_related("patient", "patient__user", "appointment", "author").all()
    serializer_class = ClinicalNoteSerializer
    permission_classes = [ClinicalPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == "patient":
            return queryset.filter(patient__user=self.request.user)
        return queryset

    def perform_create(self, serializer):
        with transaction.atomic():
            note = serializer.save(author=self.request.user)
            if note.is_signed and note.signed_at is None:
                note.signed_at = timezone.now()
                note.save(update_fields=["signed_at"])
            audit_state_change(self.request, actor=self.request.user, action="clinical_note.create", instance=note)

    def perform_update(self, serializer):
        with transaction.atomic():
            note = serializer.save()
            if note.is_signed and note.signed_at is None:
                note.signed_at = timezone.now()
                note.save(update_fields=["signed_at"])
            audit_state_change(self.request, actor=self.request.user, action="clinical_note.update", instance=note)

    def perform_destroy(self, instance):
        resource_id = str(instance.pk)
        with transaction.atomic():
            instance.delete()
            audit_state_change(self.request, actor=self.request.user, action="clinical_note.delete", resource_type="ClinicalNote", resource_id=resource_id)
