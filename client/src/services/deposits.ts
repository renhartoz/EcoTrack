import { http } from "./http";
import type { PaginatedResponse } from "@/types/api";
import type {
  Deposit,
  DepositCreatePayload,
  DepositFilterParams,
  DepositUpdatePayload,
} from "@/types/deposits";

export async function getDeposits(
  params?: DepositFilterParams,
): Promise<PaginatedResponse<Deposit>> {
  const searchParams = new URLSearchParams();
  if (params?.from) {
    searchParams.set("from", params.from);
  }
  if (params?.to) {
    searchParams.set("to", params.to);
  }
  if (params?.nasabah) {
    searchParams.set("nasabah", params.nasabah.toString());
  }
  if (params?.waste_type) {
    searchParams.set("waste_type", params.waste_type.toString());
  }
  if (params?.source) {
    searchParams.set("source", params.source);
  }
  if (params?.page) {
    searchParams.set("page", params.page.toString());
  }
  if (params?.page_size) {
    searchParams.set("page_size", params.page_size.toString());
  }

  const query = searchParams.toString();
  const url = query ? `/api/deposits/?${query}` : "/api/deposits/";
  return http.get<PaginatedResponse<Deposit>>(url);
}

export async function createDeposit(
  payload: DepositCreatePayload,
): Promise<Deposit> {
  return http.post<Deposit>("/api/deposits/", payload);
}

export async function updateDeposit(
  id: number | string,
  payload: DepositUpdatePayload,
): Promise<Deposit> {
  return http.patch<Deposit>(`/api/deposits/${id}/`, payload);
}

export async function deleteDeposit(
  id: number | string,
): Promise<{ status: string; deleted_at: string }> {
  return http.delete<{ status: string; deleted_at: string }>(
    `/api/deposits/${id}/`,
  );
}

export async function exportDepositsCsv(
  params?: DepositFilterParams,
): Promise<Blob> {
  const searchParams = new URLSearchParams();
  if (params?.from) {
    searchParams.set("from", params.from);
  }
  if (params?.to) {
    searchParams.set("to", params.to);
  }
  if (params?.nasabah) {
    searchParams.set("nasabah", params.nasabah.toString());
  }
  if (params?.waste_type) {
    searchParams.set("waste_type", params.waste_type.toString());
  }
  if (params?.source) {
    searchParams.set("source", params.source);
  }

  const query = searchParams.toString();
  const url = query
    ? `/api/deposits/export/?${query}`
    : "/api/deposits/export/";

  const response = await fetch(url, {
    method: "GET",
    credentials: "include",
    headers: {
      Accept: "text/csv",
    },
  });

  if (!response.ok) {
    throw new Error("Failed to export deposits CSV");
  }

  return response.blob();
}
