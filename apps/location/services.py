"""
Location Service
----------------
Resolves (lat, lon) to the nearest Indian state using a multi-anchor
approach: each large/irregular state has several city anchors so that
any point in the state matches correctly — not just points near the
geographic centroid.

Upgrade path: replace with district-centroid table (~700 rows) or
PostGIS point-in-polygon for even higher precision.
"""
import math
from .models import State

# ---------------------------------------------------------------------------
# Anchor table — (lat, lon, state_name)
# Large states like Karnataka, Maharashtra, UP, Rajasthan have 4-6 anchors
# so that any city in the state resolves correctly.
# ---------------------------------------------------------------------------
STATE_ANCHORS = [
    # Andhra Pradesh
    (15.8281, 78.0373, "Andhra Pradesh"),
    (13.6288, 79.4192, "Andhra Pradesh"),
    (16.5062, 80.6480, "Andhra Pradesh"),
    (17.6868, 83.2185, "Andhra Pradesh"),

    # Arunachal Pradesh
    (27.0844, 93.6053, "Arunachal Pradesh"),
    (28.6179, 94.9187, "Arunachal Pradesh"),

    # Assam
    (26.1445, 91.7362, "Assam"),
    (26.7509, 94.2037, "Assam"),
    (24.8333, 92.7789, "Assam"),

    # Bihar
    (25.5941, 85.1376, "Bihar"),
    (25.1200, 85.5200, "Bihar"),
    (26.1197, 86.9942, "Bihar"),

    # Chhattisgarh
    (21.2514, 81.6296, "Chhattisgarh"),
    (22.0796, 82.1409, "Chhattisgarh"),
    (18.8667, 82.0667, "Chhattisgarh"),

    # Goa
    (15.4909, 73.8278, "Goa"),
    (15.2993, 74.1240, "Goa"),

    # Gujarat
    (23.0225, 72.5714, "Gujarat"),
    (21.1702, 72.8311, "Gujarat"),
    (22.3039, 70.8022, "Gujarat"),
    (23.2156, 69.6669, "Gujarat"),

    # Haryana
    (29.0588, 76.0856, "Haryana"),
    (30.7333, 76.7794, "Haryana"),
    (28.4595, 77.0266, "Haryana"),

    # Himachal Pradesh
    (31.1048, 77.1734, "Himachal Pradesh"),
    (32.2190, 76.3234, "Himachal Pradesh"),
    (31.5200, 76.9700, "Himachal Pradesh"),

    # Jammu & Kashmir
    (34.0837, 74.7973, "Jammu & Kashmir"),
    (32.7266, 74.8570, "Jammu & Kashmir"),
    (34.2929, 77.7324, "Jammu & Kashmir"),

    # Jharkhand
    (23.3441, 85.3096, "Jharkhand"),
    (22.8046, 86.2029, "Jharkhand"),
    (23.8133, 86.4395, "Jharkhand"),

    # Karnataka
    (12.9716, 77.5946, "Karnataka"),
    (15.3647, 75.1240, "Karnataka"),
    (12.2958, 76.6394, "Karnataka"),
    (15.8497, 74.4977, "Karnataka"),
    (17.3297, 76.8343, "Karnataka"),
    (13.3379, 77.1173, "Karnataka"),

    # Kerala
    (8.5241,  76.9366, "Kerala"),
    (10.8505, 76.2711, "Kerala"),
    (11.2588, 75.7804, "Kerala"),
    (9.9312,  76.2673, "Kerala"),

    # Madhya Pradesh
    (23.2599, 77.4126, "Madhya Pradesh"),
    (22.7196, 75.8577, "Madhya Pradesh"),
    (26.2183, 78.1828, "Madhya Pradesh"),
    (23.1637, 79.9411, "Madhya Pradesh"),
    (24.5854, 81.8750, "Madhya Pradesh"),

    # Maharashtra
    (19.0760, 72.8777, "Maharashtra"),
    (18.5204, 73.8567, "Maharashtra"),
    (20.0059, 73.7898, "Maharashtra"),
    (21.1458, 79.0882, "Maharashtra"),
    (17.6599, 75.9064, "Maharashtra"),
    (19.8762, 75.3433, "Maharashtra"),

    # Manipur
    (24.8170, 93.9368, "Manipur"),
    (25.0000, 93.7000, "Manipur"),

    # Meghalaya
    (25.5788, 91.8933, "Meghalaya"),
    (25.3000, 90.5200, "Meghalaya"),

    # Mizoram
    (23.7271, 92.7176, "Mizoram"),
    (22.9500, 92.8500, "Mizoram"),

    # Nagaland
    (25.6751, 94.1086, "Nagaland"),
    (26.3167, 94.6333, "Nagaland"),

    # Odisha
    (20.2961, 85.8245, "Odisha"),
    (19.8135, 85.8312, "Odisha"),
    (21.4669, 83.9812, "Odisha"),
    (18.8636, 82.7228, "Odisha"),

    # Punjab
    (30.9010, 75.8573, "Punjab"),
    (31.6340, 74.8723, "Punjab"),
    (30.3398, 76.3869, "Punjab"),

    # Rajasthan
    (26.9124, 75.7873, "Rajasthan"),
    (24.5854, 73.7125, "Rajasthan"),
    (26.4499, 74.6399, "Rajasthan"),
    (28.0229, 73.3119, "Rajasthan"),
    (26.3100, 73.0200, "Rajasthan"),
    (27.4850, 76.0000, "Rajasthan"),

    # Sikkim
    (27.3389, 88.6065, "Sikkim"),

    # Tamil Nadu
    (13.0827, 80.2707, "Tamil Nadu"),
    (9.9252,  78.1198, "Tamil Nadu"),
    (10.7905, 78.7047, "Tamil Nadu"),
    (11.6643, 78.1460, "Tamil Nadu"),
    (8.7139,  77.7567, "Tamil Nadu"),

    # Telangana
    (17.3850, 78.4867, "Telangana"),
    (18.0000, 79.5800, "Telangana"),
    (17.0005, 81.8040, "Telangana"),

    # Tripura
    (23.8315, 91.2868, "Tripura"),

    # Uttar Pradesh
    (26.8467, 80.9462, "Uttar Pradesh"),
    (27.1767, 78.0081, "Uttar Pradesh"),
    (25.3176, 82.9739, "Uttar Pradesh"),
    (28.6300, 77.2200, "Uttar Pradesh"),
    (29.9457, 77.5490, "Uttar Pradesh"),
    (26.4499, 80.3319, "Uttar Pradesh"),

    # Uttarakhand
    (30.3165, 78.0322, "Uttarakhand"),
    (29.9457, 78.1642, "Uttarakhand"),
    (29.3919, 79.4542, "Uttarakhand"),
    (30.0668, 79.0193, "Uttarakhand"),

    # West Bengal
    (22.5726, 88.3639, "West Bengal"),
    (23.2500, 87.0700, "West Bengal"),
    (26.7205, 88.3953, "West Bengal"),
    (24.0823, 88.2521, "West Bengal"),
]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two lat/lon points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def resolve_location(lat: float, lon: float) -> dict:
    """
    Given a latitude/longitude, find the nearest anchor point across all
    states and return that state plus a confidence note.
    """
    states_in_db = {s.name: s for s in State.objects.all()}
    if not states_in_db:
        raise RuntimeError("No states in DB. Run: python manage.py load_crops")

    best_state_name, best_dist = None, float("inf")
    for alat, alon, state_name in STATE_ANCHORS:
        d = haversine_km(lat, lon, alat, alon)
        if d < best_dist:
            best_dist, best_state_name = d, state_name

    # Fall back to centroid match if anchor state not in DB
    state_obj = states_in_db.get(best_state_name)
    if not state_obj:
        # Pick closest DB state by centroid
        for s in states_in_db.values():
            d = haversine_km(lat, lon, s.centroid_lat, s.centroid_lon)
            if d < best_dist:
                best_dist, state_obj = d, s

    if best_dist < 100:
        confidence, note = "high", "Very close to a known location anchor — reliable match."
    elif best_dist < 300:
        confidence, note = "medium", "Moderate distance from nearest anchor — likely correct, verify if near a state border."
    else:
        confidence, note = "low", "Far from any anchor — nearest match used, confirm state manually if results seem off."

    return {
        "state": state_obj,
        "distance_km": round(best_dist, 1),
        "confidence": confidence,
        "confidence_note": note,
    }


def validate_india_bounds(lat: float, lon: float) -> bool:
    """Rough bounding box — India spans ~6°N-37°N, 68°E-97°E."""
    return 6.0 <= lat <= 37.5 and 68.0 <= lon <= 97.5