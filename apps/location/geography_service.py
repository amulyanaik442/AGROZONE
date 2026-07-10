"""
Geography Service
=================
Generic continent/country/division resolution from lat/lon.
Configuration-driven: new continents/countries can be added via JSON config
files without modifying engine code.

Supports:
- Continent detection by bounding box
- Country detection by centroid/anchor nearest-match
- Administrative division hierarchy (config-driven)
- Multi-anchor matching for large/irregular countries
"""
import json
import math
import os
from pathlib import Path
from typing import Optional
from django.conf import settings
from .models import Continent, Country, AdminDivision


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _load_json(relative_path: str) -> dict:
    path = Path(settings.BASE_DIR) / relative_path
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Country anchors — multi-point anchors for large countries
# Extend this table as new countries are added. Each anchor is
# (lat, lon, country_code) so that any point in the country matches.
# ---------------------------------------------------------------------------
COUNTRY_ANCHORS = [
    # India anchors (from existing STATE_ANCHORS logic)
    (15.8281, 78.0373, "IN"), (13.6288, 79.4192, "IN"),
    (16.5062, 80.6480, "IN"), (17.6868, 83.2185, "IN"),
    (27.0844, 93.6053, "IN"), (26.1445, 91.7362, "IN"),
    (25.5941, 85.1376, "IN"), (21.2514, 81.6296, "IN"),
    (15.4909, 73.8278, "IN"), (23.0225, 72.5714, "IN"),
    (29.0588, 76.0856, "IN"), (31.1048, 77.1734, "IN"),
    (34.0837, 74.7973, "IN"), (23.3441, 85.3096, "IN"),
    (12.9716, 77.5946, "IN"), (8.5241, 76.9366, "IN"),
    (23.2599, 77.4126, "IN"), (19.0760, 72.8777, "IN"),
    (24.8170, 93.9368, "IN"), (25.5788, 91.8933, "IN"),
    (23.7271, 92.7176, "IN"), (25.6751, 94.1086, "IN"),
    (20.2961, 85.8245, "IN"), (30.9010, 75.8573, "IN"),
    (26.9124, 75.7873, "IN"), (27.3389, 88.6065, "IN"),
    (13.0827, 80.2707, "IN"), (17.3850, 78.4867, "IN"),
    (23.8315, 91.2868, "IN"), (26.8467, 80.9462, "IN"),
    (30.3165, 78.0322, "IN"), (22.5726, 88.3639, "IN"),

    # United States anchors
    (40.7128, -74.0060, "US"), (34.0522, -118.2437, "US"),
    (41.8781, -87.6298, "US"), (29.7604, -95.3698, "US"),
    (33.4484, -112.0740, "US"), (39.7392, -104.9903, "US"),
    (32.7157, -117.1611, "US"), (38.9072, -77.0369, "US"),
    (32.7767, -96.7970, "US"), (39.9526, -75.1652, "US"),
    (47.6062, -122.3321, "US"), (42.3601, -71.0589, "US"),
    (25.7617, -80.1918, "US"), (37.7749, -122.4194, "US"),

    # Brazil anchors
    (-23.5505, -46.6333, "BR"), (-22.9068, -43.1729, "BR"),
    (-15.7942, -47.8822, "BR"), (-19.9167, -43.9345, "BR"),
    (-12.9714, -38.5014, "BR"), (-8.0476, -34.8770, "BR"),
    (-3.1190, -60.0217, "BR"), (-1.4558, -48.4902, "BR"),
    (-30.0346, -51.2177, "BR"), (-25.4284, -49.2733, "BR"),

    # Nigeria anchors
    (6.5244, 3.3792, "NG"), (7.3775, 3.9470, "NG"),
    (9.0765, 7.3986, "NG"), (10.5105, 7.4165, "NG"),
    (12.0022, 8.5919, "NG"), (6.4453, 7.4929, "NG"),

    # Kenya anchors
    (-1.2921, 36.8219, "KE"), (-0.3031, 36.0800, "KE"),
    (-0.1022, 34.7617, "KE"), (0.5143, 35.2698, "KE"),

    # South Africa anchors
    (-33.9249, 18.4241, "ZA"), (-26.2041, 28.0473, "ZA"),
    (-29.8587, 31.0218, "ZA"), (-33.9581, 25.6009, "ZA"),

    # France anchors
    (48.8566, 2.3522, "FR"), (43.2965, 5.3698, "FR"),
    (45.7640, 4.8357, "FR"), (43.6047, 1.4442, "FR"),

    # Germany anchors
    (52.5200, 13.4050, "DE"), (48.1351, 11.5820, "DE"),
    (50.1109, 8.6821, "DE"), (53.5511, 9.9937, "DE"),
    (51.1657, 10.4515, "DE"),

    # Italy anchors
    (41.9028, 12.4964, "IT"), (45.4642, 9.1900, "IT"),
    (40.8518, 14.2681, "IT"), (43.7696, 11.2558, "IT"),
    (45.0703, 7.6869, "IT"),

    # Canada anchors
    (43.6532, -79.3832, "CA"), (45.5017, -73.5673, "CA"),
    (49.2827, -123.1207, "CA"), (51.0447, -114.0719, "CA"),

    # Egypt anchors
    (30.0444, 31.2357, "EG"), (31.2001, 29.9187, "EG"),
    (26.8206, 30.8025, "EG"), (25.6872, 32.6396, "EG"),

    # Ethiopia anchors
    (9.0320, 38.7469, "ET"), (11.5742, 37.3614, "ET"),
    (13.4967, 39.4715, "ET"), (6.6111, 37.4500, "ET"),

    # Morocco anchors
    (33.5731, -7.5898, "MA"), (31.6295, -7.9811, "MA"),
    (35.7673, -5.7998, "MA"), (30.4278, -9.5981, "MA"),

    # Ghana anchors
    (5.6037, -0.1870, "GH"), (6.6871, -1.6219, "GH"),
    (9.4036, -0.8393, "GH"), (4.9151, -1.9790, "GH"),

    # Tanzania anchors
    (-6.7924, 39.2083, "TZ"), (-3.3696, 36.6833, "TZ"),
    (-8.8891, 33.4570, "TZ"), (-6.1626, 35.7497, "TZ"),

    # Uganda anchors
    (0.3476, 32.5825, "UG"), (0.4272, 33.2053, "UG"),
    (0.6605, 30.2744, "UG"), (2.7733, 32.2940, "UG"),

    # Cote d'Ivoire anchors
    (5.3600, -4.0083, "CI"), (6.8500, -5.3000, "CI"),
    (7.4120, -7.5532, "CI"), (5.8962, -5.6693, "CI"),

    # Algeria anchors
    (36.7538, 3.0588, "DZ"), (35.6994, -0.6290, "DZ"),
    (31.6300, -2.2300, "DZ"), (36.3719, 6.6139, "DZ"),

    # Sudan anchors
    (15.5007, 32.5599, "SD"), (13.1863, 30.2168, "SD"),
    (19.6156, 37.2059, "SD"), (11.7900, 34.3499, "SD"),

    # Cameroon anchors
    (3.8480, 11.5021, "CM"), (6.5014, 10.3954, "CM"),
    (4.1604, 13.6850, "CM"), (4.0370, 9.6800, "CM"),

    # Poland anchors
    (52.2297, 21.0122, "PL"), (50.0647, 19.9450, "PL"),
    (51.1079, 17.0385, "PL"), (53.1325, 18.0088, "PL"),

    # Spain anchors
    (40.4168, -3.7038, "ES"), (41.3874, 2.1686, "ES"),
    (37.3891, -5.9845, "ES"), (39.4699, -0.3763, "ES"),

    # Romania anchors
    (44.4268, 26.1025, "RO"), (46.7712, 23.6236, "RO"),
    (45.7489, 21.2087, "RO"), (47.1585, 27.6014, "RO"),

    # Netherlands anchors
    (52.3676, 4.9041, "NL"), (51.9244, 4.4777, "NL"),
    (52.0907, 5.1214, "NL"), (53.2194, 6.5665, "NL"),

    # Ukraine anchors
    (50.4501, 30.5234, "UA"), (49.8397, 24.0297, "UA"),
    (48.0228, 37.8022, "UA"), (46.4825, 30.7233, "UA"),

    # United Kingdom anchors
    (51.5074, -0.1278, "GB"), (53.4808, -2.2426, "GB"),
    (55.9533, -3.1883, "GB"), (52.4862, -1.8904, "GB"),

    # Greece anchors
    (37.9838, 23.7275, "GR"), (40.6401, 22.9444, "GR"),
    (38.2466, 21.7346, "GR"), (35.3387, 25.1442, "GR"),

    # Hungary anchors
    (47.4979, 19.0402, "HU"), (47.5316, 21.6273, "HU"),
    (46.2530, 20.1414, "HU"), (46.9090, 18.0584, "HU"),

    # Bulgaria anchors
    (42.6977, 23.3219, "BG"), (43.2141, 27.9147, "BG"),
    (42.1354, 24.7453, "BG"), (42.5048, 25.9786, "BG"),

    # Denmark anchors
    (55.6761, 12.5683, "DK"), (56.1562, 10.2107, "DK"),
    (55.4038, 10.4024, "DK"), (57.0488, 9.9217, "DK"),

    # Mexico anchors
    (19.4326, -99.1332, "MX"), (25.6866, -100.3161, "MX"),
    (20.6597, -103.3496, "MX"), (21.1619, -86.8515, "MX"),

    # Argentina anchors
    (-34.6037, -58.3816, "AR"), (-31.4201, -64.1888, "AR"),
    (-32.9468, -60.6393, "AR"), (-38.7196, -62.2664, "AR"),

    # Colombia anchors
    (4.7110, -74.0721, "CO"), (6.2442, -75.5812, "CO"),
    (10.4806, -66.9036, "CO"), (3.4372, -76.5225, "CO"),

    # Peru anchors
    (-12.0464, -77.0428, "PE"), (-16.4090, -71.5375, "PE"),
    (-13.1631, -74.2244, "PE"), (-8.1106, -79.0389, "PE"),

    # Chile anchors
    (-33.4489, -70.6693, "CL"), (-36.8269, -73.0498, "CL"),
    (-41.4692, -72.9468, "CL"), (-23.6514, -70.4016, "CL"),

    # Ecuador anchors
    (-0.1807, -78.4678, "EC"), (-2.1960, -79.8862, "EC"),
    (-1.2416, -78.6183, "EC"), (-2.8969, -79.0040, "EC"),

    # Guatemala anchors
    (14.6349, -90.5069, "GT"), (15.5000, -88.0500, "GT"),
    (14.5384, -91.6788, "GT"), (14.8564, -90.2893, "GT"),

    # Costa Rica anchors
    (9.9281, -84.0907, "CR"), (10.0005, -84.1226, "CR"),
    (10.9760, -85.5364, "CR"), (9.9927, -84.2080, "CR"),

    # Paraguay anchors
    (-25.2637, -57.5759, "PY"), (-25.5070, -54.6104, "PY"),
    (-23.4039, -57.4270, "PY"), (-27.3272, -55.8479, "PY"),

    # Bolivia anchors
    (-16.5000, -68.1500, "BO"), (-17.7833, -63.1825, "BO"),
    (-19.0328, -65.2602, "BO"), (-14.8294, -64.9203, "BO"),

    # --- Auto-generated centroid anchors for all countries ---
    # Asia
    (33.93911, 67.70995, "AF"), (40.0691, 45.0382, "AM"),
    (40.1431, 47.5769, "AZ"), (26.0667, 50.5577, "BH"),
    (23.685, 90.3563, "BD"), (27.5142, 90.4336, "BT"),
    (4.5353, 114.7277, "BN"), (12.5657, 104.991, "KH"),
    (35.8617, 104.1954, "CN"), (42.3154, 43.3569, "GE"),
    (-0.7893, 113.9213, "ID"), (32.4279, 53.688, "IR"),
    (33.2232, 43.6793, "IQ"), (31.0461, 34.8516, "IL"),
    (36.2048, 138.2529, "JP"), (30.5852, 36.2384, "JO"),
    (48.0196, 66.9237, "KZ"), (29.3117, 47.4818, "KW"),
    (41.2044, 74.7661, "KG"), (19.8563, 102.4955, "LA"),
    (33.8547, 35.8623, "LB"), (4.2105, 101.9758, "MY"),
    (3.2028, 73.2207, "MV"), (46.8625, 103.8467, "MN"),
    (21.9162, 95.956, "MM"), (28.3949, 84.124, "NP"),
    (40.3399, 127.5101, "KP"), (21.5126, 55.9233, "OM"),
    (30.3753, 69.3451, "PK"), (31.9522, 35.2332, "PS"),
    (12.8797, 121.774, "PH"), (25.3548, 51.1839, "QA"),
    (23.8859, 45.0792, "SA"), (35.9078, 127.7669, "KR"),
    (7.8731, 80.7718, "LK"), (34.8021, 38.9968, "SY"),
    (23.6978, 120.9605, "TW"), (38.861, 71.2761, "TJ"),
    (15.87, 100.9925, "TH"), (-8.8742, 125.7275, "TL"),
    (38.9637, 35.2433, "TR"), (38.9697, 59.5563, "TM"),
    (23.4241, 53.8478, "AE"), (41.3775, 64.5853, "UZ"),
    (14.0583, 108.2772, "VN"), (15.5527, 48.5164, "YE"),

    # Africa
    (28.0339, 1.6596, "DZ"), (-11.2027, 17.8739, "AO"),
    (9.3077, 2.3158, "BJ"), (-22.3285, 24.6849, "BW"),
    (12.2383, -1.5616, "BF"), (-3.3731, 29.9189, "BI"),
    (16.5388, -23.0418, "CV"), (6.6111, 20.9394, "CF"),
    (15.4542, 18.7322, "TD"), (-11.6455, 43.3333, "KM"),
    (7.54, -5.5471, "CI"), (-4.0383, 21.7587, "CD"),
    (11.8251, 42.5903, "DJ"), (1.6508, 10.2679, "GQ"),
    (15.1794, 39.7823, "ER"), (-26.5225, 31.4659, "SZ"),
    (-0.8037, 11.6094, "GA"), (13.4432, -15.3101, "GM"),
    (9.9456, -9.6966, "GN"), (11.8037, -15.1804, "GW"),
    (-29.61, 28.2336, "LS"), (6.4281, -9.4295, "LR"),
    (26.3351, 17.2283, "LY"), (-18.7669, 46.8691, "MG"),
    (-13.2543, 34.3015, "MW"), (17.5707, -3.9962, "ML"),
    (21.0079, -10.9408, "MR"), (-20.3484, 57.5522, "MU"),
    (31.7917, -7.0926, "MA"), (-18.6657, 35.5296, "MZ"),
    (-22.9576, 18.4904, "NA"), (17.6078, 8.0817, "NE"),
    (-0.228, 15.8277, "CG"), (-1.9403, 29.8739, "RW"),
    (14.4974, -14.4524, "SN"), (-4.6796, 55.492, "SC"),
    (8.4606, -11.7799, "SL"), (5.1521, 46.1996, "SO"),
    (6.877, 31.307, "SS"), (8.6195, 0.8248, "TG"),
    (33.8869, 9.5375, "TN"), (1.3733, 32.2903, "UG"),
    (24.2155, -12.8858, "EH"), (-13.1339, 27.8493, "ZM"),
    (-19.0154, 29.1549, "ZW"),

    # Europe
    (41.1533, 20.1683, "AL"), (47.5162, 14.5501, "AT"),
    (53.7098, 27.9534, "BY"), (50.8503, 4.3517, "BE"),
    (43.9159, 17.6791, "BA"), (45.1, 15.2, "HR"),
    (35.1264, 33.4299, "CY"), (49.8175, 15.473, "CZ"),
    (58.5953, 25.0136, "EE"), (61.9241, 25.7482, "FI"),
    (64.9631, -19.0208, "IS"), (53.1424, -7.6921, "IE"),
    (42.6026, 20.903, "XK"), (56.8796, 24.6032, "LV"),
    (55.1694, 23.8813, "LT"), (49.8153, 6.1296, "LU"),
    (35.9375, 14.3754, "MT"), (47.4116, 28.3699, "MD"),
    (42.7087, 19.3744, "ME"), (41.6086, 21.7453, "MK"),
    (60.472, 8.4689, "NO"), (39.3999, -8.2245, "PT"),
    (61.524, 105.3188, "RU"), (44.0165, 21.0059, "RS"),
    (48.669, 19.699, "SK"), (46.1512, 14.9955, "SI"),
    (60.1282, 18.6435, "SE"), (46.8182, 8.2275, "CH"),

    # North America
    (25.0343, -77.3963, "BS"), (13.1939, -59.5432, "BB"),
    (17.1899, -88.4976, "BZ"), (21.5218, -77.7812, "CU"),
    (18.7357, -70.1627, "DO"), (13.7942, -88.8965, "SV"),
    (18.9712, -72.2852, "HT"), (15.2, -86.2419, "HN"),
    (18.1096, -77.2975, "JM"), (12.8654, -85.2072, "NI"),
    (8.538, -80.7821, "PA"), (10.6918, -61.2225, "TT"),

    # South America
    (4.8604, -58.9302, "GY"), (3.9193, -56.0278, "SR"),
    (-32.5228, -55.7658, "UY"), (6.4238, -66.5897, "VE"),

    # Oceania
    (-25.2744, 133.7751, "AU"), (-17.7134, 178.065, "FJ"),
    (-3.3704, -168.734, "KI"), (7.1315, 171.1845, "MH"),
    (7.4256, 150.5508, "FM"), (-0.5228, 166.9315, "NR"),
    (-40.9006, 174.886, "NZ"), (7.515, 134.5825, "PW"),
    (-6.315, 143.9555, "PG"), (-13.759, -172.1046, "WS"),
    (-9.6457, 160.1562, "SB"), (-21.179, -175.1982, "TO"),
    (-7.1095, 177.6493, "TV"), (-15.3767, 166.9592, "VU"),
]


# ---------------------------------------------------------------------------
# Continent detection
# ---------------------------------------------------------------------------

CONTINENT_CONFIG_PATH = "apps/location/continent_config.json"


def _load_continent_config() -> list:
    return _load_json(CONTINENT_CONFIG_PATH).get("continents", [])


def resolve_continent(lat: float, lon: float) -> Optional[Continent]:
    """
    Detect continent from lat/lon using bounding boxes.
    Returns Continent model instance or None if no match.
    """
    configs = _load_continent_config()
    best_match = None
    for cc in configs:
        bb = cc["bounding_box"]
        if bb["lat_min"] <= lat <= bb["lat_max"] and bb["lon_min"] <= lon <= bb["lon_max"]:
            try:
                return Continent.objects.get(code=cc["code"])
            except Continent.DoesNotExist:
                if best_match is None:
                    best_match = cc["code"]
    if best_match:
        return Continent.objects.filter(code=best_match).first()
    return None


# ---------------------------------------------------------------------------
# Country detection
# ---------------------------------------------------------------------------

COUNTRY_CONFIG_PATH = "apps/location/country_config.json"


def _load_country_config() -> list:
    return _load_json(COUNTRY_CONFIG_PATH).get("countries", [])


def resolve_country(lat: float, lon: float, continent: Optional[Continent] = None) -> Optional[Country]:
    """
    Find nearest country by anchor points.
    If continent is known, restricts search to countries in that continent.
    """
    qs = Country.objects.all()
    if continent:
        qs = qs.filter(continent=continent)

    country_codes = set(qs.values_list("code", flat=True))

    best_code, best_dist = None, float("inf")
    for alat, alon, code in COUNTRY_ANCHORS:
        if code not in country_codes:
            continue
        d = _haversine_km(lat, lon, alat, alon)
        if d < best_dist:
            best_dist, best_code = d, code

    if best_code:
        return qs.filter(code=best_code).first()

    # Fallback: nearest by centroid
    best_country, best_dist = None, float("inf")
    for country in qs:
        d = _haversine_km(lat, lon, country.centroid_lat, country.centroid_lon)
        if d < best_dist:
            best_dist, best_country = d, country

    return best_country


def get_confidence(dist_km: float) -> dict:
    if dist_km < 100:
        return {"level": "high", "note": "Very close to a known anchor — reliable match."}
    elif dist_km < 300:
        return {"level": "medium", "note": "Moderate distance from nearest anchor — likely correct."}
    else:
        return {"level": "low", "note": "Far from any anchor — nearest match used."}


# ---------------------------------------------------------------------------
# Admin division resolution
# ---------------------------------------------------------------------------

def resolve_admin_division(
    lat: float, lon: float, country: Country, level_name: str = ""
) -> Optional[AdminDivision]:
    """
    Find nearest admin division for a given country at a given level.
    If level_name is empty, finds the top-level division.
    """
    qs = AdminDivision.objects.filter(country=country)
    if level_name:
        qs = qs.filter(level_name=level_name)
    else:
        # Top-level: first level in the admin hierarchy for this country
        configs = _load_country_config()
        for c in configs:
            if c["code"] == country.code and c.get("admin_hierarchy"):
                top_level = c["admin_hierarchy"][0]
                qs = qs.filter(level_name=top_level)
                break

    best_div, best_dist = None, float("inf")
    for div in qs:
        if div.centroid_lat is None or div.centroid_lon is None:
            continue
        d = _haversine_km(lat, lon, div.centroid_lat, div.centroid_lon)
        if d < best_dist:
            best_dist, best_div = d, div

    return best_div


def get_admin_hierarchy(country_code: str) -> list:
    """Return the admin hierarchy levels for a country, e.g. ['State', 'District']."""
    configs = _load_country_config()
    for c in configs:
        if c["code"] == country_code:
            return c.get("admin_hierarchy", [])
    return []


# ---------------------------------------------------------------------------
# Full location resolution pipeline
# ---------------------------------------------------------------------------

def resolve_location_global(lat: float, lon: float) -> dict:
    """
    Full pipeline: lat/lon → continent → country → admin division.
    Returns a dict with all resolved entities, or None for unresolvable.

    Returns:
        {
            "continent": Continent | None,
            "country": Country | None,
            "admin_division": AdminDivision | None,
            "admin_hierarchy": [str],
            "distance_km": float,
            "confidence": str,
            "confidence_note": str,
        }
    """
    continent = resolve_continent(lat, lon)
    country = resolve_country(lat, lon, continent)

    if not country:
        return {
            "continent": continent,
            "country": None,
            "admin_division": None,
            "admin_hierarchy": [],
            "distance_km": 0.0,
            "confidence": "unknown",
            "confidence_note": "Could not determine location from coordinates.",
        }

    # Calculate distance to country centroid for confidence
    dist = _haversine_km(lat, lon, country.centroid_lat, country.centroid_lon)
    conf = get_confidence(dist)

    admin_div = resolve_admin_division(lat, lon, country)
    hierarchy = get_admin_hierarchy(country.code)

    return {
        "continent": continent,
        "country": country,
        "admin_division": admin_div,
        "admin_hierarchy": hierarchy,
        "distance_km": round(dist, 1),
        "confidence": conf["level"],
        "confidence_note": conf["note"],
    }


# ---------------------------------------------------------------------------
# Dataset path resolution
# ---------------------------------------------------------------------------

def get_country_dataset_path(country_code: str) -> Optional[Path]:
    """Return the dataset directory path for a given country code."""
    configs = _load_country_config()
    for c in configs:
        if c["code"] == country_code:
            path_str = c.get("dataset_path", "")
            if path_str:
                return Path(settings.BASE_DIR) / path_str
    return None


def discover_countries() -> list:
    """Return list of country codes that have dataset folders."""
    registry = _load_json("data/continent_registry.json")
    discovered = []
    for cont_code, cont_info in registry.get("continents", {}).items():
        cont_path = Path(settings.BASE_DIR) / cont_info["path"]
        if cont_path.exists():
            for country_dir in sorted(cont_path.iterdir()):
                if country_dir.is_dir():
                    discovered.append({
                        "continent_code": cont_code,
                        "country_name": country_dir.name,
                        "path": str(country_dir),
                    })
    return discovered
