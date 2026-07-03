"""
Location models — stores Indian states, districts, and agroclimatic zones.
Populated by the `load_crops` management command.
"""
from django.db import models


class AgroclimateZone(models.Model):
    """One of the 14 ICAR agroclimatic zones used in this dataset."""
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class State(models.Model):
    """Indian state with a centroid for nearest-match geocoding."""
    name = models.CharField(max_length=100, unique=True)
    centroid_lat = models.FloatField()
    centroid_lon = models.FloatField()
    # Notable facts extracted from the ★ lines in the Excel (e.g. GI tags)
    notable_facts = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
