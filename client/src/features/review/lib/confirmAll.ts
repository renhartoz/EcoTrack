import type { ExtractedRow } from "@/types/uploads";

export function isRowEligibleForConfirmAll(row: ExtractedRow): boolean {
  if (row.status !== "pending") {
    return false;
  }
  if (row.route !== "confirm") {
    return false;
  }
  const hasIneligibleFlag = row.flags.some(
    (flag) =>
      flag.severity === "hard" ||
      flag.code === "DUPLICATE_IN_PAGE" ||
      flag.code === "DUPLICATE_IN_DB",
  );
  return !hasIneligibleFlag;
}

export function filterEligibleForConfirmAll(
  rows: ExtractedRow[],
): ExtractedRow[] {
  return rows.filter(isRowEligibleForConfirmAll);
}
