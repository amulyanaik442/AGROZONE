from rest_framework import serializers
from .models import Continent, Country, AdminDivision, State, AgroclimateZone


class ContinentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Continent
        fields = ["id", "name", "code"]


class CountrySerializer(serializers.ModelSerializer):
    continent_name = serializers.CharField(source="continent.name", read_only=True)
    continent_code = serializers.CharField(source="continent.code", read_only=True)

    class Meta:
        model = Country
        fields = ["id", "name", "code", "continent_name", "continent_code",
                  "centroid_lat", "centroid_lon"]


class AdminDivisionSerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(source="country.name", read_only=True)

    class Meta:
        model = AdminDivision
        fields = ["id", "name", "level_name", "country_name",
                  "parent", "centroid_lat", "centroid_lon", "notable_facts"]


class AgroclimateZoneSerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(source="country.name", read_only=True)

    class Meta:
        model = AgroclimateZone
        fields = ["id", "name", "country_name"]


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ["id", "name", "centroid_lat", "centroid_lon", "notable_facts"]


class GeocodeRequestSerializer(serializers.Serializer):
    """Validates incoming lat/lon for the geocode endpoint."""
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)
