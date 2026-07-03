from django.urls import path
from . import views

urlpatterns = [
    path("states/", views.StateListView.as_view(), name="state-list"),
    path("zones/", views.ZoneListView.as_view(), name="zone-list"),
    path("geocode/", views.GeocodeView.as_view(), name="geocode"),
]
