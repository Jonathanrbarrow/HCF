const computeNoisePenalty = (noise: number | null): number => {
  if (noise === null) return 5.0 / 35.0; // corresponding to 50 dBA: (50-45)/35 = 0.1428
  if (noise <= 45.0) return 0.0;
  if (noise >= 80.0) return 1.0;
  return (noise - 45.0) / (80.0 - 45.0);
};

const computeCanopyPenalty = (canopyPct: number | null): number => {
  const pct = canopyPct !== null ? canopyPct : 20.0; // Default
  return 1.0 - (pct / 100.0);
};

const computeHeatPenalty = (heat: number | null): number => {
  const h = heat !== null ? heat : 85.0; // Default
  if (h <= 75.0) return 0.0;
  if (h >= 110.0) return 1.0;
  return (h - 75.0) / (110.0 - 75.0);
};

const computeSafetyPenalty = (safetyScore: number | null): number => {
  const s = safetyScore !== null ? safetyScore : 100.0; // Default
  return 1.0 - (s / 100.0);
};

const computeTrafficPenalty = (aadt: number | null): number => {
  if (aadt === null) return 0.0;
  if (aadt <= 1000) return 0.0;
  if (aadt >= 30000) return 1.0;
  return (aadt - 1000) / (30000 - 1000);
};

/**
 * Compute comfort score client-side with user-adjustable weights.
 *
 * Any factor with a weight of 0 is excluded. When traffic data
 * is null, its weight is automatically redistributed.
 */
export const computeComfortScoreClient = (
  noise: number | null,
  canopyPct: number | null,
  heat: number | null,
  safetyScore: number | null,
  wNoise: number,
  wCanopy: number,
  wHeat: number,
  wSafety: number,
  trafficVolume: number | null = null,
  wTraffic: number = 0,
): number => {
  // Build penalty/weight pairs — only include non-null factors with non-zero weight
  const factors: { penalty: number; weight: number }[] = [];

  if (wNoise > 0) factors.push({ penalty: computeNoisePenalty(noise), weight: wNoise });
  if (wCanopy > 0) factors.push({ penalty: computeCanopyPenalty(canopyPct), weight: wCanopy });
  if (wHeat > 0) factors.push({ penalty: computeHeatPenalty(heat), weight: wHeat });
  if (wSafety > 0) factors.push({ penalty: computeSafetyPenalty(safetyScore), weight: wSafety });
  if (wTraffic > 0 && trafficVolume !== null) {
    factors.push({ penalty: computeTrafficPenalty(trafficVolume), weight: wTraffic });
  }

  const totalWeight = factors.reduce((sum, f) => sum + f.weight, 0);
  if (totalWeight === 0) return 100;

  const totalPenalty = factors.reduce(
    (sum, f) => sum + (f.weight / totalWeight) * f.penalty,
    0,
  ) * 100.0;

  return Math.round(Math.max(0, Math.min(100, 100 - totalPenalty)));
};
