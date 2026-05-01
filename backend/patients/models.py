import uuid

from django.conf import settings
from django.db import models


class Patient(models.Model):
    class Sex(models.TextChoices):
        FEMALE = "female", "Female"
        MALE = "male", "Male"
        OTHER = "other", "Other"
        UNSPECIFIED = "unspecified", "Unspecified"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="patient_profile")
    full_name = models.CharField(max_length=255)
    medical_record_number = models.CharField(max_length=64, unique=True)
    date_of_birth = models.DateField()
    sex = models.CharField(max_length=16, choices=Sex.choices, default=Sex.UNSPECIFIED)
    phone_number = models.CharField(max_length=32, blank=True)
    emergency_contact = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True)
    allergies = models.TextField(blank=True)
    insurance_provider = models.CharField(max_length=255, blank=True)
    insurance_number = models.CharField(max_length=128, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("full_name",)

    def __str__(self):
        return f"{self.full_name} ({self.medical_record_number})"
