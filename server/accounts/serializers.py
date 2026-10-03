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
