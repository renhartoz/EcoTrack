import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Generate Markdown evaluation report summary.md from evaluation runs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--run",
            type=str,
            nargs="+",
            required=True,
            help="One or more evaluation run directories or run_results.json files.",
        )
        parser.add_argument(
            "--out",
            type=str,
            default="eval/results/summary.md",
            help="Output path for summary.md.",
        )

    def handle(self, *args, **options):
        run_inputs: list[str] = options["run"]
        runs: list[dict[str, Any]] = []

        for r_in in run_inputs:
            p = Path(r_in)
            if p.is_dir():
                direct_json = p / "run_results.json"
                if direct_json.exists():
                    with open(direct_json, encoding="utf-8") as f:
                        runs.append(json.load(f))
                else:
                    for sub_json in sorted(p.glob("*/run_results.json")):
                        with open(sub_json, encoding="utf-8") as f:
                            runs.append(json.load(f))
            elif p.exists():
                with open(p, encoding="utf-8") as f:
                    runs.append(json.load(f))
            else:
                raise CommandError(f"Run path not found: {p}")

        if not runs:
            raise CommandError("No run_results.json files found.")

        lines: list[str] = [
            "# EcoTrack Evaluation Report",
            "",
            "## 1. Strategy and Split Comparison",
            "",
            (
                "| Strategi | Split | n Row | Exact (%) | Auto Precision (%) | "
                "Auto Coverage (%) | Unsafe Auto (%) | Latensi p50 (dtk) |"
            ),
            "|---|---|---|---|---|---|---|---|",
        ]

        for r in runs:
            strat = r.get("strategy", "ocr_text")
            split = r.get("split", "dev").capitalize()
            m = r.get("metrics", {})
            n_gold = m.get("n_gold", 0)
            n_exact = m.get("n_row_exact", 0)
            n_auto = m.get("n_auto", 0)
            n_auto_exact = m.get("n_auto_exact", 0)
            n_must_not = m.get("n_must_not_auto", 0)
            n_unsafe = m.get("n_unsafe_auto", 0)

            exact_str = f"{m.get('row_exact_rate', 0.0) * 100:.1f}% ({n_exact}/{n_gold})"
            auto_prec_str = f"{m.get('auto_precision', 0.0) * 100:.1f}% ({n_auto_exact}/{n_auto})"
            auto_cov_str = f"{m.get('auto_coverage', 0.0) * 100:.1f}% ({n_auto}/{n_gold})"
            unsafe_str = f"{m.get('unsafe_auto_rate', 0.0) * 100:.1f}% ({n_unsafe}/{n_must_not})"
            p50_str = f"{m.get('latency_p50_s', 0.0):.2f}"

            lines.append(
                f"| `{strat}` | {split} | {n_gold} | {exact_str} | "
                f"{auto_prec_str} | {auto_cov_str} | {unsafe_str} | {p50_str} |"
            )

        lines.extend(
            [
                "",
                "## 2. Per-Field Accuracy and Token Usage",
                "",
                (
                    "| Strategi | Split | Tanggal Exact | Nasabah Exact | Jenis Exact | "
                    "Berat Exact | Berat (±0.1 kg) | Avg Input Tokens | "
                    "Avg Output Tokens | Latensi p95 (dtk) |"
                ),
                "|---|---|---|---|---|---|---|---|---|---|",
            ]
        )

        for r in runs:
            strat = r.get("strategy", "ocr_text")
            split = r.get("split", "dev").capitalize()
            m = r.get("metrics", {})
            n_gold = m.get("n_gold", 0)
            d_pct = m.get("tanggal_exact_rate", 0.0) * 100
            n_pct = m.get("nasabah_exact_rate", 0.0) * 100
            t_pct = m.get("waste_type_exact_rate", 0.0) * 100
            w_pct = m.get("weight_exact_rate", 0.0) * 100
            w01_pct = m.get("weight_within_01_rate", 0.0) * 100
            lines.append(
                f"| `{strat}` | {split} | "
                f"{d_pct:.1f}% ({m.get('n_tanggal_exact', 0)}/{n_gold}) | "
                f"{n_pct:.1f}% ({m.get('n_nasabah_exact', 0)}/{n_gold}) | "
                f"{t_pct:.1f}% ({m.get('n_waste_type_exact', 0)}/{n_gold}) | "
                f"{w_pct:.1f}% ({m.get('n_weight_exact', 0)}/{n_gold}) | "
                f"{w01_pct:.1f}% ({m.get('n_weight_within_01', 0)}/{n_gold}) | "
                f"{m.get('avg_prompt_tokens', 0.0):.0f} | "
                f"{m.get('avg_completion_tokens', 0.0):.0f} | "
                f"{m.get('latency_p95_s', 0.0):.2f} |"
            )

        first_run = runs[0]
        first_metrics = first_run.get("metrics", {})
        t_auto_val = first_metrics.get("t_auto", 0.92)
        t_conf_val = first_metrics.get("t_confirm", 0.60)
        lines.extend(
            [
                "",
                "## 3. Metadata and Provenance",
                "",
                f"- **Prompt Version:** `{first_run.get('prompt_version', 'extract-v3')}`",
                f"- **Schema Version:** `{first_run.get('schema_version', 'raw-v3')}`",
                f"- **Thresholds Evaluated:** `T_AUTO = {t_auto_val}`, `T_CONFIRM = {t_conf_val}`",
                (
                    "- **Data Provenance:** 100% synthetic handwritten ledger pages "
                    "(`eval/gold/synthetic/p001.jpg` to `p004.jpg`, 4 pages, 39 rows total: "
                    "3 dev pages with 29 rows, 1 test page with 10 rows)."
                ),
                "",
            ]
        )

        out_path = Path(options["out"])
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(lines), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Wrote evaluation summary report to {out_path}"))
