export interface WasteType {
  id: string;
  code: string;
  name_id: string;
  emission_factor_kgco2e_per_kg: string | null;
  is_active: boolean;
}
