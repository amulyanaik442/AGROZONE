from django.contrib import admin
from .models import Crop


@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    list_display = [
        "crop_name", "category", "state", "zone",
        "ph_lo", "ph_hi", "is_notable", "sheet_order",
    ]
    list_filter = ["state", "zone", "category", "is_notable"]
    search_fields = ["crop_name", "notes", "state__name"]
    readonly_fields = ["sheet_order"]
    ordering = ["state__name", "sheet_order"]

    fieldsets = (
        ("Identity", {
            "fields": ("state", "zone", "category", "crop_name", "notes",
                       "is_notable", "temp_range", "sheet_order"),
        }),
        ("Gate 2 — pH (Hard Filter)", {
            "fields": (("ph_lo", "ph_hi"),),
        }),
        ("Gate 3 — Soil Health (15 pts)", {
            "fields": (("oc_lo", "oc_hi"), ("ec_lo", "ec_hi")),
        }),
        ("Gate 4 — Macronutrients (55 pts)", {
            "fields": (
                ("n_lo", "n_hi"), ("p_lo", "p_hi"),
                ("k_lo", "k_hi"), ("s_lo", "s_hi"),
            ),
        }),
        ("Gate 5 — Micronutrients (30 pts)", {
            "fields": (
                ("fe_lo", "fe_hi"), ("mn_lo", "mn_hi"),
                ("cu_lo", "cu_hi"), ("zn_lo", "zn_hi"),
                ("b_lo",  "b_hi"),  ("ca_lo", "ca_hi"),
                ("mg_lo", "mg_hi"),
            ),
        }),
    )
