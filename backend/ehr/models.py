from django.conf import settings
from django.db import models

from appointments.models import Appointment
from patients.models import Patient


class EHRRecord(models.Model):
    class SyncStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SYNCED = "synced", "Synced"
        FAILED = "failed", "Failed"

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="ehr_records")
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name="ehr_records")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="ehr_records")
    record_type = models.CharField(max_length=64)
    summary = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    sync_status = models.CharField(max_length=16, choices=SyncStatus.choices, default=SyncStatus.PENDING)
    external_id = models.CharField(max_length=128, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"EHRRecord {self.pk} - {self.patient.full_name}"
