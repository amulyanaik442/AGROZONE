"""
Recommendations Views

REST API:
  POST /api/v1/recommend/   → JSON response with top 5 crops

UI:
  GET  /recommend/          → HTML form
  POST /recommend/          → HTML results
"""
from rest_framework import views, status
from rest_framework.response import Response
from django.shortcuts import render

from .serializers import SoilInputSerializer, RecommendationResponseSerializer
from .services import get_recommendations
from apps.location.models import State


# ── REST API ──────────────────────────────────────────────────────────────────

class RecommendView(views.APIView):
    """
    POST /api/v1/recommend/
    Body: SoilInputSerializer fields
    Returns: top 5 crops with scores and nutrient deficiencies
    """
    def post(self, request):
        ser = SoilInputSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = get_recommendations(ser.validated_data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        out = RecommendationResponseSerializer(result)
        return Response(out.data, status=status.HTTP_200_OK)


# ── UI Views ──────────────────────────────────────────────────────────────────

def recommend_form(request):
    """GET /recommend/ — render the soil input form."""
    states = State.objects.values_list("name", flat=True).order_by("name")
    return render(request, "recommendations/form.html", {"states": list(states)})


def recommend_result(request):
    """POST /recommend/ — process form, render result page."""
    if request.method != "POST":
        return recommend_form(request)

    states = State.objects.values_list("name", flat=True).order_by("name")

    # Parse form data into the same structure as the API serializer
    def _float(key):
        v = request.POST.get(key, "").strip()
        try:
            return float(v) if v else None
        except ValueError:
            return None

    payload = {
        "lat": _float("lat"),
        "lon": _float("lon"),
        "state_name": request.POST.get("state_name", "").strip() or None,
        "ph": _float("ph"),
        "oc": _float("oc"), "ec": _float("ec"),
        "n": _float("n"), "p": _float("p"), "k": _float("k"), "s": _float("s"),
        "fe": _float("fe"), "mn": _float("mn"), "cu": _float("cu"),
        "zn": _float("zn"), "b": _float("b"), "ca": _float("ca"), "mg": _float("mg"),
    }

    ser = SoilInputSerializer(data=payload)
    if not ser.is_valid():
        return render(request, "recommendations/form.html", {
            "states": list(states),
            "errors": ser.errors,
            "prev": request.POST,
        })

    try:
        result = get_recommendations(ser.validated_data)
    except ValueError as e:
        return render(request, "recommendations/form.html", {
            "states": list(states),
            "errors": {"location": [str(e)]},
            "prev": request.POST,
        })

    return render(request, "recommendations/result.html", {
        "result": result,
        "soil": ser.validated_data,
        "states": list(states),
    })
