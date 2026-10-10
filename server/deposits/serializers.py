from decimal import Decimal
from rest_framework import serializers

from core.models import Nasabah, WasteType
from deposits.models import Deposit


class NasabahNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Nasabah
        fields = ["id", "name"]


class WasteTypeNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = WasteType
        fields = ["id", "code", "name_id"]


class DepositSerializer(serializers.ModelSerializer):
    nasabah = NasabahNestedSerializer(read_only=True)
    waste_type = WasteTypeNestedSerializer(read_only=True)
    weight_kg = serializers.SerializerMethodField()
    upload_id = serializers.IntegerField(source="upload.id", allow_null=True, read_only=True)

    class Meta:
        model = Deposit
        fields = [
            "id",
            "nasabah",
            "waste_type",
            "weight_kg",
            "deposit_date",
            "source",
            "upload_id",
            "created_at",
        ]
        read_only_fields = fields

    def get_weight_kg(self, obj):
        if obj.weight_kg is not None:
            return f"{obj.weight_kg:.3f}"
        return None


class DepositCreateSerializer(serializers.Serializer):
    nasabah_id = serializers.IntegerField()
    waste_type_id = serializers.IntegerField()
    weight_kg = serializers.DecimalField(max_digits=10, decimal_places=3)
    deposit_date = serializers.DateField()

    def validate_weight_kg(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError("Weight must be positive.")
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        bank = getattr(request.user, "bank_sampah", None) if request else None

        if not bank:
            raise serializers.ValidationError("User has no associated bank.")

        try:
            nasabah = Nasabah.objects.get(id=attrs["nasabah_id"], bank_sampah=bank)
            if not nasabah.is_active:
                raise serializers.ValidationError({"nasabah_id": "Nasabah is inactive."})
            attrs["nasabah"] = nasabah
        except Nasabah.DoesNotExist:
            raise serializers.ValidationError({"nasabah_id": "Nasabah not found in this bank."})

        try:
            waste_type = WasteType.objects.get(id=attrs["waste_type_id"])
            attrs["waste_type"] = waste_type
        except WasteType.DoesNotExist:
            raise serializers.ValidationError({"waste_type_id": "Waste type not found."})

        return attrs


class DepositUpdateSerializer(serializers.Serializer):
    nasabah_id = serializers.IntegerField(required=False)
    waste_type_id = serializers.IntegerField(required=False)
    weight_kg = serializers.DecimalField(max_digits=10, decimal_places=3, required=False)
    deposit_date = serializers.DateField(required=False)

    def validate_weight_kg(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError("Weight must be positive.")
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        bank = getattr(request.user, "bank_sampah", None) if request else None

        if "nasabah_id" in attrs:
            try:
                nasabah = Nasabah.objects.get(id=attrs["nasabah_id"], bank_sampah=bank)
                attrs["nasabah"] = nasabah
            except Nasabah.DoesNotExist:
                raise serializers.ValidationError({"nasabah_id": "Nasabah not found in this bank."})

        if "waste_type_id" in attrs:
            try:
                attrs["waste_type"] = WasteType.objects.get(id=attrs["waste_type_id"])
            except WasteType.DoesNotExist:
                raise serializers.ValidationError({"waste_type_id": "Waste type not found."})

        return attrs
