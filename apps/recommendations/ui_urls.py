from django.urls import path
from .views import recommend_form, recommend_result

urlpatterns = [
    path("", recommend_form, name="recommend-form"),
    path("result/", recommend_result, name="recommend-result"),
]
