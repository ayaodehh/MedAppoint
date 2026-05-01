from rest_framework import serializers

from .models import EHRRecord


class EHRRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = EHRRecord
        fields = "__all__"
        read_only_fields = ("author", "last_synced_at", "created_at", "updated_at")
