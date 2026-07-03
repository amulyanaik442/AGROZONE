"""
Unit tests for the AgroZone rule engine.
Run with: python manage.py test apps.engine

Tests cover:
  - Gate 2 pH hard elimination
  - Gate 3/4/5 scoring correctness
  - Tie-breaker ordering (is_notable, sheet_order)
  - Missing soil values (neutral 0.5 score)
"""
from dataclasses import dataclass
from django.test import TestCase
from apps.engine.rule_engine import SoilInput, score_crop, rank_crops, MAX_SCORE


# ── Minimal fake ORM objects (no DB needed) ───────────────────────────────────

@dataclass
class FakeZone:
    name: str

@dataclass
class FakeState:
    name: str

@dataclass
class FakeCrop:
    id: int
    crop_name: str
    category: str
    notes: str
    is_notable: bool
    temp_range: str
    sheet_order: int
    zone: object
    state: object
    # All soil param lo/hi
    ph_lo: float; ph_hi: float
    oc_lo: float; oc_hi: float
    ec_lo: float; ec_hi: float
    n_lo: float;  n_hi: float
    p_lo: float;  p_hi: float
    k_lo: float;  k_hi: float
    s_lo: float;  s_hi: float
    fe_lo: float; fe_hi: float
    mn_lo: float; mn_hi: float
    cu_lo: float; cu_hi: float
    zn_lo: float; zn_hi: float
    b_lo: float;  b_hi: float
    ca_lo: float; ca_hi: float
    mg_lo: float; mg_hi: float


def _make_crop(id, name, ph_lo, ph_hi, is_notable=False, sheet_order=0):
    """Create a FakeCrop with default mid-range soil params."""
    return FakeCrop(
        id=id, crop_name=name, category="Cereals", notes="",
        is_notable=is_notable, temp_range="20-30°C", sheet_order=sheet_order,
        zone=FakeZone("Test Zone"), state=FakeState("Test State"),
        ph_lo=ph_lo, ph_hi=ph_hi,
        oc_lo=0.5, oc_hi=0.8, ec_lo=0.2, ec_hi=0.5,
        n_lo=200, n_hi=280, p_lo=15, p_hi=25,
        k_lo=150, k_hi=200, s_lo=8, s_hi=15,
        fe_lo=10, fe_hi=20, mn_lo=4, mn_hi=8,
        cu_lo=0.8, cu_hi=1.4, zn_lo=0.6, zn_hi=1.0,
        b_lo=0.3, b_hi=0.6, ca_lo=9, ca_hi=15,
        mg_lo=3, mg_hi=6,
    )


# ── Test cases ────────────────────────────────────────────────────────────────

class PHGateTests(TestCase):
    """Gate 2 — pH hard filter eliminates crops outside range."""

    def test_ph_in_range_passes(self):
        crop = _make_crop(1, "Wheat", ph_lo=6.0, ph_hi=7.5)
        soil = SoilInput(ph=6.8)
        result = score_crop(crop, soil)
        self.assertIsNotNone(result, "Crop inside pH range should NOT be eliminated.")

    def test_ph_below_range_eliminated(self):
        crop = _make_crop(1, "Tea", ph_lo=4.5, ph_hi=5.5)
        soil = SoilInput(ph=6.8)
        result = score_crop(crop, soil)
        self.assertIsNone(result, "Crop below pH range should be eliminated.")

    def test_ph_above_range_eliminated(self):
        crop = _make_crop(1, "Blueberry", ph_lo=4.0, ph_hi=5.0)
        soil = SoilInput(ph=7.0)
        result = score_crop(crop, soil)
        self.assertIsNone(result, "Crop above pH range should be eliminated.")

    def test_ph_at_exact_boundary_passes(self):
        crop = _make_crop(1, "Rice", ph_lo=6.0, ph_hi=7.5)
        for boundary_ph in [6.0, 7.5]:
            soil = SoilInput(ph=boundary_ph)
            result = score_crop(crop, soil)
            self.assertIsNotNone(result, f"pH exactly at boundary ({boundary_ph}) should pass.")


class ScoringTests(TestCase):
    """Gates 3-5 — scoring correctness."""

    def _perfect_soil(self):
        """Soil values exactly in the middle of all ranges."""
        return SoilInput(
            ph=6.8,
            oc=0.65, ec=0.35,
            n=240, p=20, k=175, s=11.5,
            fe=15, mn=6, cu=1.1, zn=0.8, b=0.45, ca=12, mg=4.5,
        )

    def test_perfect_soil_scores_100(self):
        crop = _make_crop(1, "Perfect Crop", ph_lo=6.0, ph_hi=7.5)
        soil = self._perfect_soil()
        result = score_crop(crop, soil)
        self.assertAlmostEqual(result.total_score, MAX_SCORE, places=1,
                               msg="All params in range should score 100.")

    def test_missing_all_optional_scores_50pct(self):
        """Missing params score 0.5 each → total should be 50%."""
        crop = _make_crop(1, "Any Crop", ph_lo=6.0, ph_hi=7.5)
        soil = SoilInput(ph=6.8)  # only pH, all others None
        result = score_crop(crop, soil)
        self.assertAlmostEqual(result.total_score, 50.0, places=1,
                               msg="All missing params should yield 50% score.")

    def test_deficiency_flagged_when_below_range(self):
        crop = _make_crop(1, "Rice", ph_lo=6.0, ph_hi=7.5)
        soil = SoilInput(ph=6.8, n=100)  # N way below 200 min
        result = score_crop(crop, soil)
        self.assertTrue(
            any("Nitrogen" in d for d in result.nutrient_deficiencies),
            "Low nitrogen should appear in nutrient_deficiencies."
        )

    def test_deficiency_flagged_when_above_range(self):
        crop = _make_crop(1, "Rice", ph_lo=6.0, ph_hi=7.5)
        soil = SoilInput(ph=6.8, n=400)  # N way above 280 max
        result = score_crop(crop, soil)
        self.assertTrue(
            any("Nitrogen" in d for d in result.nutrient_deficiencies),
            "High nitrogen should appear in nutrient_deficiencies."
        )

    def test_in_range_param_no_deficiency(self):
        crop = _make_crop(1, "Rice", ph_lo=6.0, ph_hi=7.5)
        soil = SoilInput(ph=6.8, n=240)  # N in range
        result = score_crop(crop, soil)
        self.assertFalse(
            any("Nitrogen" in d for d in result.nutrient_deficiencies),
            "In-range nitrogen should not appear in deficiencies."
        )


class RankingTests(TestCase):
    """Ranking, tie-breaking, and top-N slicing."""

    def test_top_n_returned(self):
        crops = [_make_crop(i, f"Crop{i}", 6.0, 7.5) for i in range(10)]
        soil = SoilInput(ph=6.8)
        results = rank_crops(crops, soil, top_n=5)
        self.assertEqual(len(results), 5)

    def test_ph_eliminated_crops_not_in_results(self):
        good = _make_crop(1, "Good", ph_lo=6.0, ph_hi=7.5)
        bad  = _make_crop(2, "Bad",  ph_lo=4.0, ph_hi=5.0)
        soil = SoilInput(ph=6.8)
        results = rank_crops([good, bad], soil)
        names = [r.crop_name for r in results]
        self.assertIn("Good", names)
        self.assertNotIn("Bad", names)

    def test_notable_crop_wins_tiebreak(self):
        """Two crops with identical scores: notable one should rank higher."""
        ordinary = _make_crop(1, "Ordinary", 6.0, 7.5, is_notable=False, sheet_order=0)
        notable  = _make_crop(2, "Notable",  6.0, 7.5, is_notable=True,  sheet_order=1)
        soil = SoilInput(ph=6.8)  # all params missing → both score 50.0
        results = rank_crops([ordinary, notable], soil)
        self.assertEqual(results[0].crop_name, "Notable",
                         "Notable crop should beat ordinary crop on tie-break.")

    def test_sheet_order_tiebreak(self):
        """Two non-notable crops with equal score: lower sheet_order wins."""
        first  = _make_crop(1, "First",  6.0, 7.5, sheet_order=0)
        second = _make_crop(2, "Second", 6.0, 7.5, sheet_order=1)
        soil = SoilInput(ph=6.8)
        results = rank_crops([second, first], soil)
        self.assertEqual(results[0].crop_name, "First",
                         "Earlier sheet_order should win the final tie-break.")

    def test_returns_empty_when_all_eliminated(self):
        crops = [_make_crop(i, f"Crop{i}", ph_lo=4.0, ph_hi=5.0) for i in range(5)]
        soil = SoilInput(ph=7.5)  # eliminates all
        results = rank_crops(crops, soil)
        self.assertEqual(results, [], "All crops eliminated should return empty list.")
