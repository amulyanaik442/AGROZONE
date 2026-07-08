# Test Report — AgroZone Multi-Continent Extension

## Summary

**Date**: 2026-07-08
**Branch**: main
**Tests Run**: 29 new tests + 15 existing engine tests

---

## New Tests Created

### Location Tests (`apps.location.tests`) — 20 tests

| Test | Status | Notes |
|------|--------|-------|
| `ContinentDetectionTests.test_india_detects_asia` | PASS | Bangalore → Asia |
| `ContinentDetectionTests.test_japan_detects_asia` | PASS | Tokyo → Asia |
| `ContinentDetectionTests.test_nigeria_detects_africa` | PASS | Abuja → Africa |
| `ContinentDetectionTests.test_kenya_detects_africa` | PASS | Nairobi → Africa |
| `ContinentDetectionTests.test_south_africa_detects_africa` | PASS | Cape Town → Africa |
| `ContinentDetectionTests.test_usa_detects_america` | PASS | NYC → America |
| `ContinentDetectionTests.test_brazil_detects_america` | PASS | São Paulo → America |
| `ContinentDetectionTests.test_france_detects_europe` | PASS | Paris → Europe |
| `ContinentDetectionTests.test_germany_detects_europe` | PASS | Berlin → Europe |
| `ContinentDetectionTests.test_atlantic_ocean_returns_none` | PASS | (0, -30) → None |
| `CountryDetectionTests.test_bangalore_resolves_to_india` | PASS | Bengaluru → IN |
| `CountryDetectionTests.test_lagos_resolves_to_nigeria` | PASS | Lagos → NG |
| `CountryDetectionTests.test_new_york_resolves_to_usa` | PASS | NYC → US |
| `CountryDetectionTests.test_paris_resolves_to_france` | PASS | Paris → FR |
| `AdminHierarchyTests.test_india_hierarchy` | PASS | ["State","District","Taluk"] |
| `AdminHierarchyTests.test_usa_hierarchy` | PASS | ["State","County"] |
| `AdminHierarchyTests.test_nigeria_hierarchy` | PASS | ["State","Local Government Area"] |
| `AdminHierarchyTests.test_unknown_country` | PASS | [] |
| `GlobalLocationResolutionTests.test_full_resolve_india` | PASS | lat/lon → country+continent |
| `GlobalLocationResolutionTests.test_full_resolve_usa` | PASS | lat/lon → country+continent |
| `GlobalLocationResolutionTests.test_unresolvable_location` | PASS | Antarctica → no continent |

### Global Engine Tests (`apps.engine.tests_global`) — 9 tests

| Test | Status | Notes |
|------|--------|-------|
| `GlobalCropScoringTests.test_nigerian_crop_scores_correctly` | PASS | Same engine, different country label |
| `GlobalCropScoringTests.test_us_crop_scores_correctly` | PASS | US crop scores correctly |
| `GlobalCropScoringTests.test_european_crop_with_all_params_missing` | PASS | 76.25 with only pH |
| `GlobalCropScoringTests.test_multi_continent_ranking` | PASS | 3 countries, 3 categories → 3 results |
| `GlobalCropScoringTests.test_india_regression_perfect_soil_scores_92_5` | PASS | 92.5 (weather neutral) |
| `GlobalCropScoringTests.test_india_regression_missing_params_76_25` | PASS | 76.25 (missing params) |
| `GlobalCropScoringTests.test_india_regression_ph_elimination` | PASS | Soft scoring (not eliminated) |
| `GlobalCropScoringTests.test_india_regression_deficiency_detection` | PASS | Low N flagged |

**All 29 new tests: PASS**

---

## Pre-Existing Tests

### Engine Tests (`apps.engine.tests`) — 15 tests

| Test | Status | Notes |
|------|--------|-------|
| `PHGateTests.test_ph_in_range_passes` | PASS | |
| `PHGateTests.test_ph_above_range_eliminated` | FAIL | Pre-existing: pH is now soft scoring |
| `PHGateTests.test_ph_below_range_eliminated` | FAIL | Pre-existing: pH is now soft scoring |
| `PHGateTests.test_ph_at_exact_boundary_passes` | PASS | |
| `ScoringTests.test_perfect_soil_scores_100` | FAIL | Pre-existing: 92.5 due to weather neutral |
| `ScoringTests.test_missing_all_optional_scores_50pct` | FAIL | Pre-existing: 76.25 (0.75 for missing) |
| `ScoringTests.test_deficiency_flagged_when_below_range` | PASS | |
| `ScoringTests.test_deficiency_flagged_when_above_range` | PASS | |
| `ScoringTests.test_in_range_param_no_deficiency` | PASS | |
| `RankingTests.test_top_n_returned` | FAIL | Pre-existing: category diversity |
| `RankingTests.test_ph_eliminated_crops_not_in_results` | PASS | |
| `RankingTests.test_notable_crop_wins_tiebreak` | PASS | |
| `RankingTests.test_sheet_order_tiebreak` | PASS | |
| `RankingTests.test_returns_empty_when_all_eliminated` | FAIL | Pre-existing: pH soft scoring |

**6 pre-existing failures** — all caused by the engine being updated (pH elimination → soft scoring, missing param 0.5 → 0.75, category diversity) BEFORE this multi-continent extension. NOT caused by our changes.

---

## Django System Checks

```
System check identified no issues (0 silenced).
```

---

## Regression Status

| Area | Status |
|------|--------|
| India API endpoints (unchanged) | 100% backward compatible |
| India request flow (lat/lon) | Identical path as before |
| India request flow (state_name) | Identical path as before |
| Response format | Same + 2 new optional fields |
| Scoring engine | Completely unchanged |
| Weather service | Unchanged |
| Existing data | Preserved |
| Existing migrations | Preserved (new migrations are additive) |

---

## Known Issues

1. **Pre-existing test failures** (6 tests in `apps.engine.tests`): These tests were written for an older version of the engine (pH hard elimination, 0.5 for missing params). The engine was updated before this extension, and the tests were not updated. They are unrelated to the multi-continent changes.

2. **No real crop data for non-India countries**: The extension creates the infrastructure (models, services, loaders) for global support, but actual crop datasets for Africa, Europe, and America need to be sourced and added to the `data/` folders.

3. **Admin division resolution accuracy**: The anchor-based matching works at country level but admin division resolution within a country is approximate (based on centroid distance). For production use, consider adding district/county-level anchors or PostGIS polygon matching.
