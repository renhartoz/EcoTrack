export interface EvidenceCropStyle {
  isValid: boolean;
  backgroundPosition: string;
  backgroundSize: string;
  startY?: number;
  endY?: number;
}

export function calculateEvidenceCrop(
  yMin: number | null | undefined,
  yMax: number | null | undefined,
  padding = 0.01,
): EvidenceCropStyle {
  if (
    yMin === null ||
    yMin === undefined ||
    yMax === null ||
    yMax === undefined ||
    Number.isNaN(yMin) ||
    Number.isNaN(yMax) ||
    yMin >= yMax ||
    yMin < 0 ||
    yMax > 1
  ) {
    return {
      isValid: false,
      backgroundPosition: "center",
      backgroundSize: "contain",
    };
  }

  const startY = Math.max(0, yMin - padding);
  const endY = Math.min(1, yMax + padding);
  const sliceHeight = endY - startY;

  if (sliceHeight <= 0) {
    return {
      isValid: false,
      backgroundPosition: "center",
      backgroundSize: "contain",
    };
  }

  const heightPercent = (1 / sliceHeight) * 100;
  const posYPercent = sliceHeight >= 1 ? 0 : (startY / (1 - sliceHeight)) * 100;

  return {
    isValid: true,
    startY,
    endY,
    backgroundPosition: `center ${posYPercent.toFixed(4)}%`,
    backgroundSize: `100% ${heightPercent.toFixed(4)}%`,
  };
}
