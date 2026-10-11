export interface RowUpdatePayload {
  tanggal?: string | null;
  nasabah_id?: string | null;
  waste_type_id?: string | null;
  weight_kg?: string | null;
}

export interface ConfirmAllResponse {
  confirmed: number;
  skipped: number;
}
