"""
Scoring module — computes Comfort Scores from environmental data.

Formula:
  Comfort Score = 100 - [(wN × Noise_Penalty) + (wS × Shade_Penalty) + (wH × Heat_Penalty)]

Each penalty is normalized to 0.0 - 1.0.
Weights default to equal (1/3 each) but are user-adjustable.
Score is always clamped to [0, 100].
"""

# Default weights — equal importance
DEFAULT_WEIGHTS = {
    "noise": 1.0 / 3.0,
    "canopy": 1.0 / 3.0,
    "heat": 1.0 / 3.0,
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


def compute_comfort_score(
    noise_dba: float = 0.0,
    canopy_pct: float = 100.0,
    heat_index: float = 70.0,
    weights: dict | None = None,
) -> float:
    """
    Compute a comfort score (0-100) from environmental inputs.

    Args:
        noise_dba: Noise level in dBA (0+)
        canopy_pct: Tree canopy cover percentage (0-100)
        heat_index: Heat index in °F
        weights: Optional dict with keys "noise", "canopy", "heat".
                 Values are relative weights (will be normalized to sum to 1.0).
                 Defaults to equal weights.

    Returns:
        float: Comfort score between 0.0 and 100.0
    """
    w = weights if weights is not None else DEFAULT_WEIGHTS.copy()

    # Normalize weights to sum to 1.0 (unless all zero)
    total_weight = sum(w.values())
    if total_weight > 0:
        w = {k: v / total_weight for k, v in w.items()}
    else:
        # All weights are zero — no penalties, perfect score
        return 100.0

    # Compute weighted penalty
    penalty = (
        w.get("noise", 0.0) * _noise_penalty(noise_dba)
        + w.get("canopy", 0.0) * _canopy_penalty(canopy_pct)
        + w.get("heat", 0.0) * _heat_penalty(heat_index)
    )

    # Score = 100 minus penalty scaled to 100
    score = 100.0 - (penalty * MAX_PENALTY)

    # Clamp to [0, 100]
    return max(0.0, min(100.0, round(score, 2)))
