"""
Location models — stores continents, countries, admin divisions, states,
and agroclimatic zones. Populated by management commands.

Backward-compatible: India State + AgroclimateZone models are preserved.
New global models (Continent, Country, AdminDivision) extend the system
to support Africa, Europe, America without modifying existing code.
"""
from django.db import models


class Continent(models.Model):
    """A continent (Asia, Africa, Europe, America)."""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=2, unique=True, help_text="ISO 2-letter code (AS, AF, EU, AM)")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Country(models.Model):
    """A country with centroid for nearest-match geocoding."""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=2, unique=True, help_text="ISO 3166-1 alpha-2 code")
    continent = models.ForeignKey(
        Continent, on_delete=models.CASCADE, related_name="countries"
    )
    centroid_lat = models.FloatField()
    centroid_lon = models.FloatField()

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "countries"

    def __str__(self):
        return f"{self.name} ({self.continent.code})"


class AdminDivision(models.Model):
    """
    Administrative division at any level (state, province, region, district).
    Uses a self-referencing parent to model arbitrary hierarchies:
      Country → State → District → Taluk  (India)
      Country → State → County             (USA)
      Country → Province → District        (African countries)
      Country → Region → Province          (European countries)
    """
    name = models.CharField(max_length=200)
    level_name = models.CharField(
        max_length=50,
        help_text="e.g. State, District, Province, Region, County, Municipality"
    )
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="admin_divisions"
    )
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True,
        related_name="children"
    )
    centroid_lat = models.FloatField(null=True, blank=True)
    centroid_lon = models.FloatField(null=True, blank=True)
    notable_facts = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["country__name", "level_name", "name"]
        indexes = [
            models.Index(fields=["country", "level_name"]),
            models.Index(fields=["parent"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.level_name}, {self.country.name})"


class AgroclimateZone(models.Model):
    """One of the 14 ICAR agroclimatic zones used in the India dataset."""
    name = models.CharField(max_length=100, unique=True)
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, null=True, blank=True,
        related_name="agroclimate_zones",
        help_text="Country this zone belongs to (null = India for backward compat)."
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class State(models.Model):
    """Indian state with a centroid for nearest-match geocoding.
    Preserved for full backward compatibility."""
    name = models.CharField(max_length=100, unique=True)
    centroid_lat = models.FloatField()
    centroid_lon = models.FloatField()
    notable_facts = models.TextField(blank=True, default="")
    country = models.ForeignKey(
        Country, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="states",
        help_text="Country this state belongs to. Null for backward compat."
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
