from django.contrib import admin
from .models import State, AgroclimateZone


@admin.register(AgroclimateZone)
class AgroclimateZoneAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]
    search_fields = ["name"]


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ["name", "centroid_lat", "centroid_lon"]
    search_fields = ["name"]
    readonly_fields = ["centroid_lat", "centroid_lon", "notable_facts"]
