export interface ImpactReportPeriod {
  month: string;
}

export interface ImpactReportByType {
  waste_type: string;
  name_id: string;
  weight_kg: string;
  co2e_kg: string | null;
}

export interface ImpactReportFigures {
  weight_kg: string;
  co2e_kg: string;
  deposit_count: number;
  active_nasabah: number;
  by_type: ImpactReportByType[];
}

export interface ImpactReportMethodologyFactor {
  waste_type: string;
  factor: string;
  source: string | null;
  note: string | null;
}

export interface ImpactReportNarrative {
  text: string;
  source: string;
  verified: boolean;
}

export interface ImpactReportCoverage {
  types_missing_factor: string[];
}

export interface ImpactReport {
  period: ImpactReportPeriod;
  figures: ImpactReportFigures;
  methodology: {
    factors: ImpactReportMethodologyFactor[];
  };
  narrative: ImpactReportNarrative;
  coverage: ImpactReportCoverage;
  is_demo: boolean;
}
