# Changelog — AgroZone Multi-Continent Extension

## v2.0.0 — Multi-Continent Support

### Files Modified

| File | Change |
|------|--------|
| `apps/location/models.py` | Added `Continent`, `Country`, `AdminDivision` models. Added `country` FK to `State` and `AgroclimateZone`. |
| `apps/location/serializers.py` | Added `ContinentSerializer`, `CountrySerializer`, `AdminDivisionSerializer`. Extended `AgroclimateZoneSerializer` and `StateSerializer`. |
| `apps/location/views.py` | Added `ContinentListView`, `CountryListView`, `AdminDivisionListView`, `GlobalGeocodeView`. Preserved all existing India views unchanged. |
| `apps/location/urls.py` | Added routes for `continents/`, `countries/`, `admin-divisions/`, `global-geocode/`. |
| `apps/location/admin.py` | Registered `Continent`, `Country`, `AdminDivision` in admin. Updated `AgroclimateZoneAdmin` and `StateAdmin`. |
| `apps/location/services.py` | No changes to `resolve_location()` or `validate_india_bounds()` — fully backward-compatible. |
| `apps/crops/models.py` | Added `continent`, `country`, `admin_division` FKs to `Crop`. Made `state` FK nullable. Updated `__str__` and Meta indexes. |
| `apps/crops/serializers.py` | Added `continent_name`, `country_name`, `admin_division_name` read-only fields. |
| `apps/crops/views.py` | Extended `CropListView` with `country` and `continent` query params. |
| `apps/crops/admin.py` | Updated `CropAdmin` to show new global fields. |
| `apps/crops/management/commands/load_crops.py` | Now creates `Continent` (Asia) and `Country` (India) records. Associates State and Crop records with India country. |
| `apps/recommendations/services.py` | Refactored `get_recommendations()` to support both India (backward-compat) and global pipelines. Added `continent` and `country` to response. |
| `apps/recommendations/serializers.py` | Added `continent` and `country` fields to `RecommendationResponseSerializer`. |
| `apps/recommendations/views.py` | Updated form and result views to pass continent/country context. |
| `core/settings.py` | Added `DATA_ROOT` and `CONTINENT_REGISTRY_PATH` settings. |
| `templates/recommendations/form.html` | Added continent/country selectors alongside existing state selector. Updated JS for tab switching. |

### Files Created

| File | Purpose |
|------|---------|
| `apps/location/geography_service.py` | Generic continent/country/division resolver from lat/lon. Bounding-box continent detection, anchor-based country matching, config-driven admin hierarchy. |
| `apps/location/continent_config.json` | Bounding box definitions for Asia, Africa, Europe, America. |
| `apps/location/country_config.json` | Country metadata: centroids, admin hierarchies, dataset paths for 10 countries across 4 continents. |
| `apps/location/tests.py` | 20 tests: continent detection (10), country detection (4), admin hierarchy (4), full resolution (3). |
| `apps/engine/tests_global.py` | 9 tests: global scoring (5), multi-continent ranking (1), India regression (3). |
| `apps/crops/management/commands/load_global_crops.py` | Configuration-driven dataset loader. Discovers Excel files from `data/<continent>/<country>/` folders. Supports `--continent`, `--country`, `--no-clear` flags. |
| `data/continent_registry.json` | Maps continent codes to filesystem paths. |
| `data/Asia/India/country.json` | India country config. |
| `data/Africa/Nigeria/country.json` | Nigeria country config (placeholder). |
| `data/Africa/Kenya/country.json` | Kenya country config (placeholder). |
| `data/Africa/South_Africa/country.json` | South Africa country config (placeholder). |
| `data/America/USA/country.json` | USA country config (placeholder). |
| `data/America/Brazil/country.json` | Brazil country config (placeholder). |
| `data/America/Canada/country.json` | Canada country config (placeholder). |
| `data/Europe/France/country.json` | France country config (placeholder). |
| `data/Europe/Germany/country.json` | Germany country config (placeholder). |
| `data/Europe/Italy/country.json` | Italy country config (placeholder). |
| `apps/location/migrations/0002_...py` | Migration: new Continent, Country, AdminDivision tables + country FK on State, AgroclimateZone. |
| `apps/crops/migrations/0002_...py` | Migration: new continent/country/admin_division FKs on Crop, state FK made nullable. |

### Refactoring Summary

- **Backward compatibility**: All existing India endpoints (POST /api/v1/recommend/, GET /api/v1/location/states/, POST /api/v1/location/geocode/) are unchanged. India API requests produce identical response formats (with the addition of `continent` and `country` fields in the response).
- **Scoring engine untouched**: `apps/engine/rule_engine.py` and `apps/engine/weather_service.py` are completely unchanged. The rule engine is already country-agnostic.
- **India data loader preserved**: `load_crops.py` still works exactly as before, with the addition of populating continent/country fields.
- **No existing migrations altered**: New migrations are additive only.

### Compatibility Notes

- **API responses** now include two new optional fields: `continent` and `country`. Existing clients that ignore unknown fields will work fine.
- **Frontend form** now shows continent/country/state selectors alongside GPS coordinates.
- **Existing tests** in `apps/engine/tests.py` have pre-existing failures related to pH elimination behavior (the engine was updated from hard elimination to soft scoring before this extension). These are NOT caused by the multi-continent changes.
- **Database**: Running `python manage.py migrate` adds new tables. Existing data is untouched.
- **Data loading**: Run `python manage.py load_crops` to reload India data with continent/country associations. Run `python manage.py load_global_crops` to load other countries.
