from rest_framework import serializers
from .models import Crop


class CropSerializer(serializers.ModelSerializer):
    state_name = serializers.CharField(source="state.name", read_only=True)
    zone_name = serializers.CharField(source="zone.name", read_only=True)

    class Meta:
        model = Crop
        fields = [
            "id", "state_name", "zone_name", "category", "crop_name",
            "notes", "is_notable", "temp_range",
            "ph_lo", "ph_hi",
            "oc_lo", "oc_hi", "ec_lo", "ec_hi",
            "n_lo", "n_hi", "p_lo", "p_hi", "k_lo", "k_hi", "s_lo", "s_hi",
            "fe_lo", "fe_hi", "mn_lo", "mn_hi", "cu_lo", "cu_hi",
            "zn_lo", "zn_hi", "b_lo", "b_hi", "ca_lo", "ca_hi", "mg_lo", "mg_hi",
        ]
