import { http } from "./http";
import type { PaginatedResponse } from "@/types/api";
import type { UploadDetail, UploadListItem } from "@/types/uploads";

export async function createImageUpload(
  imageBlob: Blob,
  sourceSha256?: string,
  filename = "ledger.jpg",
): Promise<UploadDetail> {
  const file =
    imageBlob instanceof File
      ? imageBlob
      : new File([imageBlob], filename, {
          type: imageBlob.type || "image/jpeg",
        });
  const formData = new FormData();
  formData.append("image", file, filename);
  if (sourceSha256) {
    formData.append("source_sha256", sourceSha256);
  }
  return http.post<UploadDetail>("/api/uploads/", formData);
}

export async function createTextUpload(text: string): Promise<UploadDetail> {
  return http.post<UploadDetail>("/api/uploads/text/", { text });
}

export async function getUploads(
  page = 1,
  pageSize = 20,
): Promise<PaginatedResponse<UploadListItem>> {
  return http.get<PaginatedResponse<UploadListItem>>(
    `/api/uploads/?page=${page}&page_size=${pageSize}`,
  );
}

export async function getUploadDetail(
  id: number | string,
): Promise<UploadDetail> {
  return http.get<UploadDetail>(`/api/uploads/${id}/`);
}

export async function retryUpload(id: number | string): Promise<UploadDetail> {
  return http.post<UploadDetail>(`/api/uploads/${id}/retry/`, {});
}

export function getUploadImageUrl(id: number | string): string {
  return `/api/uploads/${id}/image/`;
}
