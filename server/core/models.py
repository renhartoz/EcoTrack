from django.db import models


class BankSampah(models.Model):
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=255, null=True, blank=True)
    is_demo = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class Nasabah(models.Model):
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
