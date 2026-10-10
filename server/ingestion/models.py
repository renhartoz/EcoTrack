from django.db import models


class Upload(models.Model):
    bank_sampah = models.ForeignKey(
        "core.BankSampah",
        on_delete=models.CASCADE,
        related_name="uploads",
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="uploads",
    )
    source_type = models.CharField(
        max_length=10,
        choices=[
            ("image", "Image"),
            ("text", "Text"),
        ],
    )
    source_sha256 = models.CharField(
        max_length=64,
        null=True,
        blank=True,
    )
    image_sha256 = models.CharField(
        max_length=64,
        null=True,
        blank=True,
    )
    raw_text = models.TextField(
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        default="processing",
        choices=[
            ("processing", "Processing"),
            ("ready", "Ready"),
            ("failed", "Failed"),
        ],
    )
    processing_started_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    error_code = models.CharField(
        max_length=50,
        null=True,
        blank=True,
    )
    error_message = models.TextField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )


class UploadImage(models.Model):
    upload = models.OneToOneField(
        Upload,
        on_delete=models.CASCADE,
        related_name="image",
    )
    content_type = models.CharField(
        max_length=50,
        default="image/jpeg",
    )
    data = models.BinaryField()
    created_at = models.DateTimeField(
        auto_now_add=True,
    )


class Extraction(models.Model):
    upload = models.ForeignKey(
        Upload,
        on_delete=models.CASCADE,
        related_name="extractions",
    )
    strategy = models.CharField(
        max_length=20,
        choices=[
            ("vision", "Vision"),
            ("ocr_text", "OCR Text"),
            ("hybrid", "Hybrid"),
            ("text", "Text"),
        ],
    )
    provider = models.CharField(
        max_length=50,
    )
    model = models.CharField(
        max_length=100,
    )
    ocr_engine = models.CharField(
        max_length=20,
        null=True,
        blank=True,
    )
    prompt_version = models.CharField(
        max_length=50,
    )
    schema_version = models.CharField(
        max_length=50,
    )
    raw_response = models.JSONField(
        default=dict,
    )
    ocr_lines = models.JSONField(
        null=True,
        blank=True,
    )
    page_meta = models.JSONField(
        default=dict,
    )
    latency_ms = models.IntegerField(
        default=0,
    )
    input_tokens = models.IntegerField(
        default=0,
    )
    output_tokens = models.IntegerField(
        default=0,
    )
    from_cache = models.BooleanField(
        default=False,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )


class ExtractedRow(models.Model):
    upload = models.ForeignKey(
        Upload,
        on_delete=models.CASCADE,
        related_name="rows",
    )
    extraction = models.ForeignKey(
        Extraction,
        on_delete=models.CASCADE,
        related_name="rows",
    )
    row_index = models.IntegerField()
    tanggal_raw = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )
    nama_raw = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    jenis_raw = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    berat_raw = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )
    satuan_raw = models.CharField(
        max_length=50,
        null=True,
        blank=True,
    )
    evidence_text = models.TextField(
        default="",
    )
    has_correction = models.BooleanField(
        default=False,
    )
    date_is_repeat = models.BooleanField(
        default=False,
    )
    llm_confidence = models.FloatField(
        default=0.0,
    )
    y_min = models.FloatField(
        null=True,
        blank=True,
    )
    y_max = models.FloatField(
        null=True,
        blank=True,
    )
    source_lines = models.JSONField(
        null=True,
        blank=True,
    )
    tanggal = models.DateField(
        null=True,
        blank=True,
    )
    nasabah = models.ForeignKey(
        "core.Nasabah",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="extracted_rows",
    )
    waste_type = models.ForeignKey(
        "core.WasteType",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="extracted_rows",
    )
    weight_kg = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
    )
    flags = models.JSONField(
        default=list,
    )
    score = models.FloatField(
        null=True,
        blank=True,
    )
    route = models.CharField(
        max_length=20,
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        default="pending",
        choices=[
            ("pending", "Pending"),
            ("saved", "Saved"),
            ("rejected", "Rejected"),
            ("reverted", "Reverted"),
        ],
    )
    human_edited = models.BooleanField(
        default=False,
    )
    deposit = models.OneToOneField(
        "deposits.Deposit",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="extracted_row",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["extraction", "row_index"],
                name="unique_row_per_extraction",
            )
        ]


class ProviderCache(models.Model):
    key = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
    )
    kind = models.CharField(
        max_length=10,
        choices=[
            ("llm", "LLM"),
            ("ocr", "OCR"),
        ],
    )
    response = models.JSONField()
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
