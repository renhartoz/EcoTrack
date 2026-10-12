import { useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Calendar,
  CheckCircle2,
  Clock,
  Layers,
  Scale,
  Sparkles,
  Users,
} from "lucide-react";
import { formatWeight } from "@/lib/format";
import { UI_STRINGS } from "@/lib/strings.id";
import { getDashboardSummary } from "@/services/dashboard";

export function DashboardPage() {
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [appliedParams, setAppliedParams] = useState<{
    from?: string;
    to?: string;
  }>({});

  const {
    data: summary,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ["dashboard-summary", appliedParams],
    queryFn: () => getDashboardSummary(appliedParams),
  });

  function handleFilterSubmit(e: FormEvent) {
    e.preventDefault();
    setAppliedParams({
      from: fromDate || undefined,
      to: toDate || undefined,
    });
  }

  function handleResetFilter() {
    setFromDate("");
    setToDate("");
    setAppliedParams({});
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-rule pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-ink">
            {UI_STRINGS.navDashboard}
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Pengelolaan sampah non-organik (Pasar Tradisional, UMKM Kuliner,
            Rumah Tangga) dan estimasi emisi.
          </p>
        </div>

        <form
          onSubmit={handleFilterSubmit}
          className="flex flex-wrap items-center gap-2"
        >
          <div className="flex items-center gap-1.5">
            <label htmlFor="dashboard-from" className="sr-only">
              {UI_STRINGS.filterFrom}
            </label>
            <input
              id="dashboard-from"
              type="date"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              className="min-h-[44px] rounded-sm border border-input-border bg-paper px-2.5 py-1.5 text-xs text-ink outline-none focus-visible:ring-2 focus-visible:ring-sprout"
            />
            <span className="text-xs text-muted-foreground">-</span>
            <label htmlFor="dashboard-to" className="sr-only">
              {UI_STRINGS.filterTo}
            </label>
            <input
              id="dashboard-to"
              type="date"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              className="min-h-[44px] rounded-sm border border-input-border bg-paper px-2.5 py-1.5 text-xs text-ink outline-none focus-visible:ring-2 focus-visible:ring-sprout"
            />
          </div>
          <button
            type="submit"
            className="flex min-h-[44px] items-center gap-1.5 rounded-sm bg-sprout px-3 py-1.5 text-xs font-medium text-white transition-opacity hover:opacity-90 focus-visible:ring-2 focus-visible:ring-sprout outline-none"
          >
            <Calendar className="h-3.5 w-3.5" />
            <span>Terapkan</span>
          </button>
          {(appliedParams.from || appliedParams.to) && (
            <button
              type="button"
              onClick={handleResetFilter}
              className="min-h-[44px] rounded-sm border border-rule px-3 py-1.5 text-xs font-medium text-ink transition-colors hover:bg-muted focus-visible:ring-2 focus-visible:ring-sprout outline-none"
            >
              Reset
            </button>
          )}
        </form>
      </div>

      {isLoading && (
        <div className="rounded-sm border border-rule bg-paper p-8 text-center text-sm text-muted-foreground">
          {UI_STRINGS.loading}
        </div>
      )}

      {isError && (
        <div
          role="alert"
          className="flex items-center gap-2 rounded-sm border border-brick bg-paper p-4 text-sm text-brick"
        >
          <AlertCircle className="h-5 w-5 shrink-0" />
          <span>{error?.message || UI_STRINGS.unknownError}</span>
        </div>
      )}

      {summary && (
        <div className="space-y-6">
          {summary.is_demo && (
            <output
              id="demo-banner"
              className="block flex items-start gap-3 rounded-sm border border-amber/60 bg-paper p-4 text-ink"
            >
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber" />
              <div>
                <span className="font-bold text-sm text-amber">
                  {UI_STRINGS.demoBannerTitle}
                </span>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {UI_STRINGS.demoBannerText}
                </p>
              </div>
            </output>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-sm border border-rule bg-paper p-4">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>{UI_STRINGS.dashboardWeightLabel}</span>
                <Scale className="h-4 w-4 text-sprout" />
              </div>
              <div className="mt-2 text-2xl font-bold tracking-tight text-ink tabular-nums">
                {formatWeight(summary.totals.weight_kg)}
              </div>
              <div className="mt-1 text-[11px] text-muted-foreground">
                Periode: {summary.period.from} s/d {summary.period.to}
              </div>
            </div>

            <div className="rounded-sm border border-rule bg-paper p-4">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>{UI_STRINGS.dashboardCo2eLabel}</span>
                <Sparkles className="h-4 w-4 text-sprout" />
              </div>
              <div className="mt-2 text-2xl font-bold tracking-tight text-sprout tabular-nums">
                {summary.totals.co2e_kg}{" "}
                <span className="text-sm font-normal text-muted-foreground">
                  kg CO2e
                </span>
              </div>
              <div className="mt-1 text-[11px] text-muted-foreground">
                Estimasi berbasis faktor konversi KLHK
              </div>
            </div>

            <div className="rounded-sm border border-rule bg-paper p-4">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>{UI_STRINGS.dashboardDepositsLabel}</span>
                <Layers className="h-4 w-4 text-ink" />
              </div>
              <div className="mt-2 text-2xl font-bold tracking-tight text-ink tabular-nums">
                {summary.totals.deposit_count}
              </div>
              <div className="mt-1 text-[11px] text-muted-foreground">
                Transaksi tercatat
              </div>
            </div>

            <div className="rounded-sm border border-rule bg-paper p-4">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>{UI_STRINGS.dashboardNasabahLabel}</span>
                <Users className="h-4 w-4 text-ink" />
              </div>
              <div className="mt-2 text-2xl font-bold tracking-tight text-ink tabular-nums">
                {summary.totals.active_nasabah}
              </div>
              <div className="mt-1 text-[11px] text-muted-foreground">
                Nasabah aktif berpartisipasi
              </div>
            </div>
          </div>

          <div className="rounded-sm border border-rule bg-paper p-4">
            <div className="mb-3 flex items-center justify-between border-b border-rule pb-2">
              <div className="flex items-center gap-2 font-bold text-sm text-ink">
                <Activity className="h-4 w-4 text-sprout" />
                <span>{UI_STRINGS.pipelineTitle}</span>
              </div>
              {summary.pipeline.pending_rows > 0 && (
                <Link
                  to="/uploads"
                  className="flex min-h-[44px] items-center gap-1 text-xs font-semibold text-sprout hover:underline focus-visible:ring-2 focus-visible:ring-sprout outline-none"
                >
                  <span>Tinjau baris tertunda</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              )}
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div className="rounded-sm border border-rule p-3">
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <CheckCircle2 className="h-3.5 w-3.5 text-sprout" />
                  <span>{UI_STRINGS.pipelineAutoRate}</span>
                </div>
                <div className="mt-1 text-xl font-bold text-sprout tabular-nums">
                  {Math.round(summary.pipeline.auto_rate * 100)}%
                </div>
              </div>

              <div className="rounded-sm border border-rule p-3">
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Clock className="h-3.5 w-3.5 text-amber" />
                  <span>{UI_STRINGS.pipelineCorrectionRate}</span>
                </div>
                <div className="mt-1 text-xl font-bold text-amber tabular-nums">
                  {Math.round(summary.pipeline.correction_rate * 100)}%
                </div>
              </div>

              <div className="rounded-sm border border-rule p-3">
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <AlertTriangle className="h-3.5 w-3.5 text-brick" />
                  <span>{UI_STRINGS.pipelinePending}</span>
                </div>
                <div className="mt-1 text-xl font-bold text-brick tabular-nums">
                  {summary.pipeline.pending_rows}
                </div>
              </div>
            </div>
          </div>

          {summary.coverage.types_missing_factor.length > 0 && (
            <div className="rounded-sm border border-rule bg-paper p-3 text-xs text-muted-foreground">
              <span className="font-semibold text-ink">
                {UI_STRINGS.missingFactorNotice}
              </span>{" "}
              {summary.coverage.types_missing_factor.join(", ")}.
            </div>
          )}

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div className="rounded-sm border border-rule bg-paper">
              <div className="border-b border-rule p-3 font-bold text-sm text-ink">
                {UI_STRINGS.byTypeTitle}
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-rule bg-muted/20 text-muted-foreground">
                    <tr>
                      <th className="p-3">Jenis</th>
                      <th className="p-3 text-right">Berat (kg)</th>
                      <th className="p-3 text-right">CO2e (estimasi)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-rule">
                    {summary.by_type.map((item) => (
                      <tr
                        key={item.waste_type}
                        className="transition-colors hover:bg-muted/10"
                      >
                        <td className="p-3 font-medium text-ink">
                          {item.name_id}
                        </td>
                        <td className="p-3 text-right font-mono text-ink tabular-nums">
                          {formatWeight(item.weight_kg)}
                        </td>
                        <td className="p-3 text-right font-mono text-ink tabular-nums">
                          {item.co2e_kg ? `${item.co2e_kg} kg` : "-"}
                        </td>
                      </tr>
                    ))}
                    {summary.by_type.length === 0 && (
                      <tr>
                        <td
                          colSpan={3}
                          className="p-4 text-center text-muted-foreground"
                        >
                          Belum ada data pada periode ini.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="rounded-sm border border-rule bg-paper">
              <div className="border-b border-rule p-3 font-bold text-sm text-ink">
                {UI_STRINGS.monthlyTitle}
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-rule bg-muted/20 text-muted-foreground">
                    <tr>
                      <th className="p-3">Bulan</th>
                      <th className="p-3 text-right">Berat (kg)</th>
                      <th className="p-3 text-right">CO2e (kg)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-rule">
                    {summary.monthly.map((m) => (
                      <tr
                        key={m.month}
                        className="transition-colors hover:bg-muted/10"
                      >
                        <td className="p-3 font-medium text-ink">{m.month}</td>
                        <td className="p-3 text-right font-mono text-ink tabular-nums">
                          {formatWeight(m.weight_kg)}
                        </td>
                        <td className="p-3 text-right font-mono text-ink tabular-nums">
                          {m.co2e_kg}
                        </td>
                      </tr>
                    ))}
                    {summary.monthly.length === 0 && (
                      <tr>
                        <td
                          colSpan={3}
                          className="p-4 text-center text-muted-foreground"
                        >
                          Belum ada data bulanan.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
