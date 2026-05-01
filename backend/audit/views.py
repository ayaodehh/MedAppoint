from rest_framework import mixins, viewsets

from accounts.permissions import AuditPermission

from .models import AuditLogEntry
from .serializers import AuditLogEntrySerializer


class AuditLogEntryViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = AuditLogEntry.objects.select_related("actor").all()
    serializer_class = AuditLogEntrySerializer
    permission_classes = [AuditPermission]
