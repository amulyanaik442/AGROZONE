"""
Recommendation Service
----------------------
Full pipeline:
  1. Resolve location → state
  2. Fetch live weather from Open-Meteo (graceful fallback if unavailable)
  3. Load crops for that state
  4. Run rule engine (pH soft + soil + weather scoring)
  5. Return structured result dict
"""
from apps.location.models import State
from apps.location.services import resolve_location, validate_india_bounds
from apps.crops.models import Crop
from apps.engine.rule_engine import SoilInput, rank_crops, MAX_SCORE
from apps.engine.weather_service import fetch_weather


def build_soil_input(data: dict) -> SoilInput:
    return SoilInput(
        ph=data["ph"],
        oc=data.get("oc"), ec=data.get("ec"),
        n=data.get("n"),   p=data.get("p"),
        k=data.get("k"),   s=data.get("s"),
        fe=data.get("fe"), mn=data.get("mn"),
        cu=data.get("cu"), zn=data.get("zn"),
        b=data.get("b"),   ca=data.get("ca"),
        mg=data.get("mg"),
    )


def get_recommendations(validated_data: dict) -> dict:
    """
    Full pipeline → top 5 crops with scores, deficiencies, weather context.
    Raises ValueError for bad location or empty DB.
    """
    lat        = validated_data.get("lat")
    lon        = validated_data.get("lon")
    state_name = validated_data.get("state_name")

    # ── Step 1: Resolve state ─────────────────────────────────────────────
    if lat is not None and lon is not None:
        if not validate_india_bounds(lat, lon):
            raise ValueError("Coordinates are outside India's bounding box.")
        loc        = resolve_location(lat, lon)
        state      = loc["state"]
        distance_km    = loc["distance_km"]
        confidence     = loc["confidence"]
        confidence_note = loc["confidence_note"]
    else:
        try:
            state = State.objects.get(name__iexact=state_name.strip())
        except State.DoesNotExist:
            raise ValueError(f"State '{state_name}' not found in database.")
        # For manual state selection use state centroid for weather
        lat, lon       = state.centroid_lat, state.centroid_lon
        distance_km    = 0.0
        confidence     = "manual"
        confidence_note = "State selected manually — weather fetched from state centroid."

    # ── Step 2: Fetch live weather (non-blocking, graceful fallback) ──────
    weather = fetch_weather(lat, lon)
    weather_available = weather is not None
    if not weather_available:
        weather = None   # rank_crops handles None → neutral 0.5 weather score

    # ── Step 3: Load crops for this state ─────────────────────────────────
    crops_qs = (
        Crop.objects
        .filter(state=state)
        .select_related("state", "zone")
        .order_by("sheet_order")
    )
    total_crops = crops_qs.count()
    if total_crops == 0:
        raise ValueError(f"No crops for '{state.name}'. Run: python manage.py load_crops")

    # ── Step 4: Score and rank ────────────────────────────────────────────
    soil      = build_soil_input(validated_data)
    top_crops = rank_crops(list(crops_qs), soil, weather=weather, top_n=5)

    zone_name = (
        top_crops[0].zone_name if top_crops
        else (crops_qs.first().zone.name if crops_qs.first() and crops_qs.first().zone else "Unknown")
    )

    # ── Step 5: Build response ────────────────────────────────────────────
    return {
        "state":          state.name,
        "zone":           zone_name,
        "distance_km":    distance_km,
        "confidence":     confidence,
        "confidence_note": confidence_note,
        "weather":        weather,
        "weather_available": weather_available,
        "crops_evaluated": total_crops,
        "crops_eliminated_by_ph": 0,   # pH is now soft scoring
        "top_crops": [
            {
                "rank":          i + 1,
                "crop_name":     r.crop_name,
                "category":      r.category,
                "zone_name":     r.zone_name,
                "state_name":    r.state_name,
                "notes":         r.notes,
                "is_notable":    r.is_notable,
                "temp_range":    r.temp_range,
                "total_score":   r.total_score,
                "max_score":     MAX_SCORE,
                "score_pct":     round(r.total_score / MAX_SCORE * 100, 1),
                "nutrient_deficiencies": r.nutrient_deficiencies,
                "param_scores":  r.param_scores,
                "weather_score": r.weather_score,
            }
            for i, r in enumerate(top_crops)
        ],
    }