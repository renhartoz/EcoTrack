import { http } from "./http";
import type { DashboardSummary } from "@/types/dashboard";

export interface DashboardParams {
  from?: string;
  to?: string;
}

export async function getDashboardSummary(
  params?: DashboardParams,
): Promise<DashboardSummary> {
  const query = new URLSearchParams();
  if (params?.from) {
    query.set("from", params.from);
  }
  if (params?.to) {
    query.set("to", params.to);
  }
  const queryString = query.toString();
  const url = queryString
    ? `/api/dashboard/summary/?${queryString}`
    : "/api/dashboard/summary/";
  return http.get<DashboardSummary>(url);
}
