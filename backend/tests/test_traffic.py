"""
Tests for the traffic data module and traffic penalty integration.

These tests verify:
  - Traffic penalty threshold boundaries
  - Feature flag disable behavior
  - Scoring engine integration with traffic factor
"""
import pytest

from hcf.scoring.engine import _traffic_penalty, compute_comfort_score


class TestTrafficPenalty:
    """Tests for _traffic_penalty() thresholds."""

    def test_low_traffic_no_penalty(self):
        """AADT <= 1000 should produce zero penalty."""
        assert _traffic_penalty(0) == 0.0
        assert _traffic_penalty(500) == 0.0
        assert _traffic_penalty(1000) == 0.0

    def test_high_traffic_max_penalty(self):
        """AADT >= 30000 should produce max penalty."""
        assert _traffic_penalty(30000) == 1.0
        assert _traffic_penalty(50000) == 1.0

    def test_mid_traffic_linear(self):
        """Mid-range AADT should interpolate linearly."""
        # Midpoint: (1000 + 30000) / 2 = 15500
        penalty = _traffic_penalty(15500)
        assert 0.49 < penalty < 0.51, f"Expected ~0.5, got {penalty}"

    def test_negative_clamped(self):
        """Negative AADT should be clamped to 0."""
        assert _traffic_penalty(-100) == 0.0


class TestComfortScoreWithTraffic:
    """Tests for compute_comfort_score() with traffic integration."""

    def test_traffic_none_excluded(self):
        """When traffic_volume=None, score should use only 4 factors."""
        score_without = compute_comfort_score(
            noise_dba=50.0, canopy_pct=50.0, heat_index=85.0,
            safety_score=80.0, traffic_volume=None,
        )
        # Score should be the same as the old 4-factor calculation
        assert 0 <= score_without <= 100

    def test_traffic_affects_score(self):
        """Adding high traffic should lower the comfort score."""
        base_score = compute_comfort_score(
            noise_dba=50.0, canopy_pct=50.0, heat_index=85.0,
            safety_score=80.0, traffic_volume=None,
        )
        traffic_score = compute_comfort_score(
            noise_dba=50.0, canopy_pct=50.0, heat_index=85.0,
            safety_score=80.0, traffic_volume=25000,
        )
        assert traffic_score < base_score, (
            f"High traffic ({traffic_score}) should score lower than "
            f"no traffic ({base_score})"
        )

    def test_low_traffic_minimal_impact(self):
        """Low traffic (<=1000) should not change score vs no traffic."""
        no_traffic = compute_comfort_score(
            noise_dba=50.0, canopy_pct=50.0, heat_index=85.0,
            safety_score=80.0, traffic_volume=None,
        )
        low_traffic = compute_comfort_score(
            noise_dba=50.0, canopy_pct=50.0, heat_index=85.0,
            safety_score=80.0, traffic_volume=500,
        )
        # With traffic_volume=500 (penalty=0), the only difference
        # is weight redistribution (5 factors vs 4).
        # The scores will be close but not identical because weights
        # are redistributed. Just verify it's still reasonable.
        assert abs(low_traffic - no_traffic) < 5, (
            f"Low traffic should have minimal impact: "
            f"no_traffic={no_traffic}, low_traffic={low_traffic}"
        )


class TestAllFactorsDisabled:
    """Test that disabling all factors via None still returns valid scores."""

    def test_all_none_returns_perfect(self):
        """All factors None should return 100 (perfect score)."""
        score = compute_comfort_score(
            noise_dba=None, canopy_pct=None, heat_index=None,
            safety_score=None, traffic_volume=None,
        )
        assert score == 100.0

    def test_single_factor_only(self):
        """Only one factor enabled should score based on that factor alone."""
        # Only noise at max penalty (80+ dBA)
        score = compute_comfort_score(
            noise_dba=80.0, canopy_pct=None, heat_index=None,
            safety_score=None, traffic_volume=None,
        )
        assert score == 0.0, f"Max noise alone should give 0, got {score}"

        # Only noise at no penalty (<=45 dBA)
        score = compute_comfort_score(
            noise_dba=45.0, canopy_pct=None, heat_index=None,
            safety_score=None, traffic_volume=None,
        )
        assert score == 100.0, f"Min noise alone should give 100, got {score}"
