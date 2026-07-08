# AgroZone — Multi-Continent Crop Recommendation Engine

**Rule-based deterministic crop recommendation system** built with Django. Takes soil health values + GPS coordinates → returns the **top 5 best-suited crops** with a full score breakdown.

Supports **40 countries across 4 continents** (Asia, Africa, Europe, America) with a **configuration-driven architecture** — new countries can be added via JSON config files, no engine code changes needed.

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
 RETURN: Top 5 crops with scores, deficiencies, weather context
```

### Scoring (per parameter)
| Condition | Score multiplier |
|-----------|-----------------|
| Value inside `[lo, hi]` | 1.0 (full) |
| Value outside range | `max(0, 1 - distance/width)` |
| Missing value | 0.75 (neutral) |
| pH out of range | 0.75 (soft — no hard elimination) |

---

## Folder Structure

```
agrozone/
├── manage.py
├── requirements.txt
├── data/                              ← Crop datasets (per continent/country)
│   ├── continent_registry.json        ← Filesystem discovery config
│   ├── Asia/India/
│   ├── Africa/{Nigeria,Kenya,...}/
│   ├── Europe/{France,Germany,...}/
│   └── America/{US,Brazil,...}/
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
│   ├── engine/                        ← Scoring engine (pure Python, no Django)
│   │   ├── rule_engine.py             ← 5-gate scoring — unchanged
│   │   ├── weather_service.py         ← Open-Meteo API client — unchanged
│   │   └── tests_global.py            ← 9 global scoring + India regression tests
│   └── recommendations/               ← Orchestration layer
│       ├── services.py                ← India + global pipeline branching
│       ├── views.py                   ← REST API + HTML form views
│       └── urls.py
├── templates/                         ← HTML (Django templates)
│   ├── base.html
│   └── recommendations/{form,result}.html
└── static/css/main.css
```

---

## Quick Start

```bash
git clone https://github.com/madhavihanchate/agrozone.git
cd agrozone
python -m venv venv
venv\Scripts\Activate      # Windows
# source venv/bin/activate  # Mac/Linux

pip install -r requirements.txt
python manage.py migrate
python manage.py load_crops            # India: 1,856 crops across 29 states
python manage.py load_global_crops     # Global: 1,614 crops across 38 countries
python manage.py runserver
```

Open http://127.0.0.1:8000/recommend/

---

## URLs

### HTML UI
| URL | Description |
|-----|-------------|
| `/recommend/` | Soil input form |
| `/recommend/result/` | Top-5 results page |

### REST API
| Method | URL | Description |
|--------|-----|-------------|
| POST | `/api/v1/recommend/` | Get top 5 crops |
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
| `python manage.py load_global_crops` | All global countries | Yes — `--no-clear` by default |
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

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **No engine changes** | `rule_engine.py` was already country-agnostic — takes any list of crops |
| **Backward-compatible India** | India pipeline, API format, and data loader untouched |
| **Config-driven geography** | New countries added via JSON + anchor tuples, not Python |
| **Optional weather** | Open-Meteo has no API key; graceful 50% neutral score on failure |
| **Soft pH scoring** | pH out-of-range scores 0.75 instead of elimination (better UX) |
| **Admin division → sheet name** | Each Excel sheet = one admin division (State/Province/Region) |

---

## Current Dataset

| Continent | Countries | Crops |
|-----------|-----------|-------|
| Asia | India (29 states) | 1,856 |
| Africa | 13 countries | 528 |
| Europe | 13 countries | 758 |
| America | 13 countries | 328 |
| **Total** | **40** | **3,470** |

---

## Pre-Existing Test Notes

6 tests in `apps.engine.tests` fail due to earlier engine updates (pH soft scoring, missing param 0.5→0.75). These are **not** regressions from the multi-continent extension. The corrected expectations are verified in `apps.engine.tests_global`.
