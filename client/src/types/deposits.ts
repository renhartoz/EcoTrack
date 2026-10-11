export type DepositSource = "auto" | "confirmed" | "manual";

export interface Deposit {
  id: string;
  nasabah: {
    id: string;
    name: string;
  };
  waste_type: {
    id: string;
    code: string;
    name_id: string;
  };
  weight_kg: string;
  deposit_date: string;
  source: DepositSource;
  upload_id: string | null;
  created_at: string;
}

export interface DepositCreatePayload {
  nasabah_id: string;
  waste_type_id: string;
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
  nasabah?: string;
  waste_type?: string;
  source?: DepositSource;
  page?: number;
  page_size?: number;
}
