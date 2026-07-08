from rest_framework import serializers


class SoilInputSerializer(serializers.Serializer):
    """
    Validates the full soil input payload.
    ph is required (Gate 2 hard filter). All others are optional.
    """
    # Location — one of lat+lon, state_name, or continent_name+country_name
    lat = serializers.FloatField(required=False, allow_null=True)
    lon = serializers.FloatField(required=False, allow_null=True)
    state_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    continent_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    country_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    # Gate 2 — required
    ph = serializers.FloatField(min_value=0.0, max_value=14.0)

    # Gate 3 — soft
    oc = serializers.FloatField(required=False, allow_null=True, min_value=0)
    ec = serializers.FloatField(required=False, allow_null=True, min_value=0)

    # Gate 4 — macronutrients
    n  = serializers.FloatField(required=False, allow_null=True, min_value=0)
    p  = serializers.FloatField(required=False, allow_null=True, min_value=0)
    k  = serializers.FloatField(required=False, allow_null=True, min_value=0)
    s  = serializers.FloatField(required=False, allow_null=True, min_value=0)

    # Gate 5 — micronutrients
    fe = serializers.FloatField(required=False, allow_null=True, min_value=0)
    mn = serializers.FloatField(required=False, allow_null=True, min_value=0)
    cu = serializers.FloatField(required=False, allow_null=True, min_value=0)
    zn = serializers.FloatField(required=False, allow_null=True, min_value=0)
    b  = serializers.FloatField(required=False, allow_null=True, min_value=0)
    ca = serializers.FloatField(required=False, allow_null=True, min_value=0)
    mg = serializers.FloatField(required=False, allow_null=True, min_value=0)

    def validate(self, data):
        has_latlon = data.get("lat") is not None and data.get("lon") is not None
        has_state = bool(data.get("state_name"))
        has_cont_country = bool(data.get("continent_name")) and bool(data.get("country_name"))
        if not has_latlon and not has_state and not has_cont_country:
            raise serializers.ValidationError(
                "Provide lat+lon, state_name, or continent_name+country_name for location."
            )
        return data


class ParamScoreSerializer(serializers.Serializer):
    score = serializers.FloatField()
    max   = serializers.FloatField()
    pct   = serializers.IntegerField()


class CropResultSerializer(serializers.Serializer):
    rank               = serializers.IntegerField()
    crop_name          = serializers.CharField()
    category           = serializers.CharField()
    zone_name          = serializers.CharField()
    state_name         = serializers.CharField()
    notes              = serializers.CharField()
    is_notable         = serializers.BooleanField()
    temp_range         = serializers.CharField()
    total_score        = serializers.FloatField()
    max_score          = serializers.FloatField()
    score_pct          = serializers.FloatField()
    nutrient_deficiencies = serializers.ListField(child=serializers.CharField())
    param_scores       = serializers.DictField()


class RecommendationResponseSerializer(serializers.Serializer):
    state             = serializers.CharField()
    zone              = serializers.CharField()
    continent         = serializers.CharField(required=False, allow_blank=True)
    country           = serializers.CharField(required=False, allow_blank=True)
    distance_km       = serializers.FloatField()
    confidence        = serializers.CharField()
    confidence_note   = serializers.CharField()
    crops_evaluated   = serializers.IntegerField()
    crops_eliminated_by_ph = serializers.IntegerField()
    top_crops         = CropResultSerializer(many=True)
