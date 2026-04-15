from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .models import PlanSlide


# ==========================================================
# PUBLIC PLAN SLIDES API (FOR FRONTEND SLIDER)
# ==========================================================
@api_view(["GET"])
@permission_classes([AllowAny])
def public_plan_slides(request):
    """
    Returns active plan slides for UI slider
    """

    try:
        slides = PlanSlide.objects.filter(
            is_active=True
        ).order_by("order", "-created_at")

        data = [
            {
                "id": slide.id,
                "url": slide.file_url,
                "type": slide.media_type
            }
            for slide in slides
        ]

        return Response(data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )