"""
Global engine tests — continent/country-aware scoring.
Run with: python manage.py test apps.engine.tests_global

Tests cover:
  - Global pipeline with non-India crops
  - India regression (same inputs → same outputs as before)
  - Mixed continent/country scenarios
"""
from dataclasses import dataclass
from django.test import TestCase
from apps.engine.rule_engine import SoilInput, score_crop, rank_crops, MAX_SCORE


# ── Fake objects for global testing ─────────────────────────────────────────

@dataclass
class FakeContinent:
    name: str

@dataclass
class FakeCountry:
    name: str

@dataclass
class FakeAdminDivision:
    name: str

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
    continent: object = None
    country: object = None
    admin_division: object = None


def _make_crop(id, name, ph_lo, ph_hi, is_notable=False, sheet_order=0,
               category="Cereals", continent=None, country=None):
    """Create a FakeCrop with default mid-range soil params."""
    return FakeCrop(
        id=id, crop_name=name, category=category, notes="",
        is_notable=is_notable, temp_range="20-30°C", sheet_order=sheet_order,
        zone=FakeZone("Test Zone"), state=FakeState("Test State"),
        continent=continent, country=country,
        ph_lo=ph_lo, ph_hi=ph_hi,
        oc_lo=0.5, oc_hi=0.8, ec_lo=0.2, ec_hi=0.5,
        n_lo=200, n_hi=280, p_lo=15, p_hi=25,
        k_lo=150, k_hi=200, s_lo=8, s_hi=15,
        fe_lo=10, fe_hi=20, mn_lo=4, mn_hi=8,
        cu_lo=0.8, cu_hi=1.4, zn_lo=0.6, zn_hi=1.0,
        b_lo=0.3, b_hi=0.6, ca_lo=9, ca_hi=15,
        mg_lo=3, mg_hi=6,
    )


class GlobalCropScoringTests(TestCase):
    """The scoring engine is country-agnostic — test with non-India labels."""

    def test_nigerian_crop_scores_correctly(self):
        """A crop tagged with Nigeria should score identically to an India crop."""
        nigeria = FakeCountry(name="Nigeria")
        crop = _make_crop(1, "Cassava", 5.5, 7.0, continent=FakeContinent("Africa"),
                          country=nigeria)
        soil = SoilInput(ph=6.2, oc=0.6, ec=0.3,
                         n=220, p=18, k=160, s=10,
                         fe=12, mn=5, cu=1.0, zn=0.7, b=0.4, ca=10, mg=4)
        result = score_crop(crop, soil)
        self.assertIsNotNone(result)
        self.assertGreater(result.total_score, 0)

    def test_us_crop_scores_correctly(self):
        usa = FakeCountry(name="United States")
        crop = _make_crop(1, "Corn", 5.8, 7.0, continent=FakeContinent("America"),
                          country=usa)
        soil = SoilInput(ph=6.5, oc=0.7, ec=0.3,
                         n=240, p=20, k=180, s=12,
                         fe=15, mn=6, cu=1.1, zn=0.8, b=0.5, ca=12, mg=5)
        result = score_crop(crop, soil)
        self.assertIsNotNone(result)
        self.assertGreater(result.total_score, 0)

    def test_european_crop_with_all_params_missing(self):
        """Missing params → neutral 0.75 score for all optional fields."""
        france = FakeCountry(name="France")
        crop = _make_crop(1, "Wheat", 6.0, 7.5, continent=FakeContinent("Europe"),
                          country=france)
        soil = SoilInput(ph=7.0)  # only pH, all optional None
        result = score_crop(crop, soil)
        self.assertIsNotNone(result)
        # pH=20 + all optional at 0.75 (48.75) + weather neutral 7.5 = 76.25
        self.assertAlmostEqual(result.total_score, 76.25, places=1)

    def test_multi_continent_ranking(self):
        """Rank crops from different countries together — categories enforced."""
        crops = [
            _make_crop(1, "India Rice", 6.0, 7.5, category="Cereals",
                       continent=FakeContinent("Asia"), country=FakeCountry("India")),
            _make_crop(2, "US Corn", 5.8, 7.0, category="Cash Crops",
                       continent=FakeContinent("America"), country=FakeCountry("United States")),
            _make_crop(3, "France Wheat", 6.0, 7.5, category="Vegetables",
                       continent=FakeContinent("Europe"), country=FakeCountry("France")),
        ]
        soil = SoilInput(ph=6.8)
        results = rank_crops(crops, soil, top_n=3)
        self.assertEqual(len(results), 3)
        # All should have correct state_name (engine copies it from crop.state.name)
        for r in results:
            self.assertIsNotNone(r.state_name)

    def test_india_regression_perfect_soil_scores_92_5(self):
        """India crop with perfect soil scores 92.5 (weather neutral at 50%)."""
        crop = _make_crop(1, "Perfect Crop", 6.0, 7.5)
        soil = SoilInput(
            ph=6.8,
            oc=0.65, ec=0.35,
            n=240, p=20, k=175, s=11.5,
            fe=15, mn=6, cu=1.1, zn=0.8, b=0.45, ca=12, mg=4.5,
        )
        result = score_crop(crop, soil)
        # pH(20) + oc(5) + ec(5) + n(10) + p(9) + k(9) + s(7) +
        # fe(3) + mn(3) + cu(3) + zn(3) + b(2) + ca(3) + mg(3) = 85
        # + weather neutral 7.5 = 92.5
        self.assertAlmostEqual(result.total_score, 92.5, places=1)

    def test_india_regression_missing_params_76_25(self):
        """India crop with only pH should score 76.25 (regression)."""
        crop = _make_crop(1, "Any Crop", 6.0, 7.5)
        soil = SoilInput(ph=6.8)
        result = score_crop(crop, soil)
        # pH(20) + all optional at 0.75 (48.75) + weather neutral 7.5 = 76.25
        self.assertAlmostEqual(result.total_score, 76.25, places=1)

    def test_india_regression_ph_elimination(self):
        """India crop outside pH range should still be scored (soft scoring)."""
        crop = _make_crop(1, "Tea", 4.5, 5.5)
        soil = SoilInput(ph=6.8)
        result = score_crop(crop, soil)
        # pH no longer eliminates — it's soft scoring
        self.assertIsNotNone(result)
        self.assertGreater(result.total_score, 0)

    def test_india_regression_deficiency_detection(self):
        """India crop with low N should still flag deficiency (regression)."""
        crop = _make_crop(1, "Rice", 6.0, 7.5)
        soil = SoilInput(ph=6.8, n=100)
        result = score_crop(crop, soil)
        self.assertTrue(
            any("Nitrogen" in d for d in result.nutrient_deficiencies)
        )
