"""
Management command: load_crops
Usage: python manage.py load_crops

Reads data/India_State_Wise_Crops_Final.xlsx and populates:
  - location_state
  - location_agroclimateezone
  - crops_crop

Safe to re-run — clears existing data first (--no-clear to skip).
"""
import re
from openpyxl import load_workbook
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from apps.location.models import State, AgroclimateZone
from apps.crops.models import Crop


# ── State centroids (approximate geographic centre, decimal degrees) ──────────
STATE_CENTROIDS = {
    "Andhra Pradesh":       (15.9129, 79.7400),
    "Arunachal Pradesh":    (28.2180, 94.7278),
    "Assam":                (26.2006, 92.9376),
    "Bihar":                (25.0961, 85.3131),
    "Chhattisgarh":         (21.2787, 81.8661),
    "Goa":                  (15.2993, 74.1240),
    "Gujarat":              (22.2587, 71.1924),
    "Haryana":              (29.0588, 76.0856),
    "Himachal Pradesh":     (31.1048, 77.1734),
    "Jharkhand":            (23.6102, 85.2799),
    "Jammu & Kashmir":      (33.7782, 76.5762),
    "Karnataka":            (15.3173, 75.7139),
    "Kerala":               (10.8505, 76.2711),
    "Madhya Pradesh":       (22.9734, 78.6569),
    "Maharashtra":          (19.7515, 75.7139),
    "Manipur":              (24.6637, 93.9063),
    "Meghalaya":            (25.4670, 91.3662),
    "Mizoram":              (23.1645, 92.9376),
    "Nagaland":             (26.1584, 94.5624),
    "Odisha":               (20.9517, 85.0985),
    "Punjab":               (31.1471, 75.3412),
    "Rajasthan":            (27.0238, 74.2179),
    "Sikkim":               (27.5330, 88.5122),
    "Tamil Nadu":           (11.1271, 78.6569),
    "Telangana":            (18.1124, 79.0193),
    "Tripura":              (23.9408, 91.9882),
    "Uttar Pradesh":        (26.8467, 80.9462),
    "Uttarakhand":          (30.0668, 79.0193),
    "West Bengal":          (22.9868, 87.8550),
}

SKIP_SHEETS = {"INDEX", "Soil_Methodology", "Sheet1", "Sheet2", "Sheet3", "Sheet4"}


def _parse_range(value: str) -> tuple[float, float]:
    """
    Parse a range string like '5.5-7.5' or '240-292' into (lo, hi) floats.
    Returns (0.0, 0.0) for unparseable values.
    """
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


class Command(BaseCommand):
    help = "Load India_State_Wise_Crops_Final.xlsx into the SQLite database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-clear",
            action="store_true",
            help="Skip clearing existing data (appends instead).",
        )

    def handle(self, *args, **options):
        path = settings.CROPS_EXCEL_PATH
        if not path.exists():
            raise CommandError(f"Excel file not found: {path}")

        if not options["no_clear"]:
            self.stdout.write("Clearing existing crop data…")
            Crop.objects.all().delete()
            AgroclimateZone.objects.all().delete()
            State.objects.all().delete()

        wb = load_workbook(path, read_only=True, data_only=True)
        state_sheets = [s for s in wb.sheetnames if s not in SKIP_SHEETS]

        # ── Pre-create zones (collected from all sheets first) ────────────
        self.stdout.write("Scanning zones…")
        zone_names = set()
        for sheet_name in state_sheets:
            ws = wb[sheet_name]
            for row in ws.iter_rows(values_only=True):
                if row and row[0] not in (None, "Category") and row[1] and row[3]:
                    cat = str(row[0]).strip()
                    if not cat.startswith("  ") and not cat.startswith("★") and not cat.startswith("🌾"):
                        zone_names.add(str(row[3]).strip())

        zone_map = {}
        for zname in zone_names:
            zone, _ = AgroclimateZone.objects.get_or_create(name=zname)
            zone_map[zname] = zone
        self.stdout.write(f"  {len(zone_map)} zones created.")

        # ── Load each state sheet ─────────────────────────────────────────
        total_crops = 0
        for sheet_name in state_sheets:
            ws = wb[sheet_name]
            rows = list(ws.iter_rows(values_only=True))

            # Extract ★ notable facts from the header block
            notable_facts = []
            for r in rows:
                if r and r[0] and str(r[0]).startswith("★"):
                    notable_facts.append(str(r[0]).lstrip("★").strip())

            # Get centroid
            centroid = STATE_CENTROIDS.get(sheet_name)
            if not centroid:
                self.stdout.write(self.style.WARNING(f"  No centroid for '{sheet_name}', skipping."))
                continue

            state, _ = State.objects.get_or_create(
                name=sheet_name,
                defaults={
                    "centroid_lat": centroid[0],
                    "centroid_lon": centroid[1],
                    "notable_facts": "\n".join(notable_facts),
                },
            )

            # Parse crop rows
            # Columns: Category(0) | Crop Name(1) | Notes(2) | Zone(3) |
            #          OC(4) | N(5) | P2O5(6) | K(7) | S(8) |
            #          Fe(9) | Mn(10) | Cu(11) | Zn(12) | B(13) |
            #          pH(14) | EC(15) | Ca(16) | Mg(17) | Temp(18)
            crop_objects = []
            sheet_order = 0
            for row in rows:
                if not row or not row[0] or not row[1]:
                    continue
                cat = str(row[0]).strip()
                # Skip section headers, title rows, notable rows
                if (cat.startswith("  ") or cat.startswith("★") or
                        cat.startswith("🌾") or cat == "Category"):
                    continue

                crop_name = str(row[1]).strip()
                notes     = str(row[2]).strip() if row[2] else ""
                zone_name = str(row[3]).strip() if row[3] else ""
                zone_obj  = zone_map.get(zone_name)

                # Check if this crop is a state specialty (mentioned in notable facts)
                is_notable = any(
                    crop_name.lower() in fact.lower() for fact in notable_facts
                )

                # Parse all 14 soil parameters
                oc_lo, oc_hi   = _parse_range(row[4])
                n_lo,  n_hi    = _parse_range(row[5])
                p_lo,  p_hi    = _parse_range(row[6])
                k_lo,  k_hi    = _parse_range(row[7])
                s_lo,  s_hi    = _parse_range(row[8])
                fe_lo, fe_hi   = _parse_range(row[9])
                mn_lo, mn_hi   = _parse_range(row[10])
                cu_lo, cu_hi   = _parse_range(row[11])
                zn_lo, zn_hi   = _parse_range(row[12])
                b_lo,  b_hi    = _parse_range(row[13])
                ph_lo, ph_hi   = _parse_range(row[14])
                ec_lo, ec_hi   = _parse_range(row[15])
                ca_lo, ca_hi   = _parse_range(row[16])
                mg_lo, mg_hi   = _parse_range(row[17])
                temp           = str(row[18]).strip() if len(row) > 18 and row[18] else ""

                crop_objects.append(Crop(
                    state=state, zone=zone_obj, category=cat,
                    crop_name=crop_name, notes=notes,
                    is_notable=is_notable, temp_range=temp,
                    sheet_order=sheet_order,
                    ph_lo=ph_lo, ph_hi=ph_hi,
                    oc_lo=oc_lo, oc_hi=oc_hi, ec_lo=ec_lo, ec_hi=ec_hi,
                    n_lo=n_lo, n_hi=n_hi, p_lo=p_lo, p_hi=p_hi,
                    k_lo=k_lo, k_hi=k_hi, s_lo=s_lo, s_hi=s_hi,
                    fe_lo=fe_lo, fe_hi=fe_hi, mn_lo=mn_lo, mn_hi=mn_hi,
                    cu_lo=cu_lo, cu_hi=cu_hi, zn_lo=zn_lo, zn_hi=zn_hi,
                    b_lo=b_lo, b_hi=b_hi, ca_lo=ca_lo, ca_hi=ca_hi,
                    mg_lo=mg_lo, mg_hi=mg_hi,
                ))
                sheet_order += 1

            Crop.objects.bulk_create(crop_objects)
            total_crops += len(crop_objects)
            self.stdout.write(f"  {sheet_name}: {len(crop_objects)} crops loaded.")

        self.stdout.write(self.style.SUCCESS(
            f"\n✅  Done. {total_crops} crops across {len(state_sheets)} states."
        ))
