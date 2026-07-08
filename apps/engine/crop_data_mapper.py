"""
Crop Data Mapper
----------------
Reads the World_Country_Wise_Crop_Database_UPDATED.xlsx dataset and provides
efficient lookup of additional crop information by country and crop name.

Dataset format:
  - One sheet per country (e.g. "India", "United States")
  - Headers at row 6; data starts at row 8
  - Additional info columns: 21 (Crop Duration), 22 (Sowing Season),
    23 (Water Requirement), 24 (Common Pests), 25 (Fertilizers), 26 (Harvest Time)

Supports fuzzy matching via normalized names, case-insensitive
comparisons, and graceful fallback when a crop is not found.
"""
import os
from typing import Optional

import openpyxl

from django.conf import settings

from .crop_utils import normalize_crop_name, extract_base_name, safe_get


# Column indices (1-based as they appear in the Excel)
COL_CROP_NAME = 2
COL_CROP_DURATION = 21
COL_SOWING_SEASON = 22
COL_WATER_REQ = 23
COL_COMMON_PESTS = 24
COL_RECOMMENDED_FERTILIZERS = 25
COL_HARVEST_TIME = 26

HEADER_ROW = 6
DATA_START_ROW = 8


# Indian states -> country mapping
_STATE_TO_COUNTRY = {
    "andhra pradesh": "India",
    "arunachal pradesh": "India",
    "assam": "India",
    "bihar": "India",
    "chhattisgarh": "India",
    "goa": "India",
    "gujarat": "India",
    "haryana": "India",
    "himachal pradesh": "India",
    "jammu & kashmir": "India",
    "jharkhand": "India",
    "karnataka": "India",
    "kerala": "India",
    "madhya pradesh": "India",
    "maharashtra": "India",
    "manipur": "India",
    "meghalaya": "India",
    "mizoram": "India",
    "nagaland": "India",
    "odisha": "India",
    "punjab": "India",
    "rajasthan": "India",
    "sikkim": "India",
    "tamil nadu": "India",
    "telangana": "India",
    "tripura": "India",
    "uttar pradesh": "India",
    "uttarakhand": "India",
    "west bengal": "India",
}


def _resolve_country(location_name: str) -> str:
    """Convert a state/country name to the sheet name in the Excel."""
    key = location_name.strip().lower() if location_name else ""
    if key in _STATE_TO_COUNTRY:
        return _STATE_TO_COUNTRY[key]
    return location_name


class CropDataMapper:
    """
    Loads and indexes additional crop information from the World database Excel.

    Indexes by (country, normalized_crop_name) for efficient lookup.
    """

    def __init__(self, excel_path: Optional[str] = None):
        self.excel_path = excel_path or self._default_path()
        self._index: dict = {}
        self._fallback: dict = {}
        self._loaded = False

    def _default_path(self) -> str:
        return os.path.join(
            str(settings.DATA_ROOT),
            "World_Country_Wise_Crop_Database_UPDATED.xlsx"
        )

    def load(self) -> None:
        """Load and index the Excel dataset."""
        if self._loaded:
            return

        if not os.path.exists(self.excel_path):
            self._loaded = True
            return

        wb = openpyxl.load_workbook(self.excel_path, read_only=True)

        for sheet_name in wb.sheetnames:
            if sheet_name in ("INDEX", "Soil_Methodology"):
                continue

            ws = wb[sheet_name]
            country_key = sheet_name.strip().lower()

            for row in ws.iter_rows(min_row=DATA_START_ROW, values_only=True):
                if not row or not row[0]:
                    continue

                crop_name_val = row[COL_CROP_NAME - 1] if len(row) >= COL_CROP_NAME else None
                if not crop_name_val:
                    continue

                crop_name = str(crop_name_val).strip()
                if not crop_name:
                    continue

                # Skip category header rows (all-caps or indented)
                cat_val = str(row[0]).strip() if row[0] else ""
                if cat_val and (cat_val.isupper() or cat_val.startswith("  ")):
                    continue

                entry = {
                    "country": sheet_name,
                    "crop_name": crop_name,
                    "crop_duration": safe_get(row[COL_CROP_DURATION - 1] if len(row) >= COL_CROP_DURATION else None),
                    "best_sowing_season": safe_get(row[COL_SOWING_SEASON - 1] if len(row) >= COL_SOWING_SEASON else None),
                    "water_requirement": safe_get(row[COL_WATER_REQ - 1] if len(row) >= COL_WATER_REQ else None),
                    "common_pests": safe_get(row[COL_COMMON_PESTS - 1] if len(row) >= COL_COMMON_PESTS else None),
                    "recommended_fertilizers": safe_get(row[COL_RECOMMENDED_FERTILIZERS - 1] if len(row) >= COL_RECOMMENDED_FERTILIZERS else None),
                    "harvest_time": safe_get(row[COL_HARVEST_TIME - 1] if len(row) >= COL_HARVEST_TIME else None),
                }

                crop_norm = normalize_crop_name(crop_name)
                crop_lower = crop_name.lower()

                # Index: (country, normalized_crop_name) -> entry
                self._index[(country_key, crop_norm)] = entry
                self._index[(country_key, crop_lower)] = entry

                # Fallback: crop name only (first occurrence wins)
                if crop_norm not in self._fallback:
                    self._fallback[crop_norm] = entry
                if crop_lower not in self._fallback:
                    self._fallback[crop_lower] = entry

        wb.close()
        self._loaded = True

    def lookup(self, crop_name: str, location_name: Optional[str] = None) -> Optional[dict]:
        """
        Look up additional info for a given crop name, scoped to a location.

        Matching strategy:
          1. Resolve location -> country sheet name
          2. Exact match on (country, normalized crop name)
          3. Try with extracted base name
          4. Fallback to crop name only (cross-country)
          5. Partial substring match
          6. Return None if nothing found (graceful degradation)

        Args:
            crop_name: The crop name to look up
            location_name: State or country name for scope

        Returns:
            Dict with 6 feature keys, or None if not found.
        """
        self.load()

        if not crop_name:
            return None

        country = _resolve_country(location_name) if location_name else None
        country_key = country.strip().lower() if country else None

        crop_norm = normalize_crop_name(crop_name)
        crop_lower = crop_name.strip().lower()
        base_name = extract_base_name(crop_name)
        base_norm = normalize_crop_name(base_name)

        # Strategy 1: Exact match with country scoping
        if country_key:
            for key in [(country_key, crop_norm), (country_key, crop_lower)]:
                if key in self._index:
                    return self._index[key]

            if base_norm:
                key = (country_key, base_norm)
                if key in self._index:
                    return self._index[key]

        # Strategy 2: Fallback by normalized name (cross-country)
        for key in [crop_norm, crop_lower]:
            if key in self._fallback:
                return self._fallback[key]

        # Strategy 3: Fallback by base name
        if base_norm and base_norm not in (crop_norm, crop_lower):
            if base_norm in self._fallback:
                return self._fallback[base_norm]

        # Strategy 4: Partial substring match
        for fb_key, fb_entry in self._fallback.items():
            if fb_key in crop_norm or crop_norm in fb_key:
                return fb_entry
            if base_norm and (fb_key in base_norm or base_norm in fb_key):
                return fb_entry

        return None

    def lookup_many(self, crop_names: list, location_name: Optional[str] = None) -> dict:
        """Look up additional info for multiple crop names."""
        return {name: self.lookup(name, location_name) for name in crop_names}


# Singleton
_mapper_instance: Optional[CropDataMapper] = None


def get_mapper() -> CropDataMapper:
    global _mapper_instance
    if _mapper_instance is None:
        _mapper_instance = CropDataMapper()
    return _mapper_instance
