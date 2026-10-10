import { http } from "./http";
import type { PaginatedResponse } from "@/types/api";
import type {
  Nasabah,
  NasabahCreatePayload,
  NasabahUpdatePayload,
} from "@/types/nasabah";

export async function getNasabahList(params?: {
  q?: string;
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<Nasabah>> {
  const searchParams = new URLSearchParams();
  if (params?.q) {
    searchParams.set("q", params.q);
  }
  if (params?.page) {
    searchParams.set("page", params.page.toString());
  }
  if (params?.page_size) {
    searchParams.set("page_size", params.page_size.toString());
  }

  const query = searchParams.toString();
  const url = query ? `/api/nasabah/?${query}` : "/api/nasabah/";
  return http.get<PaginatedResponse<Nasabah>>(url);
}

export async function createNasabah(
  payload: NasabahCreatePayload,
): Promise<Nasabah> {
  return http.post<Nasabah>("/api/nasabah/", payload);
}

export async function getNasabahDetail(id: number | string): Promise<Nasabah> {
  return http.get<Nasabah>(`/api/nasabah/${id}/`);
}

export async function updateNasabah(
  id: number | string,
  payload: NasabahUpdatePayload,
): Promise<Nasabah> {
  return http.patch<Nasabah>(`/api/nasabah/${id}/`, payload);
}
