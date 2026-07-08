"""
Crop Models
-----------
Each Crop row mirrors one Excel row:
  Category | Crop Name | Notes | Zone | OC | N | P2O5 | K | S | Fe | Mn | Cu | Zn | B | pH | EC | Ca | Mg | Temp

Supports multi-continent: India crops reference State; global crops
reference Country + optional AdminDivision. Both paths converge to the
same rule engine.

Backward-compatible: all new fields are nullable. India data untouched.
"""
from django.db import models
from apps.location.models import State, AgroclimateZone, Continent, Country, AdminDivision


class Crop(models.Model):
    """
    A single crop entry for a specific location x agroclimatic zone.

    For India: state + zone are used (backward-compatible).
    For global: continent + country + admin_division are used.
    """
    # ── Global identity (new) ─────────────────────────────────────────────
    continent = models.ForeignKey(
        Continent, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="crops"
    )
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, null=True, blank=True,
        related_name="crops"
    )
    admin_division = models.ForeignKey(
        AdminDivision, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="crops",
        help_text="Administrative division (state/province/region) for non-India crops."
    )

    # ── India-specific identity (backward-compatible) ────────────────────
    state = models.ForeignKey(
        State, on_delete=models.CASCADE, null=True, blank=True,
        related_name="crops"
    )
    zone = models.ForeignKey(
        AgroclimateZone, on_delete=models.SET_NULL, null=True, blank=True
    )

    # ── Core identity ─────────────────────────────────────────────────────
    category = models.CharField(max_length=60)          # e.g. "Cereals & Millets"
    crop_name = models.CharField(max_length=120)
    notes = models.TextField(blank=True, default="")    # Notes/Significance column
    is_notable = models.BooleanField(default=False)     # True if mentioned in notable facts
    temp_range = models.CharField(max_length=30, blank=True, default="")  # e.g. "20-35°C"
    sheet_order = models.PositiveIntegerField(default=0)  # row position in Excel — used as tie-breaker

    # ── Gate 2: pH (hard filter) ──────────────────────────────────────────
    ph_lo = models.FloatField()
    ph_hi = models.FloatField()

    # ── Gate 3: Soil Health — soft scoring ───────────────────────────────
    oc_lo = models.FloatField()   # Organic Carbon (%)
    oc_hi = models.FloatField()
    ec_lo = models.FloatField()   # Electrical Conductivity (dS/m)
    ec_hi = models.FloatField()

    # ── Gate 4: Macronutrients — highest scored weight ───────────────────
    n_lo = models.FloatField()    # Nitrogen (kg/ha)
    n_hi = models.FloatField()
    p_lo = models.FloatField()    # P2O5 (kg/ha)
    p_hi = models.FloatField()
    k_lo = models.FloatField()    # Potassium (kg/ha)
    k_hi = models.FloatField()
    s_lo = models.FloatField()    # Sulphur (ppm)
    s_hi = models.FloatField()

    # ── Gate 5: Micronutrients — lower weight, tie-breaker ───────────────
    fe_lo = models.FloatField()   # Iron (ppm)
    fe_hi = models.FloatField()
    mn_lo = models.FloatField()   # Manganese (ppm)
    mn_hi = models.FloatField()
    cu_lo = models.FloatField()   # Copper (ppm)
    cu_hi = models.FloatField()
    zn_lo = models.FloatField()   # Zinc (ppm)
    zn_hi = models.FloatField()
    b_lo = models.FloatField()    # Boron (ppm)
    b_hi = models.FloatField()
    ca_lo = models.FloatField()   # Calcium (meq/100g)
    ca_hi = models.FloatField()
    mg_lo = models.FloatField()   # Magnesium (meq/100g)
    mg_hi = models.FloatField()

    class Meta:
        ordering = ["state__name", "sheet_order"]
        indexes = [
            models.Index(fields=["state"]),
            models.Index(fields=["zone"]),
            models.Index(fields=["category"]),
            models.Index(fields=["country"]),
            models.Index(fields=["continent"]),
            models.Index(fields=["admin_division"]),
        ]

    def __str__(self):
        if self.state:
            return f"{self.crop_name} ({self.state.name})"
        if self.admin_division:
            return f"{self.crop_name} ({self.admin_division.name}, {self.country.name})"
        if self.country:
            return f"{self.crop_name} ({self.country.name})"
        return self.crop_name
