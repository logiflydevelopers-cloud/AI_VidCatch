from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from .models import Plan
from .serializers import PlanSerializer
from .sync_plans import sync_plans

# ============================
# SIMPLE SYNC (TESTING)
# ============================
@api_view(["POST"])
def sync_plans_api(request):
    try:
        sync_plans()
        return Response({
            "status": True,
            "message": "Plans synced successfully"
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "status": False,
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ============================
# SECURE SYNC (RECOMMENDED)
# ============================
@api_view(["POST"])
@permission_classes([IsAdminUser])
def sync_plans_admin(request):
    try:
        sync_plans()
        return Response({
            "status": True,
            "message": "Plans synced successfully (Admin)"
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "status": False,
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
# ============================
# GET ALL ACTIVE PLANS
# ============================
@api_view(["GET"])
def get_all_plans(request):
    try:
        plans = Plan.objects.filter(is_active=True).order_by("price_inr")

        serializer = PlanSerializer(plans, many=True)

        return Response({
            "status": True,
            "plans": serializer.data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "status": False,
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)