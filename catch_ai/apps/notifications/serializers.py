from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Notification
        fields = [
            "id",
            "title",
            "message",
            "subtitle",

            "display_type",

            "media",
            "media_type",

            "priority",

            "trigger_type",
            "trigger_value",

            "start_time",
            "end_time",

            "user_type",

            "created_at",
        ]


class NotificationCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"

    