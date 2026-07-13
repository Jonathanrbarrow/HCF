"""
Scoring module — computes Comfort Scores from environmental data.

Formula:
  Comfort Score = 100 - [(wN × Noise_Penalty) + (wC × Canopy_Penalty)
                         + (wH × Heat_Penalty) + (wS × Safety_Penalty)
                         + (wT × Traffic_Penalty) + (wA × AQI_Penalty)]

Each penalty is normalized to 0.0 - 1.0.
Weights default to equal (1/6 each) and are user-adjustable.
Any factor set to None is excluded — its weight is removed and the
remaining weights auto-normalize.
Score is always clamped to [0, 100].
"""

# Default weights — equal importance
DEFAULT_WEIGHTS = {
    "noise": 1.0 / 6,
    "canopy": 1.0 / 6,
    "heat": 1.0 / 6,
    "safety": 1.0 / 6,
    "traffic": 1.0 / 6,
    "aqi": 1.0 / 6,
}

# Maximum total penalty (sum of weighted penalties is scaled to this)
MAX_PENALTY = 100.0


def _noise_penalty(noise_dba: float) -> float:
    """
    Convert noise level to penalty (0.0 - 1.0).

    Thresholds:
    - <= 45 dBA: 0.0 (quiet, comfortable)
    - >= 80 dBA: 1.0 (painfully loud)
    - Linear interpolation between
    """
    noise_dba = max(0.0, float(noise_dba))
    if noise_dba <= 45.0:
        return 0.0
    elif noise_dba >= 80.0:
        return 1.0
    else:
        return (noise_dba - 45.0) / (80.0 - 45.0)


def _canopy_penalty(canopy_pct: float) -> float:
    """
    Convert canopy cover to shade penalty (0.0 - 1.0).

    More canopy = less penalty (shade is good).
    - 100% canopy: 0.0 (full shade)
    - 0% canopy: 1.0 (no shade at all)
    """
    canopy_pct = max(0.0, min(100.0, float(canopy_pct)))
    return 1.0 - (canopy_pct / 100.0)


def _heat_penalty(heat_index: float) -> float:
    """
    Convert heat index (°F) to penalty (0.0 - 1.0).

    Thresholds based on NWS Heat Index categories:
    - <= 75°F: 0.0 (comfortable)
    - >= 110°F: 1.0 (dangerous)
    - Linear interpolation between
    """
    heat_index = max(0.0, float(heat_index))
    if heat_index <= 75.0:
        return 0.0
    elif heat_index >= 110.0:
        return 1.0
    else:
        return (heat_index - 75.0) / (110.0 - 75.0)


def _safety_penalty(safety_score: float) -> float:
    """
    Convert safety score (0-100) to penalty (0.0 - 1.0).

    More safety = less penalty.
    - 100 safety score: 0.0 (fully safe)
    - 0 safety score: 1.0 (hostile/dangerous)
    """
    safety_score = max(0.0, min(100.0, float(safety_score)))
    return 1.0 - (safety_score / 100.0)


def _traffic_penalty(aadt: float) -> float:
    """
    Convert traffic volume (AADT) to penalty (0.0 - 1.0).

    Thresholds based on FHWA road classification volumes:
    - <= 1000 AADT: 0.0 (quiet local/residential)
    - >= 30000 AADT: 1.0 (major arterial / highway)
    - Linear interpolation between
    """
    aadt = max(0.0, float(aadt))
    if aadt <= 1000.0:
        return 0.0
    elif aadt >= 30000.0:
        return 1.0
    else:
        return (aadt - 1000.0) / (30000.0 - 1000.0)


def _aqi_penalty(aqi: float) -> float:
    """
    Convert AQI (Air Quality Index) to penalty (0.0 - 1.0).

    Thresholds based on EPA AQI categories:
    - <= 50: 0.0 (Good — no health concern)
    - >= 200: 1.0 (Very Unhealthy — significant risk)
    - Linear interpolation between
    """
    aqi = max(0.0, float(aqi))
    if aqi <= 50.0:
        return 0.0
    elif aqi >= 200.0:
        return 1.0
    else:
        return (aqi - 50.0) / (200.0 - 50.0)


def compute_comfort_score(
    noise_dba: float | None = None,
    canopy_pct: float | None = None,
    heat_index: float | None = None,
    safety_score: float | None = None,
    traffic_volume: float | None = None,
    aqi: float | None = None,
    weights: dict | None = None,
) -> float:
    """
    Compute a comfort score (0-100) from environmental inputs.

    Any factor set to None is excluded from scoring — its weight is
    removed and the remaining weights auto-normalize. This enables
    per-factor feature toggles for troubleshooting.

    Args:
        noise_dba: Noise level in dBA (0+), or None to exclude
        canopy_pct: Tree canopy cover percentage (0-100), or None to exclude
        heat_index: Heat index in °F, or None to exclude
        safety_score: Road pedestrian safety score (0-100), or None to exclude
        traffic_volume: AADT, or None to exclude
        aqi: Air Quality Index (0-500), or None to exclude
        weights: Optional dict with keys "noise", "canopy", "heat",
                 "safety", "traffic", "aqi". Values are relative weights
                 (will be normalized to sum to 1.0).
                 Defaults to equal weights.

    Returns:
        float: Comfort score between 0.0 and 100.0
    """
    w = weights if weights is not None else DEFAULT_WEIGHTS.copy()

    # Build penalty map — only include enabled (non-None) factors
    penalties: dict[str, float] = {}
    if noise_dba is not None:
        penalties["noise"] = _noise_penalty(noise_dba)
    if canopy_pct is not None:
        penalties["canopy"] = _canopy_penalty(canopy_pct)
    if heat_index is not None:
        penalties["heat"] = _heat_penalty(heat_index)
    if safety_score is not None:
        penalties["safety"] = _safety_penalty(safety_score)
    if traffic_volume is not None:
        penalties["traffic"] = _traffic_penalty(traffic_volume)
    if aqi is not None:
        penalties["aqi"] = _aqi_penalty(aqi)

    # Strip weights for disabled factors
    w = {k: v for k, v in w.items() if k in penalties}

    # Normalize weights to sum to 1.0 (unless all zero)
    total_weight = sum(w.values())
    if total_weight > 0:
        w = {k: v / total_weight for k, v in w.items()}
    else:
        # All weights are zero — no penalties, perfect score
        return 100.0

    # Compute weighted penalty
    penalty = sum(w.get(k, 0.0) * p for k, p in penalties.items())

    # Score = 100 minus penalty scaled to 100
    score = 100.0 - (penalty * MAX_PENALTY)

    # Clamp to [0, 100]
    return max(0.0, min(100.0, round(score, 2)))

