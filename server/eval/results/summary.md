# EcoTrack Evaluation Report

## 1. Strategy and Split Comparison

| Strategi | Split | n Row | Exact (%) | Auto Precision (%) | Auto Coverage (%) | Unsafe Auto (%) | Latensi p50 (dtk) |
|---|---|---|---|---|---|---|---|
| `ocr_text` | Dev | 29 | 96.5% (28/29) | 100.0% (15/15) | 51.7% (15/29) | 0.0% (0/7) | 10.59 |
| `ocr_text` | Test | 10 | 100.0% (10/10) | 100.0% (4/4) | 40.0% (4/10) | 0.0% (0/3) | 10.38 |
| `vision` | Dev | 29 | 96.5% (28/29) | 100.0% (16/16) | 55.2% (16/29) | 14.3% (1/7) | 5.18 |
| `hybrid` | Dev | 29 | 96.5% (28/29) | 100.0% (15/15) | 51.7% (15/29) | 0.0% (0/7) | 13.58 |

## 2. Per-Field Accuracy and Token Usage

| Strategi | Split | Tanggal Exact | Nasabah Exact | Jenis Exact | Berat Exact | Berat (±0.1 kg) | Avg Input Tokens | Avg Output Tokens | Latensi p95 (dtk) |
|---|---|---|---|---|---|---|---|---|---|
| `ocr_text` | Dev | 100.0% (29/29) | 100.0% (29/29) | 100.0% (29/29) | 96.5% (28/29) | 96.5% (28/29) | 910 | 788 | 12.90 |
| `ocr_text` | Test | 100.0% (10/10) | 100.0% (10/10) | 100.0% (10/10) | 100.0% (10/10) | 100.0% (10/10) | 896 | 781 | 10.38 |
| `vision` | Dev | 100.0% (29/29) | 100.0% (29/29) | 100.0% (29/29) | 96.5% (28/29) | 96.5% (28/29) | 2210 | 963 | 5.31 |
| `hybrid` | Dev | 100.0% (29/29) | 100.0% (29/29) | 100.0% (29/29) | 96.5% (28/29) | 96.5% (28/29) | 2210 | 963 | 16.05 |

## 3. Metadata and Provenance

- **Prompt Version:** `extract-v3`
- **Schema Version:** `raw-v3`
- **Thresholds Evaluated:** `T_AUTO = 0.92`, `T_CONFIRM = 0.6`
- **Data Provenance:** 100% synthetic handwritten ledger pages (`eval/gold/synthetic/p001.jpg` to `p004.jpg`, 4 pages, 39 rows total: 3 dev pages with 29 rows, 1 test page with 10 rows).
