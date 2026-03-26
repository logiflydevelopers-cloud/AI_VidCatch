from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate

from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import SignupSerializer
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings
from rest_framework.permissions import AllowAny

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str

User = get_user_model()


def get_tokens_for_user(user):

    refresh = RefreshToken.for_user(user)

    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


@api_view(["POST"])
@permission_classes([AllowAny])
def signup(request):

    serializer = SignupSerializer(data=request.data)

    if serializer.is_valid():

        user = serializer.save()

        tokens = get_tokens_for_user(user)

        return Response({
            "message": "User created successfully",
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "is_admin": user.is_staff
            },
            "tokens": tokens
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):

    email = request.data.get("email")
    password = request.data.get("password")

    if not email or not password:
        return Response(
            {"error": "Email and password are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = authenticate(request, email=email, password=password)

    if user is None:
        return Response(
            {"error": "Invalid email or password"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.is_active:
        return Response(
            {"error": "Account is disabled"},
            status=status.HTTP_403_FORBIDDEN
        )

    tokens = get_tokens_for_user(user)

    return Response({
        "message": "Login successful",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "is_admin": user.is_staff
        },
        "tokens": tokens
    }, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):

    user = request.user

    return Response({
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "is_admin": user.is_staff
    })

@api_view(["POST"])
@permission_classes([AllowAny])
def google_login(request):

    token = request.data.get("token") or request.data.get("credential")

    if not token:
        return Response(
            {"error": "Token is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )
    except ValueError:
        return Response(
            {"error": "Invalid Google token"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    email = idinfo["email"]
    username = idinfo.get("name", "")
    google_id = idinfo["sub"]

    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            "username": username,
            "login_provider": "google",
            "google_id": google_id
        }
    )

    refresh = RefreshToken.for_user(user)

    return Response({
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "is_admin": user.is_staff
        },
        "tokens": {
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }
    })

@api_view(["POST"])
@permission_classes([AllowAny])
def forgot_password(request):

    email = request.data.get("email")

    if not email:
        return Response(
            {"error": "Email is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = User.objects.filter(email=email).first()

    # Don't reveal if user exists or not
    if user:
        token = PasswordResetTokenGenerator().make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.id))

        reset_link = f"http://localhost:3000/reset-password?uid={uid}&token={token}"

        # For now (testing)
        print("RESET LINK:", reset_link)

        # Later: send email here

    return Response({
        "message": "If email exists, reset link sent"
    }, status=status.HTTP_200_OK)

@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password(request):

    uid = request.data.get("uid")
    token = request.data.get("token")
    new_password = request.data.get("new_password")

    if not uid or not token or not new_password:
        return Response(
            {"error": "uid, token and new_password are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(id=user_id)
    except Exception:
        return Response(
            {"error": "Invalid user"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not PasswordResetTokenGenerator().check_token(user, token):
        return Response(
            {"error": "Invalid or expired token"},
            status=status.HTTP_400_BAD_REQUEST
        )

    user.set_password(new_password)
    user.save()

    return Response({
        "message": "Password reset successful"
    }, status=status.HTTP_200_OK)