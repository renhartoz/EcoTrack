import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    bank_sampah = models.ForeignKey(
        "core.BankSampah",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
    )
    created_at = models.DateTimeField(auto_now_add=True)
