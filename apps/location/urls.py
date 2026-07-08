from django.urls import path
from . import views

urlpatterns = [
    # India endpoints (unchanged)
    path("states/", views.StateListView.as_view(), name="state-list"),
    path("zones/", views.ZoneListView.as_view(), name="zone-list"),
    path("geocode/", views.GeocodeView.as_view(), name="geocode"),
    # Global endpoints (new)
    path("continents/", views.ContinentListView.as_view(), name="continent-list"),
    path("countries/", views.CountryListView.as_view(), name="country-list"),
    path("admin-divisions/", views.AdminDivisionListView.as_view(), name="admin-division-list"),
    path("global-geocode/", views.GlobalGeocodeView.as_view(), name="global-geocode"),
]
