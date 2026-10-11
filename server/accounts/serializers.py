from rest_framework import serializers

from accounts.models import User
from core.models import BankSampah


class BankSampahSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = BankSampah
        fields = ["id", "name", "city", "is_demo"]


class UserSummarySerializer(serializers.ModelSerializer):
    bank_sampah = BankSampahSummarySerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "bank_sampah"]


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, allow_blank=False)
    password = serializers.CharField(required=True, allow_blank=False, write_only=True)


class RegisterDemoSerializer(serializers.Serializer):
    username = serializers.CharField(required=False, allow_blank=True, max_length=150)
    password = serializers.CharField(
        required=False,
        allow_blank=True,
        min_length=8,
        write_only=True,
    )
    bank_name = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate_username(self, value):
        if value:
            clean_value = value.strip()
            if User.objects.filter(username=clean_value).exists():
                raise serializers.ValidationError("Username already exists.")
            return clean_value
        return value
