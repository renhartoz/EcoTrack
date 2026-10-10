export interface Nasabah {
  id: number;
  name: string;
  normalized_name: string;
  is_active: boolean;
  created_at: string;
}

export interface NasabahCreatePayload {
  name: string;
}

export interface NasabahUpdatePayload {
  name?: string;
  is_active?: boolean;
}
