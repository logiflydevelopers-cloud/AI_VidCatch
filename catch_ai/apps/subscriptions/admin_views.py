from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from .models import Plan
from .serializers import PlanSerializer
import uuid


# CREATE + LIST
@api_view(['GET', 'POST'])
@permission_classes([IsAdminUser])
def plans(request):

    # LIST ALL PLANS
    if request.method == 'GET':
        data = Plan.objects.all().order_by('-created_at')
        serializer = PlanSerializer(data, many=True)
        return Response(serializer.data)

    # CREATE PLAN
    if request.method == 'POST':
        data = request.data.copy()

        if not data.get("id"):
            data["id"] = "plan_" + uuid.uuid4().hex[:6].upper()

        serializer = PlanSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=400)


# GET + UPDATE + DELETE (Single Plan)
@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAdminUser])
def plan_detail(request, plan_id):

    try:
        plan = Plan.objects.get(id=plan_id)
    except Plan.DoesNotExist:
        return Response({"error": "Plan not found"}, status=404)

    # GET
    if request.method == 'GET':
        return Response(PlanSerializer(plan).data)

    # UPDATE
    if request.method in ['PUT', 'PATCH']:
        serializer = PlanSerializer(plan, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    # DELETE
    if request.method == 'DELETE':
        plan.delete()
        return Response({"message": "Deleted successfully"})