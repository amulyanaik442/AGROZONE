# AgroZone — Multi-Continent Crop Recommendation + Crop Planning Engine

**Rule-based deterministic crop recommendation system** built with Django. Takes soil health values + GPS coordinates → returns the **top 5 best-suited crops** with full score breakdown and **crop planning guides** (duration, sowing season, water requirement, pests, fertilizers, harvest time).

Supports **187 countries across 6 continents** (Asia, Africa, Europe, North America, South America, Oceania) with a **configuration-driven architecture** — new countries can be added via JSON config files, no engine code changes needed.

---

## Features

- **Crop Recommendation** — 5-gate scoring system (pH, soil health, macronutrients, micronutrients, weather)
- **Crop Planning** — Instant crop guide with duration, sowing season, water needs, pest info, fertilizers, and harvest time
- **Live Weather** — Real-time temperature data from Open-Meteo API
- **Multi-Continent** — Works for 187 countries across 6 continents
- **India Backward-Compatible** — Full support for 29 Indian states with agroclimatic zones
- **Category Diversity** — Top 5 results guaranteed to come from different crop categories
- **Explainable Scores** — Every point is traceable gate-by-gate

---

## Why Rule-Based (Not ML)?

- **Explainability** — every point is traceable gate-by-gate ("this crop lost 15% because Sulphur is low"). Critical for agronomists and farmer adoption.
- **Zero training data** — works from day one across any country.
- **Deterministic** — same input → same output, essential for a decision-support tool.

---

## Request Lifecycle

```
Farmer submits soil values + coordinates
         │
         ▼
 GATE 1 — LOCATION RESOLUTION
         ├─ India coordinates → nearest Indian state (backward-compatible)
         └─ Global coordinates → continent → country → admin division
         │
         ▼  Load crops for that state/country (filtered by location)
         │
 GATE 2 — pH SOFT SCORING (20 pts, never eliminates)
 GATE 3 — OC + EC (10 pts)
 GATE 4 — N, P, K, S (35 pts)
 GATE 5 — Fe, Mn, Cu, Zn, B, Ca, Mg (20 pts)
 WEATHER — Temperature match (15 pts, graceful fallback)
         │
         ▼
 SORT: score DESC → is_notable DESC → sheet_order ASC
         │
         ▼
 TOP 5 CROPS → Crop Planning Enrichment
         │
         ▼
 RETURN: Top 5 crops with scores, deficiencies, weather context,
         and crop planning guides (duration, season, water, pests, etc.)
```

---

## Crop Planning Engine

After generating recommendations, the system enriches each crop with planning data from `World_Country_Wise_Crop_Database_UPDATED.xlsx`.

### How It Works

```
Top 5 recommended crops
         │
         ▼
 Crop Data Mapper (singleton, lazy-loads Excel)
         │
         ├─ Normalize crop name (remove parentheticals, lowercase)
         ├─ Map Indian local names → English equivalents
         │   (e.g., Ragi → Finger Millet, Jowar → Sorghum)
         ├─ Lookup by (country, crop_name) with cascading fallbacks
         │
         ▼
 Attach additional_info to each crop:
   • Crop Duration
   • Best Sowing Season
   • Water Requirement
   • Common Pests
   • Recommended Fertilizers
   • Harvest Time
```

### Crop Planning Data Flow

| Step | Description |
|------|-------------|
| 1 | User submits form → recommendation engine returns top 5 crops |
| 2 | `enrich_crop_recommendations()` called with crop list + country name |
| 3 | `CropDataMapper` looks up each crop in the master Excel database |
| 4 | Indian local names (Ragi, Jowar, Bajra) mapped to English equivalents |
| 5 | Planning data attached as `additional_info` dict to each crop |
| 6 | Result page renders expandable "Crop Guide" section for each crop |

---

## Folder Structure

```
agrozone/
├── manage.py
├── requirements.txt
├── data/                              ← Crop datasets (per continent/country)
│   ├── continent_registry.json        ← Filesystem discovery config
│   ├── India_State_Wise_Crops_Final.xlsx  ← India state-wise dataset
│   ├── World_Country_Wise_Crop_Database_UPDATED.xlsx  ← Master crop planning database
│   ├── Asia/{India,China,Japan,...}/
│   ├── Africa/{Nigeria,Kenya,South_Africa,...}/
│   ├── Europe/{France,Germany,UK,...}/
│   ├── North America/{US,Canada,Mexico,...}/
│   ├── South America/{Brazil,Argentina,Chile,...}/
│   └── Oceania/{Australia,New_Zealand,Fiji,...}/
├── core/                              ← Django project config
│   ├── settings.py
│   └── urls.py
├── apps/
│   ├── location/                      ← Geography models + services
│   │   ├── models.py                  ← Continent, Country, AdminDivision, State, Zone
│   │   ├── geography_service.py       ← Lat/lon → continent/country/division (config-driven)
│   │   ├── continent_config.json      ← Bounding boxes for continent detection
│   │   ├── country_config.json        ← ISO codes, centroids, admin hierarchies
│   │   ├── services.py                ← India nearest-state resolver (unchanged)
│   │   ├── views.py                   ← /api/v1/location/... + global endpoints
│   │   └── tests.py                   ← 20 continent/country/division tests
│   ├── crops/                         ← Crop model + dataset loaders
│   │   ├── models.py                  ← Crop with 14 soil params + continent/country FKs
│   │   ├── management/commands/
│   │   │   ├── load_crops.py          ← India dataset loader (backward-compatible)
│   │   │   └── load_global_crops.py   ← Generic multi-continent loader
│   │   └── admin.py
│   ├── engine/                        ← Scoring engine + crop planning
│   │   ├── rule_engine.py             ← 5-gate scoring — unchanged
│   │   ├── weather_service.py         ← Open-Meteo API client — unchanged
│   │   ├── crop_feature_engine.py     ← Entry point for crop planning enrichment
│   │   ├── crop_feature_service.py    ← Service layer for enrichment
│   │   ├── crop_data_mapper.py        ← Excel loader + lookup logic
│   │   └── crop_utils.py              ← Name normalization + Indian-to-English mapping
│   └── recommendations/               ← Orchestration layer
│       ├── services.py                ← India + global pipeline branching
│       ├── views.py                   ← REST API + HTML form views
│       └── urls.py
├── templates/                         ← HTML (Django templates)
│   ├── base.html
│   └── recommendations/{form,result}.html
└── static/
    ├── css/main.css
    └── js/main.js
```

---

## Quick Start

```bash
git clone https://github.com/amulyanaik442/AGROZONE.git
cd AGROZONE
python -m venv venv
venv\Scripts\Activate      # Windows
# source venv/bin/activate  # Mac/Linux

pip install -r requirements.txt
python manage.py migrate
python manage.py load_crops            # India: 1,856 crops across 29 states
python manage.py load_global_crops     # Global: 10,376 crops across 186 countries
python manage.py runserver
```

Open http://127.0.0.1:8000/recommend/

---

## URLs

### HTML UI
| URL | Description |
|-----|-------------|
| `/recommend/` | Soil input form |
| `/recommend/result/` | Top-5 results with crop planning guides |

### REST API
| Method | URL | Description |
|--------|-----|-------------|
| POST | `/api/v1/recommend/` | Get top 5 crops with planning data |
| GET | `/api/v1/location/states/` | List Indian states |
| GET | `/api/v1/location/zones/` | List agroclimatic zones |
| POST | `/api/v1/location/geocode/` | Resolve lat/lon → Indian state |
| GET | `/api/v1/location/continents/` | List all continents |
| GET | `/api/v1/location/countries/` | List all countries |
| GET | `/api/v1/location/admin-divisions/` | List admin divisions |
| POST | `/api/v1/location/global-geocode/` | Resolve lat/lon → continent/country/division |
| GET | `/api/v1/crops/` | Browse crop database |
| `/admin/` | Django admin |

---

## API Examples

### India request (backward-compatible)
```bash
curl -X POST http://127.0.0.1:8000/api/v1/recommend/ \
  -H "Content-Type: application/json" \
  -d '{"lat": 12.9716, "lon": 77.5946, "ph": 6.8, "n": 265, "p": 18, "k": 170}'
```

### Global request (same endpoint)
```bash
curl -X POST http://127.0.0.1:8000/api/v1/recommend/ \
  -H "Content-Type: application/json" \
  -d '{"lat": 6.5244, "lon": 3.3792, "ph": 6.5, "n": 80, "p": 30, "k": 80}'
```

### Resolve global coordinates
```bash
curl -X POST http://127.0.0.1:8000/api/v1/location/global-geocode/ \
  -H "Content-Type: application/json" \
  -d '{"lat": 48.8566, "lon": 2.3522}'
```

---

## Data Loading

| Command | What it loads | Safe to re-run? |
|---------|---------------|-----------------|
| `python manage.py load_crops` | India (1,856 crops, 29 states) | Yes — clears only India data |
| `python manage.py load_global_crops` | All 186 global countries | Yes — `--no-clear` by default |
| `python manage.py load_global_crops --country Nigeria` | Single country | Yes |
| `python manage.py load_global_crops --continent AF` | All African countries | Yes |

---

## Adding a New Country (No Code Changes Needed)

1. Add bounding box to `apps/location/continent_config.json` (if new continent)
2. Add entry to `apps/location/country_config.json` (name, ISO code, centroid, admin hierarchy)
3. Add anchor points to `COUNTRY_ANCHORS` in `apps/location/geography_service.py`
4. Create folder: `data/<Continent>/<Country>/crops/`
5. Place Excel file with columns: Category, Crop Name, Zone, OC, N, P, K, S, Fe, Mn, Cu, Zn, B, pH, EC, Ca, Mg, Temp
6. Run: `python manage.py load_global_crops --country <Name>`

See `MIGRATION_GUIDE.md` for detailed instructions.

---

## Current Dataset

| Continent | Countries + States | Crops |
|-----------|-------------------|-------|
| Asia | 47 countries | 3,048 |
| Africa | 56 countries | 3,691 |
| Europe | 43 countries | 2,586 |
| North America | 17 countries | 1,230 |
| South America | 12 countries | 767 |
| Oceania | 14 countries | 910 |
| India (state-wise) | 29 states | 1,856 |
| **Total** | **189 regions** | **12,232** |

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Rule-based scoring** | Explainable, deterministic, zero training data needed |
| **Backward-compatible India** | India pipeline, API format, and data loader untouched |
| **Config-driven geography** | New countries added via JSON + anchor tuples, not Python |
| **Optional weather** | Open-Meteo has no API key; graceful 50% neutral score on failure |
| **Soft pH scoring** | pH out-of-range scores 0.75 instead of elimination (better UX) |
| **Crop planning enrichment** | Separate from recommendation engine; graceful fallback for missing data |
| **Indian-to-English mapping** | Handles local crop names (Ragi, Jowar, Bajra) for global database lookup |
| **Category diversity** | Top 5 results from different categories prevent monoculture bias |
