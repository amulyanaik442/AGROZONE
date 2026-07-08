"""
Tests for the global geography service (continent/country detection).
Run with: python manage.py test apps.location
"""
from django.test import TestCase
from apps.location.models import Continent, Country, AdminDivision
from apps.location.geography_service import (
    resolve_continent, resolve_country, resolve_location_global,
    get_admin_hierarchy,
)


class ContinentDetectionTests(TestCase):
    """Test continent detection from lat/lon coordinates."""

    @classmethod
    def setUpTestData(cls):
        for name, code in [("Asia", "AS"), ("Africa", "AF"),
                            ("Europe", "EU"), ("America", "AM")]:
            Continent.objects.create(name=name, code=code)

    def test_india_detects_asia(self):
        result = resolve_continent(20.5937, 78.9629)
        self.assertIsNotNone(result)
        self.assertEqual(result.code, "AS")

    def test_japan_detects_asia(self):
        result = resolve_continent(35.6762, 139.6503)
        self.assertIsNotNone(result)
        self.assertEqual(result.code, "AS")

    def test_nigeria_detects_africa(self):
        result = resolve_continent(9.0820, 8.6753)
        self.assertIsNotNone(result)
        self.assertEqual(result.code, "AF")

    def test_kenya_detects_africa(self):
        result = resolve_continent(-1.2921, 36.8219)
        self.assertIsNotNone(result)
        self.assertEqual(result.code, "AF")

    def test_south_africa_detects_africa(self):
        result = resolve_continent(-33.9249, 18.4241)
        self.assertIsNotNone(result)
        self.assertEqual(result.code, "AF")

    def test_usa_detects_america(self):
        result = resolve_continent(40.7128, -74.0060)
        self.assertIsNotNone(result)
        self.assertEqual(result.code, "AM")

    def test_brazil_detects_america(self):
        result = resolve_continent(-23.5505, -46.6333)
        self.assertIsNotNone(result)
        self.assertEqual(result.code, "AM")

    def test_france_detects_europe(self):
        result = resolve_continent(48.8566, 2.3522)
        self.assertIsNotNone(result)
        self.assertEqual(result.code, "EU")

    def test_germany_detects_europe(self):
        result = resolve_continent(52.5200, 13.4050)
        self.assertIsNotNone(result)
        self.assertEqual(result.code, "EU")

    def test_atlantic_ocean_returns_none(self):
        """Coordinates in the middle of the Atlantic should not match any continent."""
        result = resolve_continent(0.0, -30.0)
        self.assertIsNone(result)


class CountryDetectionTests(TestCase):
    """Test nearest-country matching from lat/lon."""

    @classmethod
    def setUpTestData(cls):
        asia = Continent.objects.create(name="Asia", code="AS")
        africa = Continent.objects.create(name="Africa", code="AF")
        america = Continent.objects.create(name="America", code="AM")
        europe = Continent.objects.create(name="Europe", code="EU")

        Country.objects.create(name="India", code="IN", continent=asia,
                                centroid_lat=20.5937, centroid_lon=78.9629)
        Country.objects.create(name="Nigeria", code="NG", continent=africa,
                                centroid_lat=9.0820, centroid_lon=8.6753)
        Country.objects.create(name="United States", code="US", continent=america,
                                centroid_lat=37.0902, centroid_lon=-95.7129)
        Country.objects.create(name="France", code="FR", continent=europe,
                                centroid_lat=46.6034, centroid_lon=1.8883)

    def test_bangalore_resolves_to_india(self):
        country = resolve_country(12.9716, 77.5946)
        self.assertIsNotNone(country)
        self.assertEqual(country.code, "IN")

    def test_lagos_resolves_to_nigeria(self):
        country = resolve_country(6.5244, 3.3792)
        self.assertIsNotNone(country)
        self.assertEqual(country.code, "NG")

    def test_new_york_resolves_to_usa(self):
        country = resolve_country(40.7128, -74.0060)
        self.assertIsNotNone(country)
        self.assertEqual(country.code, "US")

    def test_paris_resolves_to_france(self):
        country = resolve_country(48.8566, 2.3522)
        self.assertIsNotNone(country)
        self.assertEqual(country.code, "FR")


class AdminHierarchyTests(TestCase):
    """Test admin hierarchy configuration."""

    def test_india_hierarchy(self):
        hierarchy = get_admin_hierarchy("IN")
        self.assertEqual(hierarchy, ["State", "District", "Taluk"])

    def test_usa_hierarchy(self):
        hierarchy = get_admin_hierarchy("US")
        self.assertEqual(hierarchy, ["State", "County"])

    def test_nigeria_hierarchy(self):
        hierarchy = get_admin_hierarchy("NG")
        self.assertEqual(hierarchy, ["State", "Local Government Area"])

    def test_unknown_country(self):
        hierarchy = get_admin_hierarchy("XX")
        self.assertEqual(hierarchy, [])


class GlobalLocationResolutionTests(TestCase):
    """Test full location resolution pipeline."""

    @classmethod
    def setUpTestData(cls):
        asia = Continent.objects.create(name="Asia", code="AS")
        america = Continent.objects.create(name="America", code="AM")
        Country.objects.create(name="India", code="IN", continent=asia,
                                centroid_lat=20.5937, centroid_lon=78.9629)
        Country.objects.create(name="United States", code="US", continent=america,
                                centroid_lat=37.0902, centroid_lon=-95.7129)

    def test_full_resolve_india(self):
        result = resolve_location_global(12.9716, 77.5946)
        self.assertIsNotNone(result["country"])
        self.assertEqual(result["country"].code, "IN")
        self.assertEqual(result["continent"].code, "AS")
        self.assertIn(result["confidence"], ["high", "medium", "low"])

    def test_full_resolve_usa(self):
        result = resolve_location_global(40.7128, -74.0060)
        self.assertIsNotNone(result["country"])
        self.assertEqual(result["country"].code, "US")
        self.assertEqual(result["continent"].code, "AM")

    def test_unresolvable_location(self):
        # Antarctica — no continent bounding box covers this
        result = resolve_location_global(-80.0, 0.0)
        # Continent is None since Antarctica has no bounding box
        self.assertIsNone(result["continent"])
