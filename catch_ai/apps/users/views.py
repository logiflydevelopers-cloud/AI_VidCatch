from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail

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
from apps.credits.models import UserCredits
from apps.generations.models import Generation
from apps.subscriptions.models import UserSubscription

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
    user_credits = UserCredits.objects.filter(user=user).first()

    return Response({
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "is_admin": user.is_staff,
        "credits": user_credits.balance if user_credits else 0
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

        reset_link = f"https://silver-sable-a9fee9.netlify.app//reset-password?uid={uid}&token={token}"

        subject = "Reset Your Password"
        message = f"""
                Hi {user.username},

                Click the link below to reset your password:

                {reset_link}

                If you didn't request this, ignore this email.
                """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )

        print(reset_link)

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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def credit_history(request):
    try:
        user = request.user
        history = []

        # ==========================
        # 🔹 AI GENERATED (DEBIT)
        # ==========================
        generations = Generation.objects.filter(user=user)

        for item in generations:
            if item.credit_used > 0:
                history.append({
                    "title": "AI generate succeed",
                    "date": item.created_at,
                    "amount": -item.credit_used,
                    "type": "debit"
                })

        # ==========================
        # 🔹 MEMBERSHIP (CREDIT)
        # ==========================
        subs = UserSubscription.objects.filter(
            user=user,
            status="active"
        ).select_related("current_plan")

        has_subscription = subs.exists()

        for sub in subs:
            if sub.current_plan and sub.current_plan.credits_per_month > 0:
                history.append({
                    "title": "Membership benefits",
                    "date": sub.created_at,
                    "amount": sub.current_plan.credits_per_month,
                    "plan_name": sub.current_plan.name,
                    "type": "credit"
                })

        # ==========================
        # 🔹 FREE CREDITS (IF NO PLAN)
        # ==========================
        if not has_subscription:
            history.append({
                "title": "Free credits",
                "date": user.created_at,  # or timezone.now()
                "amount": 1000,  # 🔥 change based on your logic
                "type": "credit"
            })

        # ==========================
        # 🔹 SORT (LATEST FIRST)
        # ==========================
        history = sorted(history, key=lambda x: x["date"], reverse=True)

        return Response(history)

    except Exception as e:
        return Response({"error": str(e)}, status=500)