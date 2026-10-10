import { http } from "./http";
import type { ConfirmAllResponse, RowUpdatePayload } from "@/types/rows";
import type { ExtractedRow } from "@/types/uploads";

export async function updateRow(
  id: number | string,
  payload: RowUpdatePayload,
): Promise<ExtractedRow> {
  return http.patch<ExtractedRow>(`/api/rows/${id}/`, payload);
}

export async function confirmRow(id: number | string): Promise<ExtractedRow> {
  return http.post<ExtractedRow>(`/api/rows/${id}/confirm/`, {});
}

export async function rejectRow(id: number | string): Promise<ExtractedRow> {
  return http.post<ExtractedRow>(`/api/rows/${id}/reject/`, {});
}

export async function confirmAllRows(
  uploadId: number | string,
): Promise<ConfirmAllResponse> {
  return http.post<ConfirmAllResponse>(
    `/api/uploads/${uploadId}/confirm-all/`,
    {},
  );
}
