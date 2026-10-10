from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from django.db.models import F, Sum
from django.utils import timezone

from core.models import BankSampah, WasteType
from deposits.models import Deposit

JAKARTA_TZ = ZoneInfo("Asia/Jakarta")

MONTH_NAMES_ID = {
    1: "Januari",
    2: "Februari",
    3: "Maret",
    4: "April",
    5: "Mei",
    6: "Juni",
    7: "Juli",
    8: "Agustus",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Desember",
}


def get_current_month_jakarta() -> tuple[int, int]:
    now_jakarta = timezone.now().astimezone(JAKARTA_TZ)
    return now_jakarta.year, now_jakarta.month


def build_narrative_template(
    year: int,
    month: int,
    figures: dict[str, Any],
) -> dict[str, Any]:
    month_name = MONTH_NAMES_ID.get(month, str(month))
    deposit_count = figures["deposit_count"]
    active_nasabah = figures["active_nasabah"]
    weight_kg = figures["weight_kg"]
    co2e_kg = figures["co2e_kg"]

    if deposit_count == 0:
        text = f"Pada periode {month_name} {year}, belum ada setoran sampah yang tercatat."
    else:
        text = (
            f"Pada periode {month_name} {year}, Bank Sampah mencatat {deposit_count} setoran "
            f"dari {active_nasabah} nasabah aktif dengan total berat sampah {weight_kg} kg."
        )
        if Decimal(co2e_kg) > Decimal("0.000"):
            text += f" Estimasi pengurangan emisi gas rumah kaca mencapai {co2e_kg} kg CO2e."

    return {
        "text": text,
        "source": "template",
        "verified": True,
    }


def get_impact_report(
    bank: BankSampah,
    year: int,
    month: int,
) -> dict[str, Any]:
    from_date = date(year, month, 1)
    if month == 12:
        next_m = date(year + 1, 1, 1)
    else:
        next_m = date(year, month + 1, 1)
    to_date = next_m - timedelta(days=1)

    deposits = Deposit.objects.filter(
        bank_sampah=bank,
        deleted_at__isnull=True,
        deposit_date__gte=from_date,
        deposit_date__lte=to_date,
    )

    weight_sum = deposits.aggregate(total=Sum("weight_kg"))["total"]
    weight_str = f"{weight_sum:.3f}" if weight_sum is not None else "0.000"

    deposits_with_factor = deposits.filter(
        waste_type__emission_factor_kgco2e_per_kg__isnull=False,
    )
    co2e_sum = deposits_with_factor.aggregate(
        total=Sum(F("weight_kg") * F("waste_type__emission_factor_kgco2e_per_kg")),
    )["total"]
    co2e_str = f"{co2e_sum:.3f}" if co2e_sum is not None else "0.000"

    deposit_count = deposits.count()
    active_nasabah = deposits.values("nasabah_id").distinct().count()

    type_aggregates = (
        deposits.values(
            "waste_type__code",
            "waste_type__name_id",
            "waste_type__emission_factor_kgco2e_per_kg",
        )
        .annotate(
            weight_sum=Sum("weight_kg"),
            co2e_sum=Sum(F("weight_kg") * F("waste_type__emission_factor_kgco2e_per_kg")),
        )
        .order_by("-weight_sum")
    )

    by_type = []
    for item in type_aggregates:
        w_val = item["weight_sum"]
        has_factor = item["waste_type__emission_factor_kgco2e_per_kg"] is not None
        if has_factor and item["co2e_sum"] is not None:
            c_val = f"{item['co2e_sum']:.3f}"
        else:
            c_val = None
        by_type.append(
            {
                "waste_type": item["waste_type__code"],
                "name_id": item["waste_type__name_id"],
                "weight_kg": f"{w_val:.3f}" if w_val is not None else "0.000",
                "co2e_kg": c_val,
            }
        )

    figures = {
        "weight_kg": weight_str,
        "co2e_kg": co2e_str,
        "deposit_count": deposit_count,
        "active_nasabah": active_nasabah,
        "by_type": by_type,
    }

    methodology_factors = [
        {
            "waste_type": wt.code,
            "factor": f"{wt.emission_factor_kgco2e_per_kg:.3f}",
            "source": wt.emission_factor_source,
            "note": wt.emission_factor_note,
        }
        for wt in WasteType.objects.filter(
            is_active=True,
            emission_factor_kgco2e_per_kg__isnull=False,
        ).order_by("code")
    ]

    missing_types = list(
        deposits.filter(
            waste_type__emission_factor_kgco2e_per_kg__isnull=True,
        )
        .values_list("waste_type__code", flat=True)
        .distinct()
        .order_by("waste_type__code")
    )

    narrative = build_narrative_template(year, month, figures)

    return {
        "period": {
            "month": f"{year:04d}-{month:02d}",
        },
        "figures": figures,
        "methodology": {
            "factors": methodology_factors,
        },
        "narrative": narrative,
        "coverage": {
            "types_missing_factor": missing_types,
        },
        "is_demo": bank.is_demo,
    }
