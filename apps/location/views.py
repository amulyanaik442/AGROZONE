"""
Location API Views
Backward-compatible India endpoints (unchanged) + new global endpoints.

India endpoints:
  GET  /api/v1/location/states/         — list all Indian states
  GET  /api/v1/location/zones/          — list all agroclimatic zones
  POST /api/v1/location/geocode/        — resolve lat/lon → Indian state

Global endpoints:
  GET  /api/v1/location/continents/     — list all continents
  GET  /api/v1/location/countries/      — list all countries
  GET  /api/v1/location/admin-divisions/ — list admin divisions
  POST /api/v1/location/global-geocode/ — resolve lat/lon globally
"""
from rest_framework import generics, views, status
from rest_framework.response import Response

from .models import Continent, Country, AdminDivision, State, AgroclimateZone
from .serializers import (
    ContinentSerializer, CountrySerializer, AdminDivisionSerializer,
    StateSerializer, AgroclimateZoneSerializer, GeocodeRequestSerializer,
)
from .services import resolve_location, validate_india_bounds
from .geography_service import resolve_location_global


# ── India endpoints (unchanged) ─────────────────────────────────────────────

class StateListView(generics.ListAPIView):
    """Return all Indian states stored in the DB."""
    queryset = State.objects.all()
    serializer_class = StateSerializer


class ZoneListView(generics.ListAPIView):
    """Return all agroclimatic zones."""
    queryset = AgroclimateZone.objects.all()
    serializer_class = AgroclimateZoneSerializer


class GeocodeView(views.APIView):
    """
    POST { "lat": 12.97, "lon": 77.59 }
    → nearest Indian state, agroclimatic zone, confidence note
    """
    def post(self, request):
        ser = GeocodeRequestSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        lat, lon = ser.validated_data["lat"], ser.validated_data["lon"]

        if not validate_india_bounds(lat, lon):
            return Response(
                {"error": "Coordinates appear to be outside India. Please enter valid Indian coordinates."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = resolve_location(lat, lon)
        state = result["state"]

        return Response({
            "lat": lat,
            "lon": lon,
            "state": StateSerializer(state).data,
            "distance_to_centroid_km": result["distance_km"],
            "confidence": result["confidence"],
            "confidence_note": result["confidence_note"],
        })


# ── Global endpoints (new) ──────────────────────────────────────────────────

class ContinentListView(generics.ListAPIView):
    """Return all continents."""
    queryset = Continent.objects.all()
    serializer_class = ContinentSerializer


class CountryListView(generics.ListAPIView):
    """Return all countries, optionally filtered by continent."""
    serializer_class = CountrySerializer

    def get_queryset(self):
        qs = Country.objects.select_related("continent").all()
        continent_code = self.request.query_params.get("continent")
        if continent_code:
            qs = qs.filter(continent__code__iexact=continent_code)
        return qs


class AdminDivisionListView(generics.ListAPIView):
    """List admin divisions, filterable by country and level."""
    serializer_class = AdminDivisionSerializer

    def get_queryset(self):
        qs = AdminDivision.objects.select_related("country").all()
        country_code = self.request.query_params.get("country")
        level = self.request.query_params.get("level")
        if country_code:
            qs = qs.filter(country__code__iexact=country_code)
        if level:
            qs = qs.filter(level_name__iexact=level)
        return qs


class GlobalGeocodeView(views.APIView):
    """
    POST { "lat": 12.97, "lon": 77.59 }
    → continent, country, admin division (global, no India restriction)
    """
    def post(self, request):
        ser = GeocodeRequestSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        lat, lon = ser.validated_data["lat"], ser.validated_data["lon"]
        result = resolve_location_global(lat, lon)

        return Response({
            "lat": lat,
            "lon": lon,
            "continent": ContinentSerializer(result["continent"]).data if result["continent"] else None,
            "country": CountrySerializer(result["country"]).data if result["country"] else None,
            "admin_division": AdminDivisionSerializer(result["admin_division"]).data if result["admin_division"] else None,
            "admin_hierarchy": result["admin_hierarchy"],
            "distance_km": result["distance_km"],
            "confidence": result["confidence"],
            "confidence_note": result["confidence_note"],
        })
