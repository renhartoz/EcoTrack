import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  Calendar,
  CheckCircle2,
  FileCheck,
  Info,
  Printer,
  Scale,
  Sparkles,
  TreePine,
  Users,
} from "lucide-react";
import { formatWeight } from "@/lib/format";
import { UI_STRINGS } from "@/lib/strings.id";
import { getImpactReport } from "@/services/reports";
import { useAuth } from "@/context/AuthContext";

const CURRENT_YEAR = new Date().getFullYear();
const PAST_MONTHS = [
  `${CURRENT_YEAR}-10`,
  `${CURRENT_YEAR}-09`,
  `${CURRENT_YEAR}-08`,
  `${CURRENT_YEAR}-07`,
];

export function ReportsPage() {
  const { user } = useAuth();

  const [selectedMonth, setSelectedMonth] = useState(() => {
    const now = new Date();
    const y = now.getFullYear();
    const m = String(now.getMonth() + 1).padStart(2, "0");
    return `${y}-${m}`;
  });

  const {
    data: report,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ["impact-report", selectedMonth],
    queryFn: () => getImpactReport(selectedMonth),
  });

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-col gap-4 border-b border-rule pb-4 print:hidden sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-ink">
            {UI_STRINGS.navReports}
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Kalkulasi otomatis dampak lingkungan dan reduksi emisi karbon
            berbasis data setoran.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 rounded-sm border border-input-border bg-paper px-3 py-1 text-xs">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            <input
              type="month"
              aria-label="Pilih Bulan Laporan"
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(e.target.value)}
              className="min-h-[44px] bg-transparent font-medium text-ink outline-none"
            />
          </div>

          <button
            type="button"
            onClick={handlePrint}
            disabled={!report || report.figures.deposit_count === 0}
            className="flex min-h-[44px] items-center gap-2 rounded-sm bg-sprout px-4 py-2 font-medium text-xs text-white transition-opacity hover:opacity-90 disabled:opacity-50 outline-none focus-visible:ring-2 focus-visible:ring-sprout"
          >
            <Printer className="h-4 w-4" />
            <span>Cetak Laporan / PDF</span>
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 print:hidden">
        <span className="text-xs text-muted-foreground">Pilihan Cepat:</span>
        {PAST_MONTHS.map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setSelectedMonth(m)}
            className={`min-h-[36px] rounded-sm border px-3 py-1 text-xs font-medium transition-colors outline-none focus-visible:ring-2 focus-visible:ring-sprout ${
              selectedMonth === m
                ? "border-sprout bg-sprout/10 text-sprout"
                : "border-rule bg-paper text-muted-foreground hover:bg-muted"
            }`}
          >
            {m}
          </button>
        ))}
      </div>

      <div className="rounded-sm border border-rule bg-paper p-4 print:hidden">
        <div className="flex items-start gap-3 text-xs text-muted-foreground">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-sprout" />
          <p>
            <strong>Bagaimana laporan ini diisi?</strong> Laporan ini dihitung
            secara otomatis oleh sistem dari data setoran yang tersimpan di tab{" "}
            <strong>Setoran</strong> dan hasil persetujuan di tab{" "}
            <strong>Tinjau</strong>. Setiap kali ada penambahan atau pengubahan
            setoran, angka dan estimasi emisi langsung diperbarui secara
            realtime.
          </p>
        </div>
      </div>

      {isLoading && (
        <div className="rounded-sm border border-rule p-8 text-center text-sm text-muted-foreground">
          {UI_STRINGS.loading}
        </div>
      )}

      {isError && (
        <div
          role="alert"
          className="rounded-sm border border-brick bg-paper p-4 text-sm text-brick"
        >
          {error instanceof Error ? error.message : UI_STRINGS.unknownError}
        </div>
      )}

      {report && (
        <div className="space-y-6 print:space-y-4">
          {report.is_demo && (
            <output className="block flex items-start gap-3 rounded-sm border border-amber/60 bg-paper p-3 text-ink print:border-rule">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber" />
              <div className="text-xs">
                <span className="font-bold text-amber">
                  {UI_STRINGS.demoBannerTitle}
                </span>
                <p className="text-muted-foreground">
                  Laporan ini dibuat dari data simulasi percontohan.
                </p>
              </div>
            </output>
          )}

          <div className="rounded-sm border border-rule bg-paper p-6 print:border-none print:p-0">
            <div className="border-b border-rule pb-4 text-center sm:text-left">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h1 className="text-2xl font-bold tracking-tight text-ink">
                    Laporan Dampak Pengelolaan Sampah
                  </h1>
                  <p className="mt-1 font-medium text-sm text-sprout">
                    {user?.bank_sampah?.name || "Bank Sampah"}
                  </p>
                </div>
                <div className="mt-2 sm:mt-0 sm:text-right">
                  <span className="inline-block rounded-sm bg-muted px-2.5 py-1 font-mono text-xs font-semibold text-ink">
                    Periode: {report.period.month}
                  </span>
                </div>
              </div>
            </div>

            <div className="mt-6 rounded-sm border border-sprout/40 bg-sprout/5 p-4">
              <div className="mb-2 flex items-center justify-between">
                <div className="flex items-center gap-2 font-semibold text-xs text-sprout uppercase tracking-wider">
                  <Sparkles className="h-4 w-4" />
                  <span>Narasi Resmi Dampak Lingkungan</span>
                </div>
                {report.narrative.verified && (
                  <span className="inline-flex items-center gap-1 text-[11px] font-medium text-sprout">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    <span>Terverifikasi Deterministik</span>
                  </span>
                )}
              </div>
              <p className="text-sm leading-relaxed text-ink">
                {report.narrative.text}
              </p>
            </div>

            <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-sm border border-rule bg-paper p-4">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-xs font-medium">
                    Total Sampah Dikelola
                  </span>
                  <Scale className="h-4 w-4 text-sprout" />
                </div>
                <div className="mt-2 text-2xl font-bold tracking-tight text-ink tabular-nums">
                  {formatWeight(report.figures.weight_kg)}
                </div>
                <p className="mt-1 text-[11px] text-muted-foreground">
                  Timbangan terverifikasi
                </p>
              </div>

              <div className="rounded-sm border border-rule bg-paper p-4">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-xs font-medium">Pengurangan Emisi</span>
                  <TreePine className="h-4 w-4 text-sprout" />
                </div>
                <div className="mt-2 text-2xl font-bold tracking-tight text-sprout tabular-nums">
                  {formatWeight(report.figures.co2e_kg)} kg
                </div>
                <p className="mt-1 text-[11px] text-muted-foreground">
                  Estimasi avoided CO2e
                </p>
              </div>

              <div className="rounded-sm border border-rule bg-paper p-4">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-xs font-medium">Jumlah Setoran</span>
                  <FileCheck className="h-4 w-4 text-ink" />
                </div>
                <div className="mt-2 text-2xl font-bold tracking-tight text-ink tabular-nums">
                  {report.figures.deposit_count}
                </div>
                <p className="mt-1 text-[11px] text-muted-foreground">
                  Transaksi tercatat
                </p>
              </div>

              <div className="rounded-sm border border-rule bg-paper p-4">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-xs font-medium">Nasabah Aktif</span>
                  <Users className="h-4 w-4 text-amber" />
                </div>
                <div className="mt-2 text-2xl font-bold tracking-tight text-ink tabular-nums">
                  {report.figures.active_nasabah}
                </div>
                <p className="mt-1 text-[11px] text-muted-foreground">
                  Partisipan bulan ini
                </p>
              </div>
            </div>

            <div className="mt-6 space-y-3">
              <h3 className="font-bold text-sm text-ink">
                Rincian Berat dan Estimasi Emisi per Jenis Sampah
              </h3>
              {report.figures.by_type.length === 0 ? (
                <div className="rounded-sm border border-rule p-6 text-center text-xs text-muted-foreground">
                  Belum ada setoran pada periode ini.
                </div>
              ) : (
                <div className="overflow-x-auto rounded-sm border border-rule bg-paper">
                  <table className="w-full text-left text-sm">
                    <thead className="border-b border-rule bg-muted/40 text-xs font-semibold text-muted-foreground">
                      <tr>
                        <th className="p-3">Jenis Sampah</th>
                        <th className="p-3">Kode</th>
                        <th className="p-3 text-right">Berat Terkumpul</th>
                        <th className="p-3 text-right">
                          Estimasi Reduksi Emisi
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-rule">
                      {report.figures.by_type.map((item) => (
                        <tr key={item.waste_type} className="hover:bg-muted/10">
                          <td className="p-3 font-medium text-ink">
                            {item.name_id}
                          </td>
                          <td className="p-3 font-mono text-xs text-muted-foreground">
                            {item.waste_type}
                          </td>
                          <td className="p-3 text-right font-mono font-semibold text-ink tabular-nums">
                            {formatWeight(item.weight_kg)}
                          </td>
                          <td className="p-3 text-right font-mono font-semibold text-sprout tabular-nums">
                            {item.co2e_kg !== null
                              ? `${formatWeight(item.co2e_kg)} kg CO2e`
                              : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {report.coverage.types_missing_factor.length > 0 && (
              <div className="mt-4 rounded-sm border border-amber/40 bg-amber/5 p-3 text-xs text-ink">
                <span className="font-semibold text-amber">
                  Catatan Faktor Emisi:
                </span>{" "}
                Jenis sampah berikut belum memiliki faktor konversi emisi resmi
                sehingga belum disertakan dalam perhitungan total emisi CO2e:{" "}
                {report.coverage.types_missing_factor.join(", ")}.
              </div>
            )}

            <div className="mt-6 border-t border-rule pt-4 text-xs text-muted-foreground">
              <h4 className="font-semibold text-ink uppercase tracking-wider text-[11px]">
                Metodologi dan Sumber Konversi
              </h4>
              <p className="mt-1">
                Perhitungan pengurangan emisi gas rumah kaca menggunakan
                metodologi avoided emissions dari daur ulang sampah kering
                berdasar publikasi KLHK dan IPCC.
              </p>
              {report.methodology.factors.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {report.methodology.factors.map((f) => (
                    <span
                      key={f.waste_type}
                      className="rounded-sm border border-rule bg-paper px-2 py-0.5 text-[11px]"
                    >
                      <strong>{f.waste_type}</strong>: {f.factor} kg CO2e/kg{" "}
                      {f.source ? `(${f.source})` : ""}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
