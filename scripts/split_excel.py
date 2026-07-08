"""Split master continent Excel files into per-country files."""
import json, shutil, re
from pathlib import Path
from openpyxl import load_workbook, Workbook

BASE = Path(r"C:\Users\madha\AppData\Local\Temp\opencode\agrozone")
DATA = BASE / "data"

MASTER_FILES = {
    "Africa":  r"C:\Users\madha\OneDrive\Desktop\crop-recommender\Africa_Country_Wise_Crops.xlsx",
    "Europe":  r"C:\Users\madha\OneDrive\Desktop\crop-recommender\Europe_Country_Wise_Crops.xlsx",
    "America": r"C:\Users\madha\Downloads\America_Country_Wise_Crops.xlsx",
}

SKIP_SHEETS = {"INDEX", "Soil_Methodology", "Sheet1", "Sheet2", "Sheet3", "Sheet4"}

for cont_name, filepath in MASTER_FILES.items():
    wb = load_workbook(filepath, data_only=True)
    sheets = [s for s in wb.sheetnames if s not in SKIP_SHEETS]
    print(f"\n{'='*60}")
    print(f"{cont_name}: {len(sheets)} country sheets")

    for sheet_name in sheets:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))

        # Find header row
        header_idx = None
        for i, row in enumerate(rows):
            if row and row[0] and str(row[0]).strip().lower() == "category":
                header_idx = i
                break
        if header_idx is None:
            print(f"  SKIP {sheet_name}: no header row found")
            continue

        # Determine country folder name
        country_name = sheet_name.replace(" ", "_")
        country_dir = DATA / cont_name / country_name
        crops_dir = country_dir / "crops"
        crops_dir.mkdir(parents=True, exist_ok=True)

        # Create per-country Excel
        out_path = crops_dir / f"{sheet_name}_Crops.xlsx"
        if out_path.exists():
            out_path.unlink()

        out_wb = Workbook()
        out_ws = out_wb.active
        out_ws.title = sheet_name[:31]  # sheet name max 31 chars

        for row in rows:
            out_ws.append(row)

        out_wb.save(out_path)
        data_count = sum(1 for r in rows[header_idx+1:] if r and r[0] and r[1])
        print(f"  OK {sheet_name}: {data_count} crops -> {out_path.relative_to(BASE)}")

    wb.close()

print("\nAll files split.")
