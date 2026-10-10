import { http } from "./http";
import type { WasteType } from "@/types/wasteTypes";

export async function getWasteTypes(): Promise<WasteType[]> {
  return http.get<WasteType[]>("/api/waste-types/");
}
