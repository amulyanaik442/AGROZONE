"""
Crop Utility Functions
----------------------
Helper functions for crop name normalization, matching, and
safe value extraction used across the feature engine modules.
"""
import re


def normalize_crop_name(name: str) -> str:
    """
    Normalize a crop name for matching against the dataset.

    Steps:
    1. Strip leading/trailing whitespace
    2. Convert to lowercase
    3. Collapse multiple spaces
    4. Remove parenthetical notes like (GI), (#1 producer), etc.
    5. Remove common suffixes like " — GI" after a name
    """
    if not name:
        return ""
    n = name.strip().lower()
    n = re.sub(r"\s+", " ", n)
    # Remove content inside parentheses (including the parens themselves)
    n = re.sub(r"\([^)]*\)", "", n)
    # Remove em dashes and trailing notes
    n = re.sub(r"\s*—.*$", "", n)
    # Remove trailing commas, periods
    n = n.strip().rstrip(".,;: ")
    return n


def extract_base_name(crop_name: str) -> str:
    """
    Extract the base/simple name from a possibly compound crop name.
    E.g., 'Rice (Paddy)' -> 'Rice', 'Bajra (Pearl Millet)' -> 'Bajra'
    """
    name = crop_name.strip()
    # Split on parenthesis and take the first part
    parts = re.split(r"[\s]*\([^)]*\)[\s]*", name)
    base = parts[0].strip() if parts else name
    # Also split on em dash
    base = re.split(r"\s*—\s*", base)[0].strip()
    # Also split on comma
    base = re.split(r"\s*,\s*", base)[0].strip()
    return base


def safe_get(value, default="Not available"):
    """Safely return a value or a default fallback."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return default
    return str(value).strip()


def format_list(items: list) -> str:
    """Join list items into a readable string, handling missing gracefully."""
    if not items:
        return "Not available"
    valid = [str(i).strip() for i in items if i and str(i).strip()]
    return ", ".join(valid) if valid else "Not available"
