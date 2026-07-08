from django.contrib import admin
from .models import Continent, Country, AdminDivision, State, AgroclimateZone


@admin.register(Continent)
class ContinentAdmin(admin.ModelAdmin):
    list_display = ["name", "code"]
    search_fields = ["name", "code"]


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "continent"]
    list_filter = ["continent"]
    search_fields = ["name", "code"]


@admin.register(AdminDivision)
class AdminDivisionAdmin(admin.ModelAdmin):
    list_display = ["name", "level_name", "country", "parent"]
    list_filter = ["country", "level_name"]
    search_fields = ["name"]
    readonly_fields = ["centroid_lat", "centroid_lon", "notable_facts"]


@admin.register(AgroclimateZone)
class AgroclimateZoneAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "country"]
    list_filter = ["country"]
    search_fields = ["name"]


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ["name", "country", "centroid_lat", "centroid_lon"]
    list_filter = ["country"]
    search_fields = ["name"]
    readonly_fields = ["centroid_lat", "centroid_lon", "notable_facts"]
