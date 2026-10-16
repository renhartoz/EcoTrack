import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from eval.metrics import evaluate_pages


class Command(BaseCommand):
    help = "Sweep T_AUTO and T_CONFIRM thresholds over saved evaluation results."

    def add_arguments(self, parser):
        parser.add_argument(
            "--run",
            type=str,
            required=True,
            help="Path to evaluation run directory or run_results.json.",
        )
        parser.add_argument(
            "--target-precision",
            type=float,
            default=0.98,
            help="Target auto-lane precision (default: 0.98).",
        )

    def handle(self, *args, **options):
        run_path = Path(options["run"])
        json_path = run_path / "run_results.json" if run_path.is_dir() else run_path
        if not json_path.exists():
            raise CommandError(f"Run results file not found: {json_path}")

        with open(json_path, encoding="utf-8") as f:
            run_data = json.load(f)

        pages = run_data.get("pages", [])
        target_precision = float(options["target_precision"])

        t_auto_grid = [round(0.80 + i * 0.02, 2) for i in range(10)]
        t_confirm_grid = [0.50, 0.55, 0.60, 0.65, 0.70]

        sweep_rows: list[dict[str, Any]] = []
        chosen: dict[str, Any] | None = None

        for t_auto in t_auto_grid:
            m = evaluate_pages(pages, t_auto=t_auto, t_confirm=0.60)
            row_entry = {
                "t_auto": t_auto,
                "t_confirm": 0.60,
                "n_auto": m["n_auto"],
                "auto_precision": m["auto_precision"],
                "auto_coverage": m["auto_coverage"],
                "unsafe_auto_rate": m["unsafe_auto_rate"],
            }
            sweep_rows.append(row_entry)
            if (
                chosen is None
                and m["n_auto"] > 0
                and m["auto_precision"] >= target_precision
                and m["unsafe_auto_rate"] == 0.0
            ):
                chosen = row_entry

        confirm_sweep: list[dict[str, Any]] = []
        best_t_auto = chosen["t_auto"] if chosen else 0.92
        for t_confirm in t_confirm_grid:
            m = evaluate_pages(pages, t_auto=best_t_auto, t_confirm=t_confirm)
            confirm_sweep.append(
                {
                    "t_auto": best_t_auto,
                    "t_confirm": t_confirm,
                    "n_confirm": m["n_confirm"],
                    "n_manual": m["n_manual"],
                }
            )

        sweep_payload = {
            "target_precision": target_precision,
            "recommended_t_auto": chosen["t_auto"] if chosen else None,
            "recommended_t_confirm": 0.60,
            "auto_save_recommended": chosen is not None,
            "t_auto_sweep": sweep_rows,
            "t_confirm_sweep": confirm_sweep,
        }

        out_file = json_path.parent / "sweep.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(sweep_payload, f, indent=2)

        if chosen:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Recommended T_AUTO={chosen['t_auto']:.2f} "
                    f"(precision={chosen['auto_precision'] * 100:.1f}%, "
                    f"coverage={chosen['auto_coverage'] * 100:.1f}%, "
                    f"unsafe_auto={chosen['unsafe_auto_rate'] * 100:.1f}%) -> {out_file}"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"No T_AUTO reached target precision {target_precision:.2f}; "
                    f"keep AUTO_SAVE_ENABLED=false -> {out_file}"
                )
            )
