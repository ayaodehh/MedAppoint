from rest_framework.permissions import BasePermission


def owns_patient_record(user, obj):
    owner = getattr(obj, "user", None)
    if owner is not None:
        return owner_id_matches(owner, user)

    patient = getattr(obj, "patient", None)
    if patient is not None:
        return owner_id_matches(getattr(patient, "user", None), user)

    return False


def owner_id_matches(owner, user):
    return bool(owner and user and owner.pk == user.pk)


class DenyAll(BasePermission):
    def has_permission(self, request, view):
        return False


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "admin")


class IsClinicianRole(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "clinician")


class IsReceptionistRole(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "receptionist")


class IsBillingRole(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "billing")


class IsPatientRole(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "patient")


class IsAuditorRole(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "auditor")


class RoleMappedPermission(BasePermission):
    action_role_map = {}
    patient_actions = set()

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        allowed_roles = self.action_role_map.get(getattr(view, "action", None), ())
        return request.user.role in allowed_roles

    def has_object_permission(self, request, view, obj):
        action = getattr(view, "action", None)
        if request.user.role == "patient" and action in self.patient_actions:
            return owns_patient_record(request.user, obj)
        if request.user.role == "auditor":
            return request.method in ("GET", "HEAD", "OPTIONS")
        return True


class UserPermission(RoleMappedPermission):
    action_role_map = {
        "create": ("admin",),
        "list": ("admin", "auditor"),
        "retrieve": ("admin", "auditor", "patient", "clinician", "receptionist", "billing"),
        "me": ("admin", "auditor", "patient", "clinician", "receptionist", "billing"),
        "update": ("admin",),
        "partial_update": ("admin",),
        "destroy": ("admin",),
    }
    patient_actions = {"retrieve", "me"}

    def has_object_permission(self, request, view, obj):
        if request.user.role == "patient":
            return obj.pk == request.user.pk
        if request.user.role in {"clinician", "receptionist", "billing"}:
            return request.method in ("GET", "HEAD", "OPTIONS")
        return super().has_object_permission(request, view, obj)


class PatientPermission(RoleMappedPermission):
    action_role_map = {
        "create": ("admin", "receptionist"),
        "list": ("admin", "receptionist", "clinician", "auditor", "patient"),
        "retrieve": ("admin", "receptionist", "clinician", "auditor", "patient"),
        "update": ("admin", "receptionist", "clinician"),
        "partial_update": ("admin", "receptionist", "clinician"),
        "destroy": ("admin",),
    }
    patient_actions = {"list", "retrieve"}


class AppointmentPermission(RoleMappedPermission):
    action_role_map = {
        "create": ("admin", "receptionist", "patient"),
        "list": ("admin", "receptionist", "clinician", "auditor", "patient"),
        "retrieve": ("admin", "receptionist", "clinician", "auditor", "patient"),
        "update": ("admin", "receptionist", "clinician"),
        "partial_update": ("admin", "receptionist", "clinician", "patient"),
        "destroy": ("admin", "receptionist"),
        "set_status": ("admin", "receptionist", "clinician"),
    }
    patient_actions = {"list", "retrieve", "partial_update"}


class ClinicalPermission(RoleMappedPermission):
    action_role_map = {
        "create": ("admin", "clinician"),
        "list": ("admin", "clinician", "auditor", "patient"),
        "retrieve": ("admin", "clinician", "auditor", "patient"),
        "update": ("admin", "clinician"),
        "partial_update": ("admin", "clinician"),
        "destroy": ("admin",),
    }
    patient_actions = {"list", "retrieve"}


class BillingPermission(RoleMappedPermission):
    action_role_map = {
        "create": ("admin", "billing"),
        "list": ("admin", "billing", "auditor", "patient"),
        "retrieve": ("admin", "billing", "auditor", "patient"),
        "update": ("admin", "billing"),
        "partial_update": ("admin", "billing"),
        "destroy": ("admin",),
        "charge": ("admin", "billing"),
    }
    patient_actions = {"list", "retrieve"}


class BillingTransactionPermission(RoleMappedPermission):
    action_role_map = {
        "create": ("admin", "billing"),
        "list": ("admin", "billing", "auditor"),
        "retrieve": ("admin", "billing", "auditor"),
    }


class EHRPermission(RoleMappedPermission):
    action_role_map = {
        "create": ("admin", "clinician"),
        "list": ("admin", "clinician", "auditor", "patient"),
        "retrieve": ("admin", "clinician", "auditor", "patient"),
        "update": ("admin", "clinician"),
        "partial_update": ("admin", "clinician"),
        "destroy": ("admin",),
        "sync_record": ("admin", "clinician"),
    }
    patient_actions = {"list", "retrieve"}


class AuditPermission(RoleMappedPermission):
    action_role_map = {
        "list": ("admin", "auditor"),
        "retrieve": ("admin", "auditor"),
    }
