from rest_framework import serializers
from .models import State, AgroclimateZone


class AgroclimateZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgroclimateZone
        fields = ["id", "name"]


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ["id", "name", "centroid_lat", "centroid_lon", "notable_facts"]


class GeocodeRequestSerializer(serializers.Serializer):
    """Validates incoming lat/lon for the geocode endpoint."""
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)
