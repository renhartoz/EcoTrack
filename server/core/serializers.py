from rest_framework import serializers

from core.models import Nasabah, WasteType
from ingestion.services.normalize import normalize_text


class NasabahSerializer(serializers.ModelSerializer):
    class Meta:
        model = Nasabah
        fields = ["id", "name", "normalized_name", "is_active", "created_at"]
        read_only_fields = ["id", "normalized_name", "created_at"]

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Name cannot be empty.")
        return value.strip()


class WasteTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WasteType
        fields = [
            "id",
            "code",
            "name_id",
            "emission_factor_kgco2e_per_kg",
            "is_active",
        ]
        read_only_fields = fields
