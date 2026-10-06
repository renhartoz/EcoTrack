from django.db import models


class Deposit(models.Model):
    bank_sampah = models.ForeignKey(
        "core.BankSampah",
        on_delete=models.CASCADE,
        related_name="deposits",
    )
    nasabah = models.ForeignKey(
        "core.Nasabah",
        on_delete=models.CASCADE,
        related_name="deposits",
    )
    waste_type = models.ForeignKey(
        "core.WasteType",
        on_delete=models.CASCADE,
        related_name="deposits",
    )
    weight_kg = models.DecimalField(
        max_digits=10,
        decimal_places=3,
    )
    deposit_date = models.DateField()
    source = models.CharField(
        max_length=20,
        choices=[
            ("auto", "Auto"),
            ("confirmed", "Confirmed"),
            ("manual", "Manual"),
        ],
    )
    upload = models.ForeignKey(
        "ingestion.Upload",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deposits",
    )
    created_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="deposits",
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )


class AuditLog(models.Model):
    bank_sampah = models.ForeignKey(
        "core.BankSampah",
        on_delete=models.CASCADE,
        related_name="audit_logs",
    )
    actor = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    actor_label = models.CharField(
        max_length=255,
    )
    action = models.CharField(
        max_length=20,
        choices=[
            ("create", "Create"),
            ("update", "Update"),
            ("delete", "Delete"),
            ("auto_save", "Auto Save"),
            ("revert", "Revert"),
        ],
    )
    entity_type = models.CharField(
        max_length=50,
    )
    entity_id = models.IntegerField()
    before = models.JSONField(
        default=dict,
        blank=True,
    )
    after = models.JSONField(
        default=dict,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
