from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from django.db.models import Case, F, Q, Sum, When
from django.db.models.functions import ExtractMonth, ExtractYear
from django.utils import timezone

from core.models import BankSampah
from deposits.models import Deposit
from ingestion.models import ExtractedRow

JAKARTA_TZ = ZoneInfo("Asia/Jakarta")


def get_current_month_range_jakarta() -> tuple[date, date]:
    now_jakarta = timezone.now().astimezone(JAKARTA_TZ)
    start_date = date(now_jakarta.year, now_jakarta.month, 1)
    if now_jakarta.month == 12:
        next_month = date(now_jakarta.year + 1, 1, 1)
    else:
        next_month = date(now_jakarta.year, now_jakarta.month + 1, 1)
    end_date = next_month - timedelta(days=1)
    return start_date, end_date


def get_dashboard_summary(
    bank: BankSampah,
    from_date: date,
    to_date: date,
) -> dict[str, Any]:
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

    month_aggregates = (
        deposits.annotate(
            year=ExtractYear("deposit_date"),
            month=ExtractMonth("deposit_date"),
        )
        .values("year", "month")
        .annotate(
            weight_sum=Sum("weight_kg"),
            co2e_sum=Sum(
                Case(
                    When(
                        waste_type__emission_factor_kgco2e_per_kg__isnull=False,
                        then=(F("weight_kg") * F("waste_type__emission_factor_kgco2e_per_kg")),
                    ),
                    default=Decimal("0.000"),
                )
            ),
        )
        .order_by("year", "month")
    )

    monthly = []
    for m_item in month_aggregates:
        y = m_item["year"]
        m = m_item["month"]
        w_tot = m_item["weight_sum"]
        c_tot = m_item["co2e_sum"]
        monthly.append(
            {
                "month": f"{y:04d}-{m:02d}",
                "weight_kg": f"{w_tot:.3f}" if w_tot is not None else "0.000",
                "co2e_kg": f"{c_tot:.3f}" if c_tot is not None else "0.000",
            }
        )

    pending_rows = ExtractedRow.objects.filter(
        upload__bank_sampah=bank,
        status="pending",
    ).count()

    terminal_rows = ExtractedRow.objects.filter(
        upload__bank_sampah=bank,
        status__in=["saved", "rejected", "reverted"],
    ).filter(
        Q(tanggal__gte=from_date, tanggal__lte=to_date)
        | Q(
            tanggal__isnull=True,
            created_at__date__gte=from_date,
            created_at__date__lte=to_date,
        )
    )

    total_terminal = terminal_rows.count()
    saved_auto = terminal_rows.filter(
        status="saved",
        deposit__source="auto",
    ).count()
    edited_count = terminal_rows.filter(human_edited=True).count()

    auto_rate = round(saved_auto / total_terminal, 2) if total_terminal > 0 else 0.0
    correction_rate = round(edited_count / total_terminal, 2) if total_terminal > 0 else 0.0

    missing_types = list(
        deposits.filter(
            waste_type__emission_factor_kgco2e_per_kg__isnull=True,
        )
        .values_list("waste_type__code", flat=True)
        .distinct()
        .order_by("waste_type__code")
    )

    return {
        "period": {
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
        },
        "totals": {
            "weight_kg": weight_str,
            "co2e_kg": co2e_str,
            "deposit_count": deposit_count,
            "active_nasabah": active_nasabah,
        },
        "by_type": by_type,
        "monthly": monthly,
        "pipeline": {
            "pending_rows": pending_rows,
            "auto_rate": auto_rate,
            "correction_rate": correction_rate,
        },
        "coverage": {
            "types_missing_factor": missing_types,
        },
        "is_demo": bank.is_demo,
    }
