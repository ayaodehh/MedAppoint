from rest_framework import serializers

from .models import AuditLogEntry


class AuditLogEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLogEntry
        fields = "__all__"
        read_only_fields = ("id", "actor", "action", "resource_type", "resource_id", "status", "ip_address", "user_agent", "metadata", "created_at")
