export type UploadSourceType = "image" | "text";
export type UploadStatus = "processing" | "ready" | "failed";
export type RowStatus = "pending" | "saved" | "rejected" | "reverted";
export type RowRoute = "auto" | "confirm" | "manual" | null;

export interface UploadPageMeta {
  bank_name_raw: string | null;
  page_date_raw: string | null;
  has_total_row: boolean;
}

export interface UploadCounts {
  auto: number;
  confirm: number;
  manual: number;
  saved: number;
  pending: number;
}

export interface RawRowFields {
  tanggal: string | null;
  nama: string | null;
  jenis: string | null;
  berat: string | null;
  satuan: string | null;
  evidence_text: string;
}

export interface NormalizedRowFields {
  tanggal: string | null;
  nasabah_id: number | null;
  waste_type_id: number | null;
  weight_kg: string | null;
}

export interface RowEvidence {
  y_min: number | null;
  y_max: number | null;
}

export interface RowFlag {
  code: string;
  severity: "hard" | "soft";
}

export interface ExtractedRow {
  id: number;
  row_index: number;
  status: RowStatus;
  route: RowRoute;
  score: number | null;
  flags: RowFlag[];
  raw: RawRowFields;
  normalized: NormalizedRowFields;
  evidence: RowEvidence;
  human_edited: boolean;
  deposit_id: number | null;
}

export interface UploadDetail {
  id: number;
  source_type: UploadSourceType;
  status: UploadStatus;
  source_sha256: string | null;
  created_at: string;
  processing_started_at: string | null;
  error_code: string | null;
  error_message: string | null;
  page: UploadPageMeta | null;
  counts: UploadCounts;
  rows: ExtractedRow[];
}

export interface UploadListItem {
  id: number;
  source_type: UploadSourceType;
  status: UploadStatus;
  created_at: string;
  error_code: string | null;
  row_count: number;
}
