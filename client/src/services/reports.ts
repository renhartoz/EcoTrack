import { http } from "./http";
import type { ImpactReport } from "@/types/reports";

export async function getImpactReport(month?: string): Promise<ImpactReport> {
  const query = month ? `?month=${encodeURIComponent(month)}` : "";
  return http.get<ImpactReport>(`/api/reports/impact/${query}`);
}
