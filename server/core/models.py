import uuid

from django.db import models


class BankSampah(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=255, null=True, blank=True)
    is_demo = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class Nasabah(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    bank_sampah = models.ForeignKey(
        BankSampah,
        on_delete=models.CASCADE,
        related_name="nasabah",
    )
    name = models.CharField(max_length=255)
    normalized_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["bank_sampah", "normalized_name"],
                name="unique_nasabah_per_bank",
            )
        ]


class WasteType(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    code = models.SlugField(max_length=50, unique=True)
    name_id = models.CharField(max_length=255)
    emission_factor_kgco2e_per_kg = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
    )
    emission_factor_source = models.TextField(blank=True, default="")
    emission_factor_note = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class WasteTypeAlias(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    waste_type = models.ForeignKey(
        WasteType,
        on_delete=models.CASCADE,
        related_name="aliases",
    )
    alias_normalized = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
