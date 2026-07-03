"""
Location API Views
GET  /api/v1/location/states/         — list all states
GET  /api/v1/location/zones/          — list all agroclimatic zones
POST /api/v1/location/geocode/        — resolve lat/lon → state
"""
from rest_framework import generics, views, status
from rest_framework.response import Response

from .models import State, AgroclimateZone
from .serializers import StateSerializer, AgroclimateZoneSerializer, GeocodeRequestSerializer
from .services import resolve_location, validate_india_bounds


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
    → nearest state, agroclimatic zone, confidence note
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
