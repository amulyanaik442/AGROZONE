"""
AgroZone Rule Engine
====================
Ranking strategy:
  1. Score each crop by temp match + soil inputs (if provided)
  2. Enforce category diversity — top 5 must come from different categories
     so user always sees a mix of Cereals, Cash Crops, Fruits, etc.
  3. Within each category, pick the best-scoring crop
  4. Final top 5 sorted by score DESC

This prevents one category from monopolising all 5 slots when
soil inputs are blank and temperature fits most crops equally.
"""
from dataclasses import dataclass, field
from typing import Optional
import math
import re

# ── Weights ───────────────────────────────────────────────────────────────────
# Add this before the Gates 3/4/5 loop:
GATE3_PARAMS = {"oc": 5.0, "ec": 5.0}
GATE4_PARAMS = {"n": 10.0, "p": 9.0, "k": 9.0, "s": 7.0}
GATE5_PARAMS = {
    "fe": 3.0, "mn": 3.0, "cu": 3.0, "zn": 3.0,
    "b":  2.0, "ca": 3.0, "mg": 3.0,
}
WEATHER_WEIGHT = 15.0
MAX_SCORE = 100.0

PARAM_LABELS = {
    "oc": "Organic Carbon", "ec": "EC",
    "n":  "Nitrogen",       "p":  "P₂O₅",
    "k":  "Potassium",      "s":  "Sulphur",
    "fe": "Iron",           "mn": "Manganese",
    "cu": "Copper",         "zn": "Zinc",
    "b":  "Boron",          "ca": "Calcium",
    "mg": "Magnesium",
}
PARAM_UNITS = {
    "oc": "%", "ec": "dS/m",
    "n": "kg/ha", "p": "kg/ha", "k": "kg/ha", "s": "ppm",
    "fe": "ppm", "mn": "ppm", "cu": "ppm", "zn": "ppm",
    "b": "ppm", "ca": "meq/100g", "mg": "meq/100g",
}

# Category priority order — defines which categories appear in top 5
# when scores are equal. Covers all 9 categories in the dataset.
CATEGORY_PRIORITY = [
    "Cereals & Millets",
    "Cash Crops",
    "Fruits",
    "Vegetables",
    "Pulses",
    "Oilseeds",
    "Spices",
    "Plantation Crops",
    "Flowers",
]


# ── Input dataclass ───────────────────────────────────────────────────────────

@dataclass
class SoilInput:
    ph:  float
    oc:  Optional[float] = None
    ec:  Optional[float] = None
    n:   Optional[float] = None
    p:   Optional[float] = None
    k:   Optional[float] = None
    s:   Optional[float] = None
    fe:  Optional[float] = None
    mn:  Optional[float] = None
    cu:  Optional[float] = None
    zn:  Optional[float] = None
    b:   Optional[float] = None
    ca:  Optional[float] = None
    mg:  Optional[float] = None


@dataclass
class CropScore:
    crop_id:              int
    crop_name:            str
    category:             str
    zone_name:            str
    state_name:           str
    notes:                str
    is_notable:           bool
    temp_range:           str
    total_score:          float = 0.0
    ph_passed:            bool  = True
    nutrient_deficiencies: list = field(default_factory=list)
    param_scores:          dict = field(default_factory=dict)
    weather_score:         dict = field(default_factory=dict)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _score_param(value: Optional[float], lo: float, hi: float) -> float:
    if value is None:
        return 0.75   # neutral — don't penalise missing inputs
    width = hi - lo
    if width <= 0:
        return 1.0 if value == lo else 0.5
    if lo <= value <= hi:
        return 1.0
    dist = (lo - value) if value < lo else (value - hi)
    return round(max(0.1, math.exp(-dist / max(width, 1.0))), 4)


def _status(value: Optional[float], lo: float, hi: float) -> str:
    if value is None:   return "missing"
    if value < lo:      return "low"
    if value > hi:      return "high"
    return "ok"


def _deficiency_label(param, value, lo, hi):
    if value is None: return None
    name = PARAM_LABELS.get(param, param)
    unit = PARAM_UNITS.get(param, "")
    if value < lo:
        return f"{name} low ({round(value,4)} {unit} < {round(lo,4)} {unit})".strip()
    if value > hi:
        return f"{name} high ({round(value,4)} {unit} > {round(hi,4)} {unit})".strip()
    return None


# ── Main scoring ──────────────────────────────────────────────────────────────

def score_crop(crop, soil: SoilInput, weather: Optional[dict] = None) -> CropScore:
    result = CropScore(
        crop_id=crop.id, crop_name=crop.crop_name, category=crop.category,
        zone_name=crop.zone.name if crop.zone else "",
        state_name=crop.state.name if crop.state else (crop.country.name if crop.country else ""), notes=crop.notes,
        is_notable=crop.is_notable, temp_range=crop.temp_range,
    )

    total = 0.0
    PH_WEIGHT = 20.0
    ph_s = _score_param(soil.ph, crop.ph_lo, crop.ph_hi)
    ph_pts = round(ph_s * PH_WEIGHT, 4)
    total += ph_pts
    
    # Gates 3 / 4 / 5
    for gate_params in (GATE3_PARAMS, GATE4_PARAMS, GATE5_PARAMS):
        for param, weight in gate_params.items():
            value = getattr(soil, param)
            lo    = getattr(crop, f"{param}_lo")
            hi    = getattr(crop, f"{param}_hi")
            s     = _score_param(value, lo, hi)
            pts   = round(s * weight, 4)
            total += pts
            result.param_scores[param] = {
                "score":  round(pts, 2), "max": weight,
                "pct":    round(s * 100, 1),
                "value":  round(value, 4) if value is not None else None,
                "lo":     round(lo, 4), "hi": round(hi, 4),
                "unit":   PARAM_UNITS.get(param, ""),
                "status": _status(value, lo, hi),
            }
            defic = _deficiency_label(param, value, lo, hi)
            if defic:
                result.nutrient_deficiencies.append(defic)

    # Weather scoring
    from apps.engine.weather_service import score_weather
    temp_current = weather.get("temp_current") if weather else None
    w_score = score_weather(temp_current, crop.temp_range)
    total += w_score["score"]
    result.weather_score = w_score

    result.total_score = round(total, 2)
    return result


def rank_crops(crops, soil: SoilInput, weather: Optional[dict] = None, top_n: int = 5) -> list:
    """
    Score all crops, then enforce category diversity:
    Pick the BEST crop from each category, then return
    top_n sorted by score — guaranteeing variety in results.
    """
    # Score every crop
    all_scored = []
    for crop in crops:
        result = score_crop(crop, soil, weather)
        result._sheet_order = crop.sheet_order
        all_scored.append(result)

    # Sort all by score DESC, notable, sheet_order
    all_scored.sort(key=lambda r: (
        -r.weather_score.get("pct", 50),
        -r.total_score,
        -int(r.is_notable),
        r._sheet_order
    ))

    # Pick best crop per category (diversity enforcement)
    seen_categories = {}
    for crop in all_scored:
        cat = crop.category
        if cat not in seen_categories:
            seen_categories[cat] = crop   # best score in this category

    # Sort categories by their best crop's score DESC
    # Use CATEGORY_PRIORITY as a tiebreaker for equal scores
    def cat_sort_key(item):
        cat, best_crop = item
        priority = CATEGORY_PRIORITY.index(cat) if cat in CATEGORY_PRIORITY else 99
        return (-best_crop.total_score, -best_crop.weather_score.get("pct", 50), priority)

    sorted_categories = sorted(seen_categories.items(), key=cat_sort_key)

    # Return top_n best-per-category crops
    top = [crop for _, crop in sorted_categories[:top_n]]
    return top