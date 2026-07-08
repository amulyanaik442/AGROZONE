"""
Management command: load_global_crops
Usage: python manage.py load_global_crops [--continent AS] [--country India]

Configuration-driven dataset loader. Discovers datasets from the `data/`
folder structure and loads them into the database using the generic models.

Supports:
  - Loading all discovered countries:  python manage.py load_global_crops
  - Loading a specific continent:      python manage.py load_global_crops --continent AS
  - Loading a specific country:        python manage.py load_global_crops --country India
  - Appending (no clear):              python manage.py load_global_crops --no-clear

Backward-compatible: does NOT clear India State/AgroclimateZone/Crop data.
Uses `--no-clear` by default for safety.
"""
import json
import re
from pathlib import Path
from openpyxl import load_workbook
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from apps.location.models import Continent, Country, AdminDivision
from apps.crops.models import Crop


def _load_country_config():
    path = Path(settings.BASE_DIR) / "apps/location/country_config.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


COUNTRY_CONFIG_CACHE = _load_country_config()


def _get_country_code(name: str) -> str:
    """Look up ISO country code from config. Falls back to auto-generating."""
    for c in COUNTRY_CONFIG_CACHE.get("countries", []):
        if c["name"].lower() == name.lower():
            return c["code"]
    return ""


def _parse_range(value: str) -> tuple:
    if not value:
        return 0.0, 0.0
    value = str(value).strip()
    m = re.match(r"^([\d.]+)\s*[-–]\s*([\d.]+)", value)
    if m:
        return float(m.group(1)), float(m.group(2))
    try:
        v = float(value)
        return v, v
    except ValueError:
        return 0.0, 0.0


EXCEL_COLUMN_NAMES = {
    "category": 0, "crop_name": 1, "notes": 2, "zone": 3,
    "oc": 4, "n": 5, "p": 6, "k": 7, "s": 8,
    "fe": 9, "mn": 10, "cu": 11, "zn": 12, "b": 13,
    "ph": 14, "ec": 15, "ca": 16, "mg": 17, "temp": 18,
}

SKIP_ROWS = {"Category", ""}


class Command(BaseCommand):
    help = "Load crop datasets from data/<continent>/<country>/ folders."

    def add_arguments(self, parser):
        parser.add_argument(
            "--continent", type=str, default="",
            help="Continent code (AS, AF, EU, AM) to load. If empty, loads all.",
        )
        parser.add_argument(
            "--country", type=str, default="",
            help="Country name to load. If empty, loads all in --continent.",
        )
        parser.add_argument(
            "--no-clear",
            action="store_true",
            help="Skip clearing existing crop data for the loaded countries.",
        )

    def handle(self, *args, **options):
        cont_filter = options.get("continent", "").strip().upper()
        country_filter = options.get("country", "").strip()
        no_clear = options.get("no_clear", False)

        # Discover datasets
        registry_path = settings.DATA_ROOT / "continent_registry.json"
        if not registry_path.exists():
            raise CommandError(f"Continent registry not found: {registry_path}")

        with open(registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)

        loaded_total = 0
        for cont_code, cont_info in registry.get("continents", {}).items():
            if cont_filter and cont_code != cont_filter:
                continue

            cont_path = Path(settings.BASE_DIR) / cont_info["path"]
            if not cont_path.exists():
                self.stdout.write(self.style.WARNING(
                    f"  Path not found: {cont_path} — skipping."
                ))
                continue

            # Get or create Continent
            continent, _ = Continent.objects.get_or_create(
                code=cont_code,
                defaults={"name": cont_info["name"]},
            )

            # Scan country folders
            for country_dir in sorted(cont_path.iterdir()):
                if not country_dir.is_dir():
                    continue
                country_name = country_dir.name.replace("_", " ")

                if country_filter and country_name.lower() != country_filter.lower():
                    continue

                # Load country config if available
                country_config_path = country_dir / "country.json"
                admin_hierarchy = ["State"]
                if country_config_path.exists():
                    with open(country_config_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                        admin_hierarchy = cfg.get("admin_hierarchy", admin_hierarchy)

                # Find Excel files
                excel_files = []
                for pattern in ["*.xlsx", "*.xls"]:
                    excels = list(country_dir.rglob(pattern))
                    for xl in excels:
                        # Skip temp files
                        if "~$" in xl.name:
                            continue
                        excel_files.append(xl)

                if not excel_files:
                    self.stdout.write(self.style.WARNING(
                        f"  No Excel files found in {country_dir}."
                    ))
                    continue

                # Get or create Country
                country_code = _get_country_code(country_name) or country_dir.name[:2].upper()
                country, _ = Country.objects.get_or_create(
                    name=country_name,
                    defaults={
                        "code": country_code,
                        "continent": continent,
                        "centroid_lat": 0.0,
                        "centroid_lon": 0.0,
                    },
                )
                if country.code != country_code:
                    country.code = country_code
                    country.save(update_fields=["code"])

                if not no_clear:
                    # Only clear crops for this country (not India's State-based crops)
                    Crop.objects.filter(country=country).delete()

                # Load each Excel file
                for excel_path in excel_files:
                    self.stdout.write(f"  Loading: {excel_path.name} -> {country_name}")
                    loaded = self._load_excel(excel_path, continent, country,
                                              admin_hierarchy, no_clear)
                    loaded_total += loaded
                    self.stdout.write(f"    {loaded} crops loaded.")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. {loaded_total} total crops loaded globally."
        ))

    def _load_excel(self, path: Path, continent: Continent, country: Country,
                    admin_hierarchy: list, no_clear: bool) -> int:
        """Load a single Excel file into the crops table."""
        wb = load_workbook(path, read_only=True, data_only=True)
        count = 0

        for sheet_name in wb.sheetnames:
            if sheet_name.upper() in {"INDEX", "SOIL_METHODOLOGY", "SHEET1",
                                       "SHEET2", "SHEET3", "SHEET4"}:
                continue

            ws = wb[sheet_name]
            rows = list(ws.iter_rows(values_only=True))

            # Try to find the header row
            header_row_idx = None
            for i, row in enumerate(rows):
                if row and row[0] and str(row[0]).strip().lower() == "category":
                    header_row_idx = i
                    break

            if header_row_idx is None:
                # Assume first row is header
                header_row_idx = 0

            # Extract admin division name from sheet name or first column
            admin_div_name = sheet_name.strip()

            # Get or create AdminDivision
            admin_div, _ = AdminDivision.objects.get_or_create(
                name=admin_div_name,
                country=country,
                level_name=admin_hierarchy[0] if admin_hierarchy else "State",
            )

            crop_objects = []
            sheet_order = 0

            for row in rows[header_row_idx + 1:]:
                if not row or not row[0] or not row[1]:
                    continue
                cat = str(row[0]).strip()
                crop_name = str(row[1]).strip()

                if cat.lower() in SKIP_ROWS or not crop_name:
                    continue

                notes = str(row[2]).strip() if len(row) > 2 and row[2] else ""
                zone_name = str(row[3]).strip() if len(row) > 3 and row[3] else ""
                temp = str(row[18]).strip() if len(row) > 18 and row[18] else ""

                oc_lo, oc_hi = _parse_range(row[4]) if len(row) > 4 else (0.0, 0.0)
                n_lo, n_hi = _parse_range(row[5]) if len(row) > 5 else (0.0, 0.0)
                p_lo, p_hi = _parse_range(row[6]) if len(row) > 6 else (0.0, 0.0)
                k_lo, k_hi = _parse_range(row[7]) if len(row) > 7 else (0.0, 0.0)
                s_lo, s_hi = _parse_range(row[8]) if len(row) > 8 else (0.0, 0.0)
                fe_lo, fe_hi = _parse_range(row[9]) if len(row) > 9 else (0.0, 0.0)
                mn_lo, mn_hi = _parse_range(row[10]) if len(row) > 10 else (0.0, 0.0)
                cu_lo, cu_hi = _parse_range(row[11]) if len(row) > 11 else (0.0, 0.0)
                zn_lo, zn_hi = _parse_range(row[12]) if len(row) > 12 else (0.0, 0.0)
                b_lo, b_hi = _parse_range(row[13]) if len(row) > 13 else (0.0, 0.0)
                ph_lo, ph_hi = _parse_range(row[14]) if len(row) > 14 else (0.0, 0.0)
                ec_lo, ec_hi = _parse_range(row[15]) if len(row) > 15 else (0.0, 0.0)
                ca_lo, ca_hi = _parse_range(row[16]) if len(row) > 16 else (0.0, 0.0)
                mg_lo, mg_hi = _parse_range(row[17]) if len(row) > 17 else (0.0, 0.0)

                crop_objects.append(Crop(
                    continent=continent,
                    country=country,
                    admin_division=admin_div,
                    category=cat,
                    crop_name=crop_name,
                    notes=notes,
                    is_notable=False,
                    temp_range=temp,
                    sheet_order=sheet_order,
                    ph_lo=ph_lo, ph_hi=ph_hi,
                    oc_lo=oc_lo, oc_hi=oc_hi,
                    ec_lo=ec_lo, ec_hi=ec_hi,
                    n_lo=n_lo, n_hi=n_hi,
                    p_lo=p_lo, p_hi=p_hi,
                    k_lo=k_lo, k_hi=k_hi,
                    s_lo=s_lo, s_hi=s_hi,
                    fe_lo=fe_lo, fe_hi=fe_hi,
                    mn_lo=mn_lo, mn_hi=mn_hi,
                    cu_lo=cu_lo, cu_hi=cu_hi,
                    zn_lo=zn_lo, zn_hi=zn_hi,
                    b_lo=b_lo, b_hi=b_hi,
                    ca_lo=ca_lo, ca_hi=ca_hi,
                    mg_lo=mg_lo, mg_hi=mg_hi,
                ))
                sheet_order += 1

            Crop.objects.bulk_create(crop_objects)
            count += len(crop_objects)

        wb.close()
        return count
