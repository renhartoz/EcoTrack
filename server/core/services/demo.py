import random
import uuid
from datetime import date
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone

from accounts.models import User
from core.models import BankSampah, Nasabah, WasteType
from deposits.models import Deposit
from ingestion.services.normalize import normalize_text

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


def create_demo_account(
    username: str | None = None,
    password: str | None = None,
    bank_name: str | None = None,
) -> tuple[User, str]:
    waste_types = list(WasteType.objects.filter(is_active=True).order_by("id"))
    if not waste_types:
        raise ValueError("No active waste types found. Load waste types fixture first.")

    if username and username.strip():
        final_username = username.strip()
    else:
        final_username = f"juri_{uuid.uuid4().hex[:8]}"
    final_password = password if password and password.strip() else "DemoJudge2026!"
    final_bank_name = (
        bank_name.strip()
        if bank_name and bank_name.strip()
        else f"Bank Sampah Demo ({final_username})"
    )

    seed_value = int.from_bytes(final_username.encode(), "big") % (2**32)
    rng = random.Random(seed_value)

    with transaction.atomic():
        bank = BankSampah.objects.create(
            name=final_bank_name,
            city="Yogyakarta",
            is_demo=True,
        )

        user = User.objects.create_user(
            username=final_username,
            password=final_password,
            bank_sampah=bank,
        )

        nasabah_list: list[Nasabah] = []
        for name in FICTIONAL_NASABAH:
            nasabah = Nasabah.objects.create(
                bank_sampah=bank,
                name=name,
                normalized_name=normalize_text(name),
                is_active=True,
            )
            nasabah_list.append(nasabah)

        now_jakarta = timezone.now().astimezone(JAKARTA_TZ)
        y, m = now_jakarta.year, now_jakarta.month
        target_months: list[tuple[int, int]] = []
        for _ in range(3):
            target_months.append((y, m))
            m -= 1
            if m == 0:
                m = 12
                y -= 1
        target_months.reverse()

        deposits_to_create: list[Deposit] = []
        for year_val, month_val in target_months:
            deposit_count = rng.randint(20, 30)
            for _ in range(deposit_count):
                chosen_nasabah = rng.choice(nasabah_list)
                chosen_wt = rng.choice(waste_types)
                day_val = rng.randint(1, 28)
                deposit_date = date(year_val, month_val, day_val)
                raw_weight = rng.uniform(1.0, 30.0)
                weight_kg = Decimal(f"{raw_weight:.3f}")

                deposits_to_create.append(
                    Deposit(
                        bank_sampah=bank,
                        nasabah=chosen_nasabah,
                        waste_type=chosen_wt,
                        weight_kg=weight_kg,
                        deposit_date=deposit_date,
                        source="manual",
                        created_by=user,
                    )
                )

        Deposit.objects.bulk_create(deposits_to_create)

    return user, final_password
