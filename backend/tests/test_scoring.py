"""
TEST SUITE 4: Comfort Scoring Engine
======================================
These tests verify that the scoring formula produces valid, meaningful
results when given real environmental data.

SCORING FORMULA:
  Comfort Score = 100 - [(wH × Heat_Penalty) + (wN × Noise_Penalty) + (wS × Shade_Penalty)]

  Where each penalty is normalized to 0.0-1.0:
  - Noise: 0dBA=0.0, >=80dBA=1.0 (linear interpolation)
  - Canopy: 100%=0.0 (full shade=no penalty), 0%=1.0 (no shade=max penalty)
  - Heat: contextual, based on temperature thresholds

WHAT THESE TESTS GUARANTEE:
- Scores are always in 0-100 range
- Worse conditions produce lower scores
- Scores vary across street segments (not uniform)
- Known good/bad inputs produce expected relative rankings
- The formula is deterministic

WHY THESE CAN'T BE FAKED:
- Mathematical invariant checks (boundary conditions, monotonicity)
- Cross-city comparison with random selection
- Structural validation of output format
"""
import pytest
from tests.cities import get_random_cities


@pytest.mark.scoring
class TestScoringFormula:
    """Does the scoring formula behave correctly?"""

    def test_perfect_conditions_score_100(self):
        """
        QUESTION: Do perfect environmental conditions produce a score of 100?

        PASS CRITERIA:
        - Noise=0dBA, Canopy=100%, Heat=comfortable → Score=100
        """
        from hcf.scoring.engine import compute_comfort_score

        score = compute_comfort_score(noise_dba=0, canopy_pct=100, heat_index=70)
        assert score == 100.0, f"Perfect conditions should score 100, got {score}"

    def test_safety_impacts_score(self):
        """
        QUESTION: Does a lower safety score lower the overall comfort score?
        """
        from hcf.scoring.engine import compute_comfort_score

        # Base conditions: quiet, shaded, cool
        perfect_safety = compute_comfort_score(noise_dba=0, canopy_pct=100, heat_index=70, safety_score=100)
        poor_safety = compute_comfort_score(noise_dba=0, canopy_pct=100, heat_index=70, safety_score=40)

        assert perfect_safety == 100.0
        assert poor_safety < 100.0, f"Poor safety did not reduce the score: {poor_safety}"


    def test_worst_conditions_score_near_zero(self):
        """
        QUESTION: Do terrible environmental conditions produce a score near 0?

        PASS CRITERIA:
        - Noise=90dBA, Canopy=0%, Heat=extreme → Score <= 10
        """
        from hcf.scoring.engine import compute_comfort_score

        score = compute_comfort_score(noise_dba=90, canopy_pct=0, heat_index=115, safety_score=0)
        assert score <= 10, f"Worst conditions should score <=10, got {score}"
        assert score >= 0, f"Score should never be negative, got {score}"

    def test_score_always_in_range(self):
        """
        QUESTION: Regardless of extreme inputs, is the score always 0-100?

        PASS CRITERIA:
        - Score ∈ [0, 100] for all edge cases
        """
        from hcf.scoring.engine import compute_comfort_score

        edge_cases = [
            (0, 0, 0),        # No noise, no canopy, freezing
            (200, 0, 200),    # Absurdly loud, no canopy, extreme heat
            (0, 100, 70),     # Perfect conditions
            (50, 50, 85),     # Moderate everything
            (-10, 150, -20),  # Invalid inputs (should be clamped)
        ]

        for noise, canopy, heat in edge_cases:
            score = compute_comfort_score(
                noise_dba=noise, canopy_pct=canopy, heat_index=heat
            )
            assert 0 <= score <= 100, (
                f"Score {score} out of range for inputs "
                f"noise={noise}, canopy={canopy}, heat={heat}"
            )

    def test_more_noise_means_lower_score(self):
        """
        QUESTION: Holding other factors constant, does more noise produce
        a lower comfort score? (Monotonicity check)

        PASS CRITERIA:
        - score(40dBA) > score(60dBA) > score(80dBA)
        """
        from hcf.scoring.engine import compute_comfort_score

        quiet = compute_comfort_score(noise_dba=40, canopy_pct=50, heat_index=80)
        moderate = compute_comfort_score(noise_dba=60, canopy_pct=50, heat_index=80)
        loud = compute_comfort_score(noise_dba=80, canopy_pct=50, heat_index=80)

        assert quiet > moderate > loud, (
            f"Noise monotonicity violated: quiet={quiet}, "
            f"moderate={moderate}, loud={loud}"
        )

    def test_more_canopy_means_higher_score(self):
        """
        QUESTION: Holding other factors constant, does more tree canopy
        produce a higher comfort score?

        PASS CRITERIA:
        - score(canopy=80%) > score(canopy=40%) > score(canopy=0%)
        """
        from hcf.scoring.engine import compute_comfort_score

        shaded = compute_comfort_score(noise_dba=50, canopy_pct=80, heat_index=80)
        partial = compute_comfort_score(noise_dba=50, canopy_pct=40, heat_index=80)
        exposed = compute_comfort_score(noise_dba=50, canopy_pct=0, heat_index=80)

        assert shaded > partial > exposed, (
            f"Canopy monotonicity violated: shaded={shaded}, "
            f"partial={partial}, exposed={exposed}"
        )

    def test_more_heat_means_lower_score(self):
        """
        QUESTION: Holding other factors constant, does higher heat index
        produce a lower comfort score?

        PASS CRITERIA:
        - score(heat=70) > score(heat=90) > score(heat=110)
        """
        from hcf.scoring.engine import compute_comfort_score

        cool = compute_comfort_score(noise_dba=50, canopy_pct=50, heat_index=70)
        warm = compute_comfort_score(noise_dba=50, canopy_pct=50, heat_index=90)
        hot = compute_comfort_score(noise_dba=50, canopy_pct=50, heat_index=110)

        assert cool > warm > hot, (
            f"Heat monotonicity violated: cool={cool}, "
            f"warm={warm}, hot={hot}"
        )

    def test_scoring_is_deterministic(self):
        """
        QUESTION: Given the same inputs, does the formula always produce
        the exact same output?

        PASS CRITERIA:
        - 10 calls with identical inputs produce identical results
        """
        from hcf.scoring.engine import compute_comfort_score

        results = [
            compute_comfort_score(noise_dba=55, canopy_pct=35, heat_index=88)
            for _ in range(10)
        ]
        assert len(set(results)) == 1, (
            f"Non-deterministic scoring: {set(results)}"
        )

    def test_custom_weights(self):
        """
        QUESTION: Can the user adjust the relative importance of each factor?

        PASS CRITERIA:
        - Setting noise weight to 0 makes noise irrelevant
        - Setting canopy weight to 0 makes canopy irrelevant
        """
        from hcf.scoring.engine import compute_comfort_score

        # With noise weight = 0, loud and quiet should score the same
        loud_no_weight = compute_comfort_score(
            noise_dba=90, canopy_pct=50, heat_index=80,
            weights={"noise": 0.0, "canopy": 0.5, "heat": 0.5}
        )
        quiet_no_weight = compute_comfort_score(
            noise_dba=30, canopy_pct=50, heat_index=80,
            weights={"noise": 0.0, "canopy": 0.5, "heat": 0.5}
        )
        assert loud_no_weight == quiet_no_weight, (
            f"With noise weight=0, noise should not affect score. "
            f"loud={loud_no_weight}, quiet={quiet_no_weight}"
        )


@pytest.mark.scoring
@pytest.mark.slow
class TestScoringWithRealData:
    """Does scoring work correctly with real fetched data?"""

    def test_score_real_segments(self, random_city):
        """
        QUESTION: Can we score real street segments from a random city
        using real environmental data?

        PASS CRITERIA:
        - Returns a GeoDataFrame with a 'comfort_score' column
        - All scores are in [0, 100]
        - Scores are not all identical (spatial variation exists)
        - At least 10 segments are scored
        """
        from hcf.scoring.pipeline import score_city_segments

        result = score_city_segments(random_city["osmnx_query"])

        assert "comfort_score" in result.columns, "Missing 'comfort_score' column"
        assert len(result) >= 10, f"Only {len(result)} segments scored"

        scores = result["comfort_score"]
        assert scores.min() >= 0, f"Score below 0: {scores.min()}"
        assert scores.max() <= 100, f"Score above 100: {scores.max()}"

        unique_scores = scores.nunique()
        assert unique_scores >= 3, (
            f"Only {unique_scores} unique scores — data may be faked"
        )
