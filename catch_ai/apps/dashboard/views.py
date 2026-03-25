from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from .services import get_dashboard_data

@api_view(["GET"])
@permission_classes([IsAdminUser])
def dashboard(request):
    data = get_dashboard_data()
    return Response(data)