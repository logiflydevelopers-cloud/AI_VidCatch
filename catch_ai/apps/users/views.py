from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate

from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import SignupSerializer

User = get_user_model()


def get_tokens_for_user(user):

    refresh = RefreshToken.for_user(user)

    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


@api_view(["POST"])
def signup(request):

    serializer = SignupSerializer(data=request.data)

    if serializer.is_valid():

        user = serializer.save()

        tokens = get_tokens_for_user(user)

        return Response({
            "message": "User created successfully",
            "user_id": user.id,
            "tokens": tokens
        })

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def login(request):

    email = request.data.get("email")
    password = request.data.get("password")

    user = authenticate(request, email=email, password=password)

    if user is None:
        return Response(
            {"error": "Invalid email or password"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    tokens = get_tokens_for_user(user)

    return Response({
        "message": "Login successful",
        "user_id": user.id,
        "tokens": tokens
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):

    user = request.user

    return Response({
        "id": user.id,
        "email": user.email,
        "username": user.username
    })