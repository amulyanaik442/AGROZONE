# AgroZone — Crop Recommendation System

Rule-based deterministic crop recommendation engine built with Django.
Takes soil health card values + location → returns top 5 crops.

---
# AgroZone — Project Walkthrough (For Someone New to the Codebase)

This document explains **what AgroZone does and why every folder/file exists**, written so you can walk a senior through the project without assuming they've seen it before.

---

## 1. What is AgroZone, in one sentence?

AgroZone is a **Django web application** that takes a farmer's soil test values (like pH, nitrogen, potassium) plus their location, and tells them the **top 5 crops** best suited to grow — using a transparent, rule-based scoring system (no machine learning, no black box).

**Input:** Soil health card numbers + latitude/longitude (or state name)
**Output:** Ranked list of crops with scores and explanations of why each crop scored what it did

Think of it as a "soil report → crop advice" calculator, built so every recommendation can be explained and audited (important for something used by real farmers/agri-businesses).

---

## 2. Why rule-based instead of ML?

This is worth mentioning to a senior because it's a deliberate design choice:
- **Explainability** — every score can be broken down gate-by-gate ("this crop lost points because Sulphur was low"), which builds trust with agronomists and farmers.
- **No training data dependency** — works correctly from day one; doesn't need thousands of labeled examples.
- **Deterministic** — same input always gives the same output, which matters for a decision-support tool in agriculture.

---

## 3. The Big Picture: How a Request Flows Through the System

```
Farmer submits soil values + location
            │
            ▼
   GATE 1 — LOCATION RESOLUTION
   Find nearest Indian state from lat/lon (or use state name directly)
   → Load only the crops relevant to that state
            │
            ▼
   GATE 2 — pH HARD FILTER
   If soil pH is outside a crop's acceptable range → crop is eliminated entirely
            │
            ▼
   GATE 3 — Organic Carbon + Electrical Conductivity (15 points)
            │
            ▼
   GATE 4 — Macronutrients: N, P, K, S (55 points)
            │
            ▼
   GATE 5 — Micronutrients: Fe, Mn, Cu, Zn, B, Ca, Mg (30 points)
            │
            ▼
   SORT results by score → return TOP 5 crops with full score breakdown
```

Every crop that survives Gate 2 gets scored out of 100 points across Gates 3-5. The scoring logic itself is simple and consistent everywhere:
- Value falls **inside** the crop's ideal range → full points
- Value falls **outside** the range → points decay linearly the further off it is
- Value is **missing** → neutral half-credit (so one missing reading doesn't unfairly sink a crop)

---

## 4. Folder-by-Folder, File-by-File Breakdown

### 📁 `data/`
Holds the **raw source dataset**.
- `India_State_Wise_Crops_Final.xlsx` — an Excel sheet with 1,856 crop records across 29 Indian states, including each crop's ideal soil parameter ranges. This is the "knowledge base" the whole system is built on. It gets loaded into the database once, via a management command (see below).

### 📁 `core/`
This is the **Django project's control room** — not a Django "app" with business logic, but the global configuration that ties every app together.
- `settings.py` — central configuration: installed apps, database settings, templates folder location, static files config, etc.
- `urls.py` — the **top-level router**. It doesn't define page logic itself; it says "any URL starting with `/api/v1/...` or `/recommend/...` gets forwarded to the relevant app's own urls.py."
- `wsgi.py` — the entry point a production web server (like Gunicorn) uses to actually run the Django app. You won't touch this often; it's boilerplate Django needs to serve traffic.

### 📁 `apps/`
This is where the actual **business logic** lives, split into focused sub-apps (standard Django practice — each app has one clear responsibility).

#### 📁 `apps/location/`
Responsible for turning **coordinates into a usable region**.
- `models.py` — defines the `State` and `Zone` database tables (an agroclimatic zone groups multiple states with similar climate/soil behavior).
- `services.py` — contains the **haversine distance formula** to find which state's center-point is geographically closest to the farmer's given lat/lon. This is Gate 1 in the flow above.
- `serializers.py` — converts `State`/`Zone` database objects into JSON for the API (and validates incoming JSON back into Python objects).
- `views.py` — the actual API endpoints for this app (e.g., list all states, list all zones, resolve lat/lon → state).
- `urls.py` — maps specific URL paths (like `/api/v1/location/states/`) to the functions in `views.py`.

#### 📁 `apps/crops/`
Owns the **crop database itself** — the 1,856 crops and their ideal parameter ranges.
- `models.py` — defines the `Crop` table with all 14 soil parameters (pH, OC, EC, N, P, K, S, Fe, Mn, Cu, Zn, B, Ca, Mg) plus metadata (name, category, notes, state, zone).
- `serializers.py` — converts `Crop` objects to/from JSON for the API.
- `views.py` — API endpoint to browse/filter the crop database directly (`/api/v1/crops/`).
- `urls.py` — routes for this app's endpoints.
- `management/commands/load_crops.py` — a **custom Django command** (`python manage.py load_crops`) that reads the Excel file from `data/` and populates the database. This is the "import script" — safe to re-run any time to refresh the data (clears and reloads by default, or can append with `--no-clear`).

#### 📁 `apps/engine/`
The **brain of the whole project** — pure calculation logic, with no database or web concerns mixed in.
- `rule_engine.py` — implements Gates 2 through 5: the pH filter, and the point-scoring math for OC/EC, macronutrients, and micronutrients. This file is intentionally "pure Python" (no Django-specific code) so the scoring logic is easy to test, reason about, and explain to a non-technical stakeholder.

#### 📁 `apps/recommendations/`
The **orchestration layer** — ties location, crops, and the engine together into one usable feature, and exposes it as both an API and a web page.
- `services.py` — the conductor: takes the farmer's input, calls `location` to resolve the state, pulls the relevant crops from `crops`, runs them through `rule_engine.py`, sorts the results, and returns the final top-5 list.
- `serializers.py` — shapes the final recommendation response (scores, deficiencies, confidence notes) into JSON.
- `views.py` — contains both the REST API view (`/api/v1/recommend/`) and the logic behind the browser-facing form/result pages.
- `urls.py` — routes for the JSON API.
- `ui_urls.py` — separate routes for the human-facing HTML pages (`/recommend/` and `/recommend/result/`), kept apart from the API routes for clarity.

### 📁 `templates/`
Plain HTML that Django fills in with data — this is what the **farmer/user actually sees** in a browser.
- `base.html` — the shared page skeleton (header, footer, common styling includes) that every other page extends, so you don't repeat the same HTML everywhere.
- `recommendations/form.html` — the input form where a user types in their soil values and location.
- `recommendations/result.html` — the results page: displays the top 5 crop cards, each with a visual score bar and a list of nutrient deficiencies.

### 📁 `static/`
Files served as-is to the browser (not processed by Django) — styling and interactivity.
- `css/main.css` — all the visual styling (layout, colors, score bar appearance).
- `js/main.js` — any client-side interactivity (form validation, dynamic score bar animation, etc.).

### 📄 Root-level files
- `manage.py` — Django's command-line utility. Every Django command (`runserver`, `migrate`, `load_crops`, `createsuperuser`) goes through this file.
- `requirements.txt` — the list of Python packages the project depends on (Django, Django REST Framework, openpyxl for Excel reading, etc.) — used by `pip install -r requirements.txt` to set up the environment.
- `db.sqlite3` — the actual SQLite database file (created automatically the first time you run `migrate`; not checked into version control usually since it's generated data).
- `.gitignore` — tells Git which files/folders to ignore (like `venv/`, `db.sqlite3`, `__pycache__/`).
- `.hintrc` — a linting config file (used by the "webhint" tool) for catching accessibility/best-practice issues in the front-end code.
- `README.md` — the original setup-and-usage README (installation steps, API examples, project structure) — this document you're reading now is a companion explainer, not a replacement for it.

---

## 5. How to Explain the Architecture Verbally (Elevator Version)

If your senior asks "walk me through it" out loud, here's the short version:

> "It's a Django project split into four focused apps. `location` figures out which Indian state a farmer is in from their GPS coordinates. `crops` owns the database of 1,856 crops and their ideal soil conditions. `engine` is pure scoring logic — no ML, just a deterministic point system across five gates: a hard pH cutoff, then soft scoring for organic carbon/EC, macronutrients, and micronutrients. `recommendations` is the glue that calls all three and exposes the result as both a JSON API and an HTML page. Everything's designed so any recommendation can be explained back to the farmer — you can literally see how many points a crop lost and why."

---

## 6. Quick Reference: Where to Look for What

| If you want to change...                            | Go to...                                                       |
|-----------------------------------------------------|----------------------------------------------------------------|
| The scoring formula / point weights                 | `apps/engine/rule_engine.py`                                   |
| How states/zones are matched to coordinates         | `apps/location/services.py`                                    |
| The crop dataset itself                             | `data/India_State_Wise_Crops_Final.xlsx`                       |
| How the Excel data gets imported                    | `apps/crops/management/commands/load_crops.py`                 |
| The API response format                             | `apps/recommendations/serializers.py`                          |
| The look of the results page                        | `templates/recommendations/result.html`, `static/css/main.css` |
| Global settings (database, installed apps)          | `core/settings.py`                                             |
| Top-level URL routing                               | `core/urls.py`                                                 |



## Quick Start (VS Code)

### 1. Create virtual environment
```bash
cd agrozone
python -m venv venv

# Windows PowerShell
venv\Scripts\Activate.ps1

# Mac/Linux
source venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run migrations
```bash
python manage.py migrate
```

### 4. Load crop data from Excel
```bash
python manage.py load_crops
```
Expected output:
```
Scanning zones…
  14 zones created.
  Andhra Pradesh: 78 crops loaded.
  ...
  West Bengal: 58 crops loaded.
✅  Done. 1856 crops across 29 states.
```

### 5. Create admin user (optional)
```bash
python manage.py createsuperuser
```

### 6. Run the server
```bash
python manage.py runserver
```

Open: http://127.0.0.1:8000

---

## URLs

| URL | Description |
|-----|-------------|
| http://127.0.0.1:8000/recommend/ | Soil input form (UI) |
| http://127.0.0.1:8000/recommend/result/ | Results page |
| http://127.0.0.1:8000/api/v1/recommend/ | REST API (POST) |
| http://127.0.0.1:8000/api/v1/location/states/ | List all states |
| http://127.0.0.1:8000/api/v1/location/zones/ | List agroclimatic zones |
| http://127.0.0.1:8000/api/v1/location/geocode/ | Resolve lat/lon → state |
| http://127.0.0.1:8000/api/v1/crops/ | Browse crop database |
| http://127.0.0.1:8000/admin/ | Django admin |

---

## API Usage

### POST /api/v1/recommend/

```bash
curl -X POST http://127.0.0.1:8000/api/v1/recommend/ \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 12.9716,
    "lon": 77.5946,
    "ph": 6.8,
    "oc": 0.65,
    "ec": 0.3,
    "n": 265,
    "p": 18,
    "k": 170,
    "s": 10,
    "fe": 14,
    "mn": 5.5,
    "cu": 1.0,
    "zn": 0.75,
    "b": 0.42,
    "ca": 12.0,
    "mg": 4.0
  }'
```

Or use state name directly (no lat/lon needed):
```bash
curl -X POST http://127.0.0.1:8000/api/v1/recommend/ \
  -H "Content-Type: application/json" \
  -d '{"state_name": "Karnataka", "ph": 6.8, "n": 265, "p": 18, "k": 170}'
```

### Response shape
```json
{
  "state": "Karnataka",
  "zone": "Southern Plateau & Hills Region",
  "distance_km": 312.4,
  "confidence": "medium",
  "confidence_note": "...",
  "crops_evaluated": 91,
  "crops_eliminated_by_ph": 12,
  "top_crops": [
    {
      "rank": 1,
      "crop_name": "Rice (Paddy)",
      "category": "Cereals & Millets",
      "zone_name": "Southern Plateau & Hills Region",
      "state_name": "Karnataka",
      "notes": "",
      "is_notable": false,
      "temp_range": "20-35°C",
      "total_score": 94.5,
      "max_score": 100.0,
      "score_pct": 94.5,
      "nutrient_deficiencies": ["Sulphur low (10 < 12)"],
      "param_scores": {
        "oc": {"score": 7.5, "max": 7.5, "pct": 100},
        "n":  {"score": 15.0, "max": 15.0, "pct": 100},
        ...
      }
    }
  ]
}
```

---

## Rule Engine — Decision Flow

```
INPUT: lat/lon (or state name) + pH + soil params
         │
         ▼
GATE 1: Location → nearest state → agroclimatic zone
         │
         ▼  Load all crops for that state
         │
         ▼
GATE 2: pH hard filter
         If soil.ph < crop.ph_lo OR soil.ph > crop.ph_hi → ELIMINATE
         │
         ▼  Remaining crops enter scoring
         │
GATE 3: OC + EC  →  15 pts (soft, never eliminates)
GATE 4: N, P2O5, K, S  →  55 pts (macronutrients)
GATE 5: Fe, Mn, Cu, Zn, B, Ca, Mg  →  30 pts (micronutrients)
         │
         ▼
SORT: score DESC → is_notable DESC → sheet_order ASC
         │
         ▼
OUTPUT: Top 5 crops with scores + deficiencies
```

### Scoring function (Gates 3-5, per parameter)
- Value inside [lo, hi] → **1.0** (full score)
- Value outside range → **linear decay**: `max(0, 1 - distance/width)`
- Missing value → **0.5** (neutral — doesn't reward or penalise)

---

## Project Structure

```
agrozone/
├── manage.py
├── requirements.txt
├── db.sqlite3              ← created after migrate
├── data/
│   └── India_State_Wise_Crops_Final.xlsx
├── core/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── location/           ← State, Zone models + geocoding service
│   │   ├── models.py
│   │   ├── services.py     ← haversine nearest-state resolver
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── urls.py
│   ├── crops/              ← Crop model (all 14 soil params)
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── management/commands/load_crops.py
│   ├── engine/
│   │   └── rule_engine.py  ← 5-gate scoring — pure Python, no ML
│   └── recommendations/
│       ├── services.py     ← orchestration layer
│       ├── serializers.py
│       ├── views.py        ← REST API + UI views
│       ├── urls.py         ← API routes
│       └── ui_urls.py      ← HTML routes
├── templates/
│   ├── base.html
│   └── recommendations/
│       ├── form.html       ← soil input form
│       └── result.html     ← top 5 crop cards + score bars
└── static/
    ├── css/main.css
    └── js/main.js
```

---

## Re-loading Data

Safe to re-run anytime — clears and reloads:
```bash
python manage.py load_crops
```

To append without clearing:
```bash
python manage.py load_crops --no-clear
```

---

## Next Steps (Phase 2)

- Replace centroid geocoding with district-level lookup table (~700 rows) for higher accuracy
- Add PostGIS polygon boundaries for precise point-in-polygon zone matching
- Add `/api/v1/crops/?state=Karnataka&category=Fruits` filtering
- Export recommendations as PDF
- Multi-language support (Hindi + regional)
