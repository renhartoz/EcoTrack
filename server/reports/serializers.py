from datetime import datetime

from rest_framework import serializers


class DashboardSummaryQuerySerializer(serializers.Serializer):
    from_date = serializers.DateField(required=False, input_formats=["%Y-%m-%d"])
    to_date = serializers.DateField(required=False, input_formats=["%Y-%m-%d"])

    def validate(self, attrs):
        from_val = attrs.get("from_date")
        to_val = attrs.get("to_date")
        if from_val and to_val and from_val > to_val:
            raise serializers.ValidationError("from must be less than or equal to to")
        return attrs


class ImpactReportQuerySerializer(serializers.Serializer):
    month = serializers.CharField(required=False)

    def validate_month(self, value):
        if not value:
            return None
        try:
            parsed = datetime.strptime(value.strip(), "%Y-%m")
            return parsed.year, parsed.month
        except ValueError:
            raise serializers.ValidationError("month must be in YYYY-MM format")
