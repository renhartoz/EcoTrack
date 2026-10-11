export interface DashboardTotals {
  weight_kg: string;
  co2e_kg: string;
  deposit_count: number;
  active_nasabah: number;
}

export interface WasteTypeBreakdown {
  waste_type: string;
  name_id: string;
  weight_kg: string;
  co2e_kg: string | null;
}

export interface MonthlyTrend {
  month: string;
  weight_kg: string;
  co2e_kg: string;
}

export interface PipelineHealth {
  pending_rows: number;
  auto_rate: number;
  correction_rate: number;
}

export interface DashboardCoverage {
  types_missing_factor: string[];
}

export interface DashboardPeriod {
  from: string;
  to: string;
}

export interface DashboardSummary {
  period: DashboardPeriod;
  totals: DashboardTotals;
  by_type: WasteTypeBreakdown[];
  monthly: MonthlyTrend[];
  pipeline: PipelineHealth;
  coverage: DashboardCoverage;
  is_demo: boolean;
}
