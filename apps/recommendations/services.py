"""
Recommendation Service
----------------------
Full pipeline (multi-continent):
  1. Resolve location → continent → country → admin division
  2. Fetch live weather from Open-Meteo (graceful fallback)
  3. Load crops for that location (India: by state; global: by country)
  4. Run rule engine (pH soft + soil + weather scoring)
  5. Return structured result dict

Backward-compatible: India requests follow the exact same path as before,
with identical response format.
"""
from apps.location.models import State, Country
from apps.location.services import resolve_location, validate_india_bounds
from apps.location.geography_service import resolve_location_global
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
    Works for any supported country. Raises ValueError for bad location or empty DB.
    """
    lat        = validated_data.get("lat")
    lon        = validated_data.get("lon")
    state_name = validated_data.get("state_name")

    # ── Step 1: Resolve location ──────────────────────────────────────────
    is_india = False
    if lat is not None and lon is not None:
        if validate_india_bounds(lat, lon):
            # India pipeline (backward-compatible)
            is_india = True
            loc           = resolve_location(lat, lon)
            state         = loc["state"]
            distance_km   = loc["distance_km"]
            confidence    = loc["confidence"]
            confidence_note = loc["confidence_note"]
            zone_name     = (Crop.objects.filter(state=state).values_list("zone__name", flat=True).distinct().first()) or "Unknown"
            country_name  = "India"
            continent_name = "Asia"
        else:
            # Global pipeline
            geo = resolve_location_global(lat, lon)
            if not geo["country"]:
                raise ValueError(
                    "Could not determine country from coordinates. "
                    "Please ensure lat/lon are within a supported region."
                )
            country       = geo["country"]
            state         = None
            distance_km   = geo["distance_km"]
            confidence    = geo["confidence"]
            confidence_note = geo["confidence_note"]
            zone_name     = geo["admin_division"].name if geo["admin_division"] else country.name
            country_name  = country.name
            continent_name = geo["continent"].name if geo["continent"] else "Unknown"
    elif state_name:
        # Manual state selection (India)
        is_india = True
        try:
            state = State.objects.get(name__iexact=state_name.strip())
        except State.DoesNotExist:
            raise ValueError(f"State '{state_name}' not found in database.")
        lat, lon       = state.centroid_lat, state.centroid_lon
        distance_km    = 0.0
        confidence     = "manual"
        confidence_note = "State selected manually — weather fetched from state centroid."
        zone_name      = (Crop.objects.filter(state=state).values_list("zone__name", flat=True).distinct().first()) or "Unknown"
        country_name   = "India"
        continent_name = "Asia"
    else:
        raise ValueError("Provide either lat+lon OR state_name.")

    # ── Step 2: Fetch live weather (non-blocking, graceful fallback) ──────
    weather = fetch_weather(lat, lon)
    weather_available = weather is not None
    if not weather_available:
        weather = None

    # ── Step 3: Load crops for this location ──────────────────────────────
    if is_india and state is not None:
        crops_qs = (
            Crop.objects
            .filter(state=state)
            .select_related("state", "zone", "country", "continent")
            .order_by("sheet_order")
        )
    else:
        # Load by country
        country = Country.objects.filter(name__iexact=country_name).first()
        if not country:
            raise ValueError(f"Country '{country_name}' not found in database.")
        crops_qs = (
            Crop.objects
            .filter(country=country)
            .select_related("country", "continent", "admin_division")
            .order_by("sheet_order")
        )

    total_crops = crops_qs.count()
    if total_crops == 0:
        location_name = state.name if (is_india and state) else country_name
        raise ValueError(f"No crops for '{location_name}'. Run: python manage.py load_global_crops")

    # ── Step 4: Score and rank ────────────────────────────────────────────
    soil      = build_soil_input(validated_data)
    top_crops = rank_crops(list(crops_qs), soil, weather=weather, top_n=5)

    # ── Step 5: Build response (backward-compatible format) ───────────────
    return {
        "state":          state.name if (is_india and state) else country_name,
        "zone":           zone_name,
        "continent":      continent_name,
        "country":        country_name,
        "distance_km":    distance_km,
        "confidence":     confidence,
        "confidence_note": confidence_note,
        "weather":        weather,
        "weather_available": weather_available,
        "crops_evaluated": total_crops,
        "crops_eliminated_by_ph": 0,
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