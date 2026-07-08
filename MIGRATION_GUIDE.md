# Migration Guide — Adding New Continents and Countries

This guide explains how to extend AgroZone to support additional continents and countries without modifying engine code.

---

## How to Add a New Continent

### 1. Add Bounding Box

Edit `apps/location/continent_config.json`:

```json
{
  "continents": [
    {
      "name": "Oceania",
      "code": "OC",
      "bounding_box": {"lat_min": -47.0, "lat_max": -10.0, "lon_min": 110.0, "lon_max": 180.0},
      "description": "Australia, New Zealand, Pacific Islands"
    }
  ]
}
```

### 2. Add to Registry

Edit `data/continent_registry.json`:

```json
{
  "continents": {
    "OC": {
      "name": "Oceania",
      "path": "data/Oceania"
    }
  }
}
```

### 3. Create Folder Structure

```
data/
└── Oceania/
    └── Australia/
        ├── country.json
        ├── crops/
        ├── administrative/
        └── soil/
```

No engine code changes needed.

---

## How to Add a New Country

### 1. Add Country Config

Edit `apps/location/country_config.json`:

```json
{
  "countries": [
    {
      "name": "Australia",
      "code": "AU",
      "continent_code": "OC",
      "centroid_lat": -25.2744,
      "centroid_lon": 133.7751,
      "admin_hierarchy": ["State", "Territory"],
      "dataset_path": "data/Oceania/Australia"
    }
  ]
}
```

### 2. Add Country Anchors

Edit `apps/location/geography_service.py` — add anchors to `COUNTRY_ANCHORS`:

```python
COUNTRY_ANCHORS = [
    # ... existing anchors ...
    (-33.8688, 151.2093, "AU"),  # Sydney
    (-37.8136, 144.9631, "AU"),  # Melbourne
    (-27.4698, 153.0251, "AU"),  # Brisbane
    (-31.9505, 115.8605, "AU"),  # Perth
    (-34.9285, 138.6007, "AU"),  # Adelaide
]
```

### 3. Create Dataset Folder

```
data/Oceania/Australia/
├── country.json
└── crops/
    └── Australia_Crops.xlsx
```

### 4. Create country.json

```json
{
  "name": "Australia",
  "code": "AU",
  "continent": "Oceania",
  "centroid_lat": -25.2744,
  "centroid_lon": 133.7751,
  "admin_hierarchy": ["State", "Territory"],
  "crop_excel_files": ["Australia_Crops.xlsx"]
}
```

### 5. Load Data

```bash
python manage.py load_global_crops --country Australia
```

No engine code changes needed.

---

## Required Folder Structure

```
data/<continent_name>/
└── <country_name>/
    ├── country.json              # Country metadata (required)
    ├── crops/                    # Crop Excel files (required)
    │   └── *.xlsx                # Excel files with columns:
    │                             #   Category, Crop Name, Notes, Zone,
    │                             #   OC, N, P2O5, K, S, Fe, Mn, Cu, Zn, B,
    │                             #   pH, EC, Ca, Mg, Temp
    ├── administrative/           # Admin division data (optional)
    └── soil/                     # Soil data (optional)
```

---

## Required Excel File Format

Excel files must have the following columns (0-indexed):

| Col | Field | Description |
|-----|-------|-------------|
| 0 | Category | e.g. "Cereals & Millets" |
| 1 | Crop Name | e.g. "Rice (Paddy)" |
| 2 | Notes | Optional notes |
| 3 | Zone | Agroclimatic zone name |
| 4 | OC | Organic Carbon range ("0.5-0.8") |
| 5 | N | Nitrogen range ("200-280") |
| 6 | P | P2O5 range ("15-25") |
| 7 | K | Potassium range ("150-200") |
| 8 | S | Sulphur range ("8-15") |
| 9 | Fe | Iron range ("10-20") |
| 10 | Mn | Manganese range ("4-8") |
| 11 | Cu | Copper range ("0.8-1.4") |
| 12 | Zn | Zinc range ("0.6-1.0") |
| 13 | B | Boron range ("0.3-0.6") |
| 14 | pH | pH range ("5.5-7.5") |
| 15 | EC | EC range ("0.2-0.5") |
| 16 | Ca | Calcium range ("9-15") |
| 17 | Mg | Magnesium range ("3-6") |
| 18 | Temp | Temperature range ("20-35°C") |

---

## Administrative Hierarchy Configuration

The `admin_hierarchy` array in `country.json` defines levels from highest to lowest:

| Country | Hierarchy |
|---------|-----------|
| India | `["State", "District", "Taluk"]` |
| USA | `["State", "County"]` |
| Brazil | `["State", "Municipality"]` |
| Nigeria | `["State", "Local Government Area"]` |
| Kenya | `["County", "Sub-county"]` |
| South Africa | `["Province", "District", "Municipality"]` |
| France | `["Region", "Department"]` |
| Germany | `["State", "District"]` |
| Italy | `["Region", "Province", "Municipality"]` |

---

## Verification Checklist

After adding a new country:

1. Run `python manage.py check` — no errors
2. Run `python manage.py load_global_crops --country <Name>` — loads data
3. Run `python manage.py test apps.location` — all continent/country tests pass
4. Run `python manage.py test apps.engine.tests_global` — scoring tests pass
5. Test API: `POST /api/v1/recommend/` with new country coordinates
6. Test API: `POST /api/v1/location/global-geocode/` with new country coordinates
