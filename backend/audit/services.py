from audit.models import AuditLogEntry


def client_ip_from_request(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def audit_state_change(request, actor, action, instance=None, resource_type="", resource_id="", metadata=None, status_value=AuditLogEntry.Status.SUCCESS):
    resource_type = resource_type or (instance.__class__.__name__ if instance is not None else "")
    resource_id = resource_id or (str(instance.pk) if instance is not None else "")
    AuditLogEntry.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        status=status_value,
        ip_address=client_ip_from_request(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        metadata=metadata or {},
    )


def audit_auth_event(request, actor, action, status_value=AuditLogEntry.Status.SUCCESS, metadata=None):
    audit_state_change(
        request=request,
        actor=actor,
        action=action,
        resource_type="auth",
        resource_id=str(getattr(actor, "pk", "")) if actor else "",
        metadata=metadata,
        status_value=status_value,
    )
