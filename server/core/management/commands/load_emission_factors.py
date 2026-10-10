import json
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import WasteType


class Command(BaseCommand):
    help = "Load emission factors from a JSON file into WasteType records."

    def add_arguments(self, parser):
        parser.add_argument("file_path", type=str)

    def handle(self, *args, **options):
        file_path_str = options["file_path"]
        path = Path(file_path_str)

        if not path.is_file():
            raise CommandError(f"File not found: {file_path_str}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            raise CommandError(f"Failed to read JSON from {file_path_str}: {exc}") from exc

        if isinstance(data, dict):
            entries = []
            for code, values in data.items():
                if isinstance(values, dict):
                    entries.append(
                        {
                            "code": code,
                            "factor": values.get("factor"),
                            "source": values.get("source"),
                            "note": values.get("note", ""),
                        }
                    )
                else:
                    raise CommandError(f"Invalid entry format for waste type '{code}'")
        elif isinstance(data, list):
            entries = data
        else:
            raise CommandError("Root JSON structure must be a list or dictionary")

        for item in entries:
            code = item.get("code")
            factor = item.get("factor")
            source = item.get("source")

            if not code:
                raise CommandError("Each entry must specify a 'code'")

            if factor is not None and factor != "":
                if not source or not str(source).strip():
                    raise CommandError(f"Waste type '{code}' has a factor but missing source")

        with transaction.atomic():
            updated_count = 0
            for item in entries:
                code = str(item.get("code")).strip().lower()
                factor = item.get("factor")
                source = item.get("source")
                note = item.get("note")

                wt = WasteType.objects.filter(code=code).first()
                if not wt:
                    self.stdout.write(
                        self.style.WARNING(f"Waste type code '{code}' not found in database.")
                    )
                    continue

                if factor is not None and factor != "":
                    wt.emission_factor_kgco2e_per_kg = Decimal(str(factor))
                    wt.emission_factor_source = str(source).strip() if source else ""
                    wt.emission_factor_note = str(note).strip() if note else ""
                else:
                    wt.emission_factor_kgco2e_per_kg = None
                    wt.emission_factor_source = ""
                    wt.emission_factor_note = ""

                wt.save(
                    update_fields=[
                        "emission_factor_kgco2e_per_kg",
                        "emission_factor_source",
                        "emission_factor_note",
                    ]
                )
                updated_count += 1

        empty_types = list(
            WasteType.objects.filter(
                is_active=True,
                emission_factor_kgco2e_per_kg__isnull=True,
            )
            .values_list("code", flat=True)
            .order_by("code")
        )

        self.stdout.write(
            self.style.SUCCESS(f"Successfully loaded emission factors for {updated_count} types.")
        )
        if empty_types:
            self.stdout.write(
                self.style.WARNING(
                    f"Waste types still missing factors ({len(empty_types)}): "
                    f"{', '.join(empty_types)}"
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("All active waste types have emission factors."))
