from decimal import Decimal
import re

from rest_framework import serializers

from ingestion.models import ExtractedRow, Upload


class UploadImageCreateSerializer(serializers.Serializer):
    image = serializers.FileField(required=True)
    source_sha256 = serializers.CharField(
        max_length=64,
        required=False,
        allow_null=True,
        allow_blank=True,
    )

    def validate_source_sha256(self, value):
        if value:
            cleaned = value.strip().lower()
            if not re.fullmatch(r"^[a-f0-9]{64}$", cleaned):
                raise serializers.ValidationError("source_sha256 must be a 64-character hex string")
            return cleaned
        return None


class UploadTextCreateSerializer(serializers.Serializer):
    text = serializers.CharField(required=True, allow_blank=False)
    source_sha256 = serializers.CharField(
        max_length=64,
        required=False,
        allow_null=True,
        allow_blank=True,
    )

    def validate_source_sha256(self, value):
        if value:
            cleaned = value.strip().lower()
            if not re.fullmatch(r"^[a-f0-9]{64}$", cleaned):
                raise serializers.ValidationError("source_sha256 must be a 64-character hex string")
            return cleaned
        return None


class UploadListSerializer(serializers.ModelSerializer):
    row_count = serializers.SerializerMethodField()

    class Meta:
        model = Upload
        fields = [
            "id",
            "source_type",
            "status",
            "created_at",
            "error_code",
            "row_count",
        ]

    def get_row_count(self, obj):
        return obj.rows.count()


class ExtractedRowSerializer(serializers.ModelSerializer):
    raw = serializers.SerializerMethodField()
    normalized = serializers.SerializerMethodField()
    evidence = serializers.SerializerMethodField()
    deposit_id = serializers.SerializerMethodField()

    class Meta:
        model = ExtractedRow
        fields = [
            "id",
            "row_index",
            "status",
            "route",
            "score",
            "flags",
            "raw",
            "normalized",
            "evidence",
            "human_edited",
            "deposit_id",
        ]

    def get_raw(self, obj):
        return {
            "tanggal": obj.tanggal_raw,
            "nama": obj.nama_raw,
            "jenis": obj.jenis_raw,
            "berat": obj.berat_raw,
            "satuan": obj.satuan_raw,
            "evidence_text": obj.evidence_text,
        }

    def get_normalized(self, obj):
        return {
            "tanggal": obj.tanggal.isoformat() if obj.tanggal else None,
            "nasabah_id": obj.nasabah_id,
            "waste_type_id": obj.waste_type_id,
            "weight_kg": f"{obj.weight_kg:.3f}" if obj.weight_kg is not None else None,
        }

    def get_evidence(self, obj):
        return {
            "y_min": obj.y_min,
            "y_max": obj.y_max,
        }

    def get_deposit_id(self, obj):
        return obj.deposit_id


class ExtractedRowUpdateSerializer(serializers.Serializer):
    tanggal = serializers.DateField(required=False, allow_null=True)
    nasabah_id = serializers.IntegerField(required=False, allow_null=True)
    waste_type_id = serializers.IntegerField(required=False, allow_null=True)
    weight_kg = serializers.DecimalField(
        max_digits=10, decimal_places=3, required=False, allow_null=True
    )

    def validate_weight_kg(self, value):
        if value is not None and value <= Decimal("0"):
            raise serializers.ValidationError("Weight must be positive.")
        return value


class UploadDetailSerializer(serializers.ModelSerializer):
    page = serializers.SerializerMethodField()
    counts = serializers.SerializerMethodField()
    rows = serializers.SerializerMethodField()

    class Meta:
        model = Upload
        fields = [
            "id",
            "source_type",
            "status",
            "source_sha256",
            "created_at",
            "processing_started_at",
            "page",
            "counts",
            "rows",
            "error_code",
            "error_message",
        ]

    def get_page(self, obj):
        latest_extraction = obj.extractions.order_by("-created_at").first()
        if latest_extraction and latest_extraction.page_meta:
            return latest_extraction.page_meta
        return None

    def get_counts(self, obj):
        rows = obj.rows.all()
        return {
            "auto": rows.filter(route="auto").count(),
            "confirm": rows.filter(route="confirm").count(),
            "manual": rows.filter(route="manual").count(),
            "saved": rows.filter(status="saved").count(),
            "pending": rows.filter(status="pending").count(),
        }

    def get_rows(self, obj):
        return ExtractedRowSerializer(obj.rows.order_by("row_index"), many=True).data
