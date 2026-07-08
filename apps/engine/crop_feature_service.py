"""
Crop Feature Service
--------------------
Service layer that integrates the crop feature engine with the
recommendation pipeline. Provides a clean interface for the views
to retrieve additional crop info for recommended crops.
"""
from typing import Optional

from .crop_data_mapper import get_mapper


def enrich_recommendations(top_crops: list, location_name: Optional[str] = None) -> list:
    """
    Enrich a list of recommended crops with additional feature information.

    For each crop in the list, adds a 'additional_info' key containing
    the mapped data from the Excel dataset (or None if not found).

    Args:
        top_crops: List of crop result dicts (from recommendation pipeline)
        location_name: Country or state name for scoped lookup

    Returns:
        The same list with each crop dict augmented with 'additional_info'
    """
    mapper = get_mapper()

    for crop in top_crops:
        crop_name = crop.get("crop_name", "")
        crop["additional_info"] = mapper.lookup(crop_name, location_name)

    return top_crops
