export function formatWeight(
  weight: string | number | null | undefined,
  includeUnit = true,
): string {
  if (weight === null || weight === undefined || weight === "") {
    return "-";
  }

  const num = typeof weight === "number" ? weight : parseFloat(weight);
  if (Number.isNaN(num)) {
    return "-";
  }

  const formatted = num.toLocaleString("id-ID", {
    minimumFractionDigits: 3,
    maximumFractionDigits: 3,
  });

  return includeUnit ? `${formatted} kg` : formatted;
}

export function formatDate(dateString: string | null | undefined): string {
  if (!dateString) {
    return "-";
  }
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) {
    return dateString;
  }
  return date.toLocaleDateString("id-ID", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}
