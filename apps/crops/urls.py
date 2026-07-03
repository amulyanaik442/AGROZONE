from django.urls import path
from . import views

urlpatterns = [
    path("", views.CropListView.as_view(), name="crop-list"),
    path("<int:pk>/", views.CropDetailView.as_view(), name="crop-detail"),
]
