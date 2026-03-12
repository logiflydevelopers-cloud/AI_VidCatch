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

        extra_kwargs = {
            "password": {"write_only": True}
        }

    def validate(self, data):

        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"error": "Passwords do not match"}
            )

        if User.objects.filter(email=data["email"]).exists():
            raise serializers.ValidationError(
                {"email": "Email already registered"}
            )

        return data

    def create(self, validated_data):

        validated_data.pop("confirm_password")

        user = User.objects.create_user(**validated_data)

        return user