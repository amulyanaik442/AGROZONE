"""AgroZone — Root URL Configuration"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    # Redirect root to UI
    path("", RedirectView.as_view(url="/recommend/", permanent=False)),
    # REST APIs
    path("api/v1/location/", include("apps.location.urls")),
    path("api/v1/crops/", include("apps.crops.urls")),
    path("api/v1/recommend/", include("apps.recommendations.urls")),
    # Frontend UI
    path("recommend/", include("apps.recommendations.ui_urls")),
]
