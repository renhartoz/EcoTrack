import os
import random
from datetime import date
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.models import BankSampah, Nasabah, WasteType
from core.services.text import normalize_text
from deposits.models import Deposit

JAKARTA_TZ = ZoneInfo("Asia/Jakarta")

FICTIONAL_NASABAH = [
    "Budi Santoso",
    "Siti Aminah",
    "Agus Setiawan",
    "Dewi Lestari",
    "Eko Prasetyo",
    "Rina Wulandari",
    "Joko Widodo",
    "Sri Wahyuni",
    "Hendra Kurniawan",
    "Tri Handayani",
    "Bambang Pamungkas",
    "Endang Susilowati",
]


class Command(BaseCommand):
    help = "Seed deterministic demo bank, operator, nasabah, and 3 months of synthetic deposits."

    def handle(self, *args, **options):
        waste_types = list(WasteType.objects.filter(is_active=True).order_by("id"))
        if not waste_types:
            raise CommandError("No active waste types found. Run loaddata waste_types first.")

        rng = random.Random(42)

        username = (
            getattr(settings, "DEMO_OPERATOR_USERNAME", None)
            or os.environ.get("DEMO_OPERATOR_USERNAME")
            or "demo_operator"
        )
        password = (
            getattr(settings, "DEMO_OPERATOR_PASSWORD", None)
            or os.environ.get("DEMO_OPERATOR_PASSWORD")
            or "DemoPassword123!"
        )

        with transaction.atomic():
            bank, _ = BankSampah.objects.get_or_create(
                name="Bank Sampah Demo",
                defaults={"city": "Yogyakarta", "is_demo": True},
            )
            if not bank.is_demo:
                bank.is_demo = True
                bank.save(update_fields=["is_demo"])

            user_model = get_user_model()
            user = user_model.objects.filter(username=username).first()
            if not user:
                user = user_model.objects.create_user(
                    username=username,
                    password=password,
                    bank_sampah=bank,
                )
            else:
                user.bank_sampah = bank
                user.set_password(password)
                user.save()

            Deposit.objects.filter(bank_sampah=bank).delete()

            nasabah_list = []
            for name in FICTIONAL_NASABAH:
                nasabah, _ = Nasabah.objects.get_or_create(
                    bank_sampah=bank,
                    name=name,
                    defaults={
                        "normalized_name": normalize_text(name),
                        "is_active": True,
                    },
                )
                nasabah_list.append(nasabah)

            now_jakarta = timezone.now().astimezone(JAKARTA_TZ)
            y, m = now_jakarta.year, now_jakarta.month
            target_months = []
            for _ in range(3):
                target_months.append((y, m))
                m -= 1
                if m == 0:
                    m = 12
                    y -= 1
            target_months.reverse()

            total_deposits_created = 0
            for year_val, month_val in target_months:
                deposit_count = rng.randint(20, 30)
                for _ in range(deposit_count):
                    chosen_nasabah = rng.choice(nasabah_list)
                    chosen_wt = rng.choice(waste_types)
                    day_val = rng.randint(1, 28)
                    deposit_date = date(year_val, month_val, day_val)
                    raw_weight = rng.uniform(1.0, 30.0)
                    weight_kg = Decimal(f"{raw_weight:.3f}")

                    Deposit.objects.create(
                        bank_sampah=bank,
                        nasabah=chosen_nasabah,
                        waste_type=chosen_wt,
                        weight_kg=weight_kg,
                        deposit_date=deposit_date,
                        source="manual",
                        created_by=user,
                    )
                    total_deposits_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded demo bank '{bank.name}' with {len(nasabah_list)} nasabah "
                f"and {total_deposits_created} deposits across 3 months."
            )
        )
