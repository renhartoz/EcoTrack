export type DepositSource = "auto" | "confirmed" | "manual";

export interface Deposit {
  id: number;
  nasabah: {
    id: number;
    name: string;
  };
  waste_type: {
    id: number;
    code: string;
    name_id: string;
  };
  weight_kg: string;
  deposit_date: string;
  source: DepositSource;
  upload_id: number | null;
  created_at: string;
}

export interface DepositCreatePayload {
  nasabah_id: number;
  waste_type_id: number;
  weight_kg: string;
  deposit_date: string;
}

export interface DepositUpdatePayload {
  weight_kg?: string;
  deposit_date?: string;
}

export interface DepositFilterParams {
  from?: string;
  to?: string;
  nasabah?: number;
  waste_type?: number;
  source?: DepositSource;
  page?: number;
  page_size?: number;
}
