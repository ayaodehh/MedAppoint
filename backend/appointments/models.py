from django.conf import settings
from django.db import models
from decimal import Decimal

from patients.models import Patient


class Appointment(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        CONFIRMED = "confirmed", "Confirmed"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No Show"

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="appointments")
    clinician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointments_as_clinician",
    )
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.REQUESTED)
    reason = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="appointments_created")
    last_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="appointments_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("scheduled_start",)

    @property
    def billable_amount(self):
        # Appointment billing is server-owned; invoices must derive amount_due from
        # this value instead of trusting any client-supplied amount.
        return Decimal(getattr(settings, "APPOINTMENT_BILLABLE_AMOUNT", "100.00"))

    def __str__(self):
        return f"Appointment {self.pk} - {self.patient.full_name}"
