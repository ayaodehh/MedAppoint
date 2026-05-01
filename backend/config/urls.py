from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts.views import AuthSessionViewSet, UserViewSet
from appointments.views import AppointmentViewSet
from audit.views import AuditLogEntryViewSet
from billing.views import BillingTransactionViewSet, InvoiceViewSet
from clinical.views import ClinicalNoteViewSet
from ehr.views import EHRRecordViewSet
from patients.views import PatientViewSet

router = DefaultRouter()
router.trailing_slash = "/?"
router.register("accounts/users", UserViewSet, basename="user")
router.register("auth", AuthSessionViewSet, basename="auth")
router.register("patients", PatientViewSet, basename="patient")
router.register("appointments", AppointmentViewSet, basename="appointment")
router.register("clinical/notes", ClinicalNoteViewSet, basename="clinical-note")
router.register("billing/invoices", InvoiceViewSet, basename="invoice")
router.register("billing/transactions", BillingTransactionViewSet, basename="billing-transaction")
router.register("ehr/records", EHRRecordViewSet, basename="ehr-record")
router.register("audit/logs", AuditLogEntryViewSet, basename="audit-log")

urlpatterns = [
    path("api/", include(router.urls)),
]
