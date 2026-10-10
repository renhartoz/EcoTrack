export interface RowUpdatePayload {
  tanggal?: string | null;
  nasabah_id?: number | null;
  waste_type_id?: number | null;
  weight_kg?: string | null;
}

export interface ConfirmAllResponse {
  confirmed: number;
  skipped: number;
}
