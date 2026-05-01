from django.conf import settings
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from appointments.models import Appointment
from audit.models import AuditLogEntry
from patients.models import Patient

from .models import User


@override_settings(
    AXES_ENABLED=False,
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class AuthAndAppointmentFlowTests(APITestCase):
    def _apply_auth_cookies(self, response):
        for cookie_name in (
            settings.JWT_ACCESS_COOKIE_NAME,
            settings.JWT_REFRESH_COOKIE_NAME,
        ):
            self.client.cookies[cookie_name] = response.cookies[cookie_name].value

    def test_patient_can_register_view_profile_and_book_appointment(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "patientflow",
                "email": "patientflow@example.com",
                "first_name": "Patient",
                "last_name": "Flow",
                "phone_number": "1234567890",
                "password": "StrongPass123!",
                "medical_record_number": "MRN-TEST-1001",
                "date_of_birth": "1990-05-01",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"]["role"], User.Role.PATIENT)
        self._apply_auth_cookies(response)

        me_response = self.client.get("/api/accounts/users/me/")
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data["username"], "patientflow")

        patients_response = self.client.get("/api/patients/")
        self.assertEqual(patients_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(patients_response.data["results"]), 1)

        patient_id = patients_response.data["results"][0]["id"]
        appointment_response = self.client.post(
            "/api/appointments/",
            {
                "patient": patient_id,
                "scheduled_start": "2026-05-03T09:00:00Z",
                "scheduled_end": "2026-05-03T09:30:00Z",
                "reason": "Routine checkup",
                "notes": "Created from API integration test",
            },
            format="json",
        )

        self.assertEqual(appointment_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(appointment_response.data["status"], Appointment.Status.REQUESTED)

        list_response = self.client.get("/api/appointments/")
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data["results"]), 1)

        self.assertTrue(
            AuditLogEntry.objects.filter(action="auth.register", actor__username="patientflow").exists()
        )
        self.assertTrue(
            AuditLogEntry.objects.filter(action="appointment.create", actor__username="patientflow").exists()
        )

    def test_receptionist_can_login_list_and_confirm_appointment(self):
        patient_user = User.objects.create_user(
            username="patientexisting",
            email="patientexisting@example.com",
            password="StrongPass123!",
            role=User.Role.PATIENT,
        )
        patient = Patient.objects.create(
            user=patient_user,
            full_name="Existing Patient",
            medical_record_number="MRN-TEST-2002",
            date_of_birth="1992-04-01",
            phone_number="1234567890",
        )
        receptionist = User.objects.create_user(
            username="receptionflow",
            email="receptionflow@example.com",
            password="StrongPass123!",
            role=User.Role.RECEPTIONIST,
        )
        appointment = Appointment.objects.create(
            patient=patient,
            scheduled_start="2026-05-04T10:00:00Z",
            scheduled_end="2026-05-04T10:30:00Z",
            reason="Status update flow",
            created_by=receptionist,
            last_updated_by=receptionist,
        )

        login_response = self.client.post(
            "/api/auth/login/",
            {
                "username": "receptionflow",
                "password": "StrongPass123!",
            },
            format="json",
        )

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self._apply_auth_cookies(login_response)

        me_response = self.client.get("/api/accounts/users/me/")
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data["role"], User.Role.RECEPTIONIST)

        appointments_response = self.client.get("/api/appointments/")
        self.assertEqual(appointments_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(appointments_response.data["results"]), 1)

        set_status_response = self.client.post(
            f"/api/appointments/{appointment.pk}/set_status/",
            {"status": Appointment.Status.CONFIRMED},
            format="json",
        )

        self.assertEqual(set_status_response.status_code, status.HTTP_200_OK)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.CONFIRMED)
        self.assertTrue(
            AuditLogEntry.objects.filter(action="appointment.set_status", actor__username="receptionflow").exists()
        )
