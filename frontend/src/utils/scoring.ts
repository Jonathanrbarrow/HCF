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

export const computeComfortScoreClient = (
  noise: number | null,
  canopyPct: number | null,
  heat: number | null,
  safetyScore: number | null,
  wNoise: number,
  wCanopy: number,
  wHeat: number,
  wSafety: number
): number => {
  const pNoise = computeNoisePenalty(noise);
  const pCanopy = computeCanopyPenalty(canopyPct);
  const pHeat = computeHeatPenalty(heat);
  const pSafety = computeSafetyPenalty(safetyScore);

  const totalWeight = wNoise + wCanopy + wHeat + wSafety;
  if (totalWeight === 0) return 100;

  const wn = wNoise / totalWeight;
  const wc = wCanopy / totalWeight;
  const wh = wHeat / totalWeight;
  const ws = wSafety / totalWeight;

  const totalPenalty = (wn * pNoise + wc * pCanopy + wh * pHeat + ws * pSafety) * 100.0;
  return Math.round(Math.max(0, Math.min(100, 100 - totalPenalty)));
};
