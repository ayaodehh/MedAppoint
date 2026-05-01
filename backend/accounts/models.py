from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        CLINICIAN = "clinician", "Clinician"
        RECEPTIONIST = "receptionist", "Receptionist"
        BILLING = "billing", "Billing"
        PATIENT = "patient", "Patient"
        AUDITOR = "auditor", "Auditor"

    role = models.CharField(max_length=32, choices=Role.choices, default=Role.PATIENT)
    phone_number = models.CharField(max_length=32, blank=True)
    otp_required = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    def __str__(self):
        return f"{self.username} ({self.role})"
