from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status

from apps.users.models import User


@api_view(["DELETE"])
@permission_classes([IsAdminUser])
def delete_user(request, user_id):

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response(
            {"error": "User not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    # Prevent deleting superuser
    if user.is_superuser:
        return Response(
            {"error": "Cannot delete superuser"},
            status=status.HTTP_403_FORBIDDEN
        )

    user.delete()

    return Response(
        {"message": "User deleted successfully"},
        status=status.HTTP_200_OK
    )