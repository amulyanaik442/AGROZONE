# Technical Architecture — AgroZone Multi-Continent Extension

## Overview

AgroZone's multi-continent extension generalizes the India-specific recommendation engine into a global, configuration-driven system. The core rule engine is unchanged — only the location resolution and data loading layers have been extended.

---

## New Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Client Request                       │
│  POST /api/v1/recommend/  {lat, lon, ph, n, p, k, ...}  │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Recommendation Service                      │
│              apps/recommendations/services.py            │
│                                                         │
│  ┌─ India coordinates? ─→ India pipeline (unchanged) ─┐ │
│  │                     (validate_india_bounds +         │ │
│  │                      resolve_location)              │ │
│  │                                                     │ │
│  └─ Global coordinates? ─→ Global pipeline ───────────┘ │
│                          (geography_service)             │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Geography Service                           │
│              apps/location/geography_service.py           │
│                                                         │
│  1. Continent Detection (bounding boxes)                 │
│  2. Country Detection (anchor nearest-match)             │
│  3. Admin Division Resolution (hierarchy-aware)          │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Crop Dataset Loader                         │
│              apps/crops/management/commands/             │
│                                                         │
│  load_crops.py (India, unchanged)                       │
│  load_global_crops.py (generic, config-driven)           │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Rule Engine (unchanged)                    │
│              apps/engine/rule_engine.py                  │
│                                                         │
│  Gate 2: pH scoring (20 pts)                            │
│  Gate 3: OC + EC (10 pts)                               │
│  Gate 4: N, P, K, S (35 pts)                            │
│  Gate 5: Fe, Mn, Cu, Zn, B, Ca, Mg (20 pts)             │
│  Weather: temperature match (15 pts)                     │
│  Category diversity enforcement                         │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Response                                   │
│  Top 5 crops with scores, deficiencies, weather          │
└─────────────────────────────────────────────────────────┘
```

---

## Request Lifecycle

### India Request (backward-compatible path)

```
POST /api/v1/recommend/ {lat: 12.97, lon: 77.59, ph: 6.8, ...}
  ↓
SoilInputSerializer validates
  ↓
validate_india_bounds(lat, lon) → True
  ↓
resolve_location(lat, lon) → State, distance, confidence
  ↓
Crop.objects.filter(state=state) → India crops
  ↓
rank_crops(crops, soil, weather) → top 5
  ↓
Response (unchanged format + continent/country fields)
```

### Global Request (new path)

```
POST /api/v1/recommend/ {lat: 40.71, lon: -74.00, ph: 6.8, ...}
  ↓
SoilInputSerializer validates
  ↓
validate_india_bounds(lat, lon) → False
  ↓
resolve_location_global(lat, lon)
  → resolve_continent(40.71, -74.00) → America
  → resolve_country(40.71, -74.00, America) → United States
  → resolve_admin_division(40.71, -74.00, US) → New York
  ↓
Crop.objects.filter(country=US) → US crops
  ↓
rank_crops(crops, soil, weather) → top 5 (same engine)
  ↓
Response (same format, with continent/country)
```

---

## Dataset Loading Lifecycle

### India (unchanged)

```
python manage.py load_crops
  ↓
Reads settings.CROPS_EXCEL_PATH → data/India_State_Wise_Crops_Final.xlsx
  ↓
Creates Continent("Asia"), Country("India")
  ↓
Creates AgroclimateZone records (14 zones)
  ↓
For each sheet (29 states):
  → Create State with country=India
  → Parse crops from rows
  → Bulk create Crop records with continent + country + state
```

### Global (new)

```
python manage.py load_global_crops
  ↓
Reads data/continent_registry.json
  ↓
For each continent → each country folder:
  → Create Continent (if not exists)
  → Load country.json config
  → Find Excel files in crops/ subfolder
  → Parse columns (same format as India)
  → Create Country + AdminDivision records
  → Bulk create Crop records with continent + country + admin_division
```

---

## Extension Points

| Extension Point | File | What to Change |
|----------------|------|----------------|
| New continent | `apps/location/continent_config.json` | Add bounding box |
| New country | `apps/location/country_config.json` | Add metadata + admin hierarchy |
| New country anchors | `apps/location/geography_service.py` | Add (lat, lon, code) tuples |
| New dataset | `data/<continent>/<country>/crops/` | Add Excel files |
| New admin hierarchy | `data/<continent>/<country>/country.json` | Set admin_hierarchy array |
| New scoring rules | `apps/engine/rule_engine.py` | Modify gates (pure Python) |
| New weather source | `apps/engine/weather_service.py` | Replace API client |
| New API endpoint | `apps/location/views.py` + `urls.py` | Add view + route |

---

## Folder Structure (Data)

```
data/
├── continent_registry.json        # Maps continents to filesystem paths
├── Asia/
│   └── India/
│       ├── country.json            # Country metadata + config
│       ├── crops/                  # Crop Excel files
│       ├── administrative/         # Admin division boundaries
│       └── soil/                   # Soil data
├── Africa/
│   ├── Nigeria/                    # Same structure
│   ├── Kenya/
│   └── South_Africa/
├── America/
│   ├── USA/
│   ├── Brazil/
│   └── Canada/
└── Europe/
    ├── France/
    ├── Germany/
    └── Italy/
```

---

## Configuration Files

### continent_config.json
Defines bounding boxes for continent detection from lat/lon.

### country_config.json
Maps country codes to names, centroids, admin hierarchies, and dataset paths.

### continent_registry.json
Maps continent codes to filesystem paths for dataset discovery.

### country.json (per country in data/)
Per-country metadata including admin hierarchy and expected Excel filenames.

---

## Key Design Decisions

1. **No engine changes**: The rule engine (`apps/engine/rule_engine.py`) was already country-agnostic. It accepts any list of crop objects regardless of origin.

2. **Backward compatibility**: The India pipeline (`resolve_location`, `validate_india_bounds`, state-based crop filtering) is completely untouched. India API requests follow the exact same code path.

3. **Configuration-driven**: New countries can be added via JSON config files. No Python code changes needed for adding countries.

4. **Anchor-based matching**: Uses multi-point anchors for large/irregular countries (same approach as the existing India implementation).

5. **Graceful degradation**: Weather is optional (neutral 50% score if unavailable). Missing soil params get neutral 0.75 score.
