from rest_framework import serializers
from .models import User


class SignupSerializer(serializers.ModelSerializer):

    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "password",
            "confirm_password"
        ]

        read_only_fields = ["id"]

        extra_kwargs = {
            "password": {
                "write_only": True,
                "min_length": 8
            }
        }

    def validate_email(self, value):

        user = User.objects.filter(email=value).first()

        if user:
            if user.login_provider == "google":
                raise serializers.ValidationError(
                    "This email is registered using Google Sign-In"
                )

            raise serializers.ValidationError(
                "Email already registered"
            )

        return value


    def validate(self, data):

        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"password": "Passwords do not match"}
            )

        return data


    def create(self, validated_data):

        validated_data.pop("confirm_password")

        user = User.objects.create_user(
            **validated_data,
            login_provider="email"
        )

        return user
    
class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=6)