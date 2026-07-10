"""
Crop Utility Functions
----------------------
Helper functions for crop name normalization, matching, and
safe value extraction used across the feature engine modules.
"""
import re


# Mapping from common Indian/local crop names to their English equivalents
# used in the World_Country_Wise_Crop_Database dataset.
INDIAN_TO_ENGLISH_CROP_NAMES = {
    "ragi": "finger millet",
    "jowar": "sorghum",
    "bajra": "pearl millet",
    "red gram": "pigeon pea",
    "tur": "pigeon pea",
    "arhar": "pigeon pea",
    "maize": "maize",
    "groundnut": "groundnut",
    "castor": "castor",
    "cotton": "cotton",
    "sugarcane": "sugarcane",
    "tobacco": "tobacco",
    "jute": "jute",
    "tea": "tea",
    "coffee": "coffee",
    "coconut": "coconut",
    "cashew": "cashew",
    "arecanut": "areca nut",
    "areca": "areca nut",
    "rubber": "rubber",
    "turmeric": "turmeric",
    "ginger": "ginger",
    "garlic": "garlic",
    "coriander": "coriander",
    "cumin": "cumin",
    "fenugreek": "fenugreek",
    "mustard": "mustard",
    "onion": "onion",
    "potato": "potato",
    "tomato": "tomato",
    "chilli": "chili pepper",
    "chili": "chili pepper",
    "chili pepper": "chili pepper",
    "brinjal": "eggplant",
    "ladies finger": "okra",
    "bhindi": "okra",
    "pumpkin": "pumpkin",
    "bottle gourd": "bottle gourd",
    "bitter gourd": "bitter gourd",
    "carrot": "carrot",
    "radish": "radish",
    "cabbage": "cabbage",
    "cauliflower": "cauliflower",
    "mango": "mango",
    "banana": "banana",
    "guava": "guava",
    "papaya": "papaya",
    "pomegranate": "pomegranate",
    "watermelon": "watermelon",
    "lemon": "citrus (orange)",
    "lime": "citrus (orange)",
    "orange": "citrus (orange)",
    "sweet lime": "citrus (orange)",
    "mosambi": "citrus (orange)",
    "sapota": "sapota",
    "chikoo": "sapota",
    "jackfruit": "jackfruit",
    "litchi": "litchi",
    "tamarind": "tamarind",
    "marigold": "marigold",
    "rose": "rose",
    "jasmine": "jasmine",
    "chrysanthemum": "chrysanthemum",
    "tuberose": "tuberose",
    "cassava": "cassava",
    "sweet potato": "cassava",
    "soybean": "soybean",
    "soya bean": "soybean",
    "sunflower": "sunflower",
    "sesame": "sesame",
    "til": "sesame",
    "linseed": "linseed",
    "safflower": "safflower",
    "niger": "niger seed",
    "field pea": "field pea",
    "pea": "field pea",
    "mat bean": "horse gram",
    "kulthi": "horse gram",
    "cowpea": "cowpea",
    "black gram": "black gram",
    "green gram": "green gram",
    "chickpea": "chickpea",
    "gram": "chickpea",
    "bengal gram": "chickpea",
    "chana": "chickpea",
    "lentil": "lentil",
    "masoor": "lentil",
    "pigeon pea": "pigeon pea",
    "barley": "barley",
    "wheat": "wheat",
    "rice": "rice",
    "paddy": "rice",
    "foxtail millet": "foxtail millet",
    "kodo millet": "kodo millet",
    "little millet": "little millet",
    "barnyard millet": "barnyard millet",
    "proso millet": "proso millet",
    "sisal": "sisal",
    "jute": "jute",
    "cocoa": "cocoa",
    "custard apple": "custard apple",
    "fig": "fig",
    "avocado": "avocado",
}


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
