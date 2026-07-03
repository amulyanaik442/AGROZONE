# AgroZone — Crop Recommendation System

Rule-based deterministic crop recommendation engine built with Django.
Takes soil health card values + location → returns top 5 crops.

---

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
