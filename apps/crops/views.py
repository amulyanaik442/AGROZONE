"""
Crops API Views
GET /api/v1/crops/               — list crops (filterable by state, country, category)
GET /api/v1/crops/<id>/          — crop detail
"""
from rest_framework import generics

from .models import Crop
from .serializers import CropSerializer


class CropListView(generics.ListAPIView):
    """
    List all crops. Supports query params:
      ?state=Karnataka              (India)
      ?country=India                (global)
      ?continent=Asia               (global)
      ?category=Pulses
      ?zone=Southern+Plateau+%26+Hills+Region
    """
    serializer_class = CropSerializer

    def get_queryset(self):
        qs = Crop.objects.select_related("state", "zone", "country", "continent").all()
        state = self.request.query_params.get("state")
        category = self.request.query_params.get("category")
        zone = self.request.query_params.get("zone")
        country = self.request.query_params.get("country")
        continent = self.request.query_params.get("continent")
        if state:
            qs = qs.filter(state__name__icontains=state)
        if category:
            qs = qs.filter(category__icontains=category)
        if zone:
            qs = qs.filter(zone__name__icontains=zone)
        if country:
            qs = qs.filter(country__name__icontains=country)
        if continent:
            qs = qs.filter(continent__name__icontains=continent)
        return qs


class CropDetailView(generics.RetrieveAPIView):
    queryset = Crop.objects.select_related("state", "zone", "country", "continent").all()
    serializer_class = CropSerializer
